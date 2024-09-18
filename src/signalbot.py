import os
import logging
import requests
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_bolt.logger import get_bolt_logger

# Set up logging
logging.basicConfig(level=logging.INFO)

load_dotenv()

# Print environment variables for debugging
print(f"SLACK_BOT_TOKEN: {os.environ.get('SLACK_BOT_TOKEN')[:10]}...")
print(f"SLACK_APP_TOKEN: {os.environ.get('SLACK_APP_TOKEN')[:10]}...")

# Create a logger
logger = get_bolt_logger(cls=logging.Logger)
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

API_BASE_URL = "https://live-db-kohl.vercel.app"

# Store conversation states
conversation_states = {}

def call_api(endpoint, method="GET", params=None, json=None):
    url = f"{API_BASE_URL}{endpoint}"
    headers = {"access_token": os.environ.get("API_KEY")}
    try:
        if method == "GET":
            response = requests.get(url, params=params, headers=headers)
        elif method == "POST":
            if json:
                response = requests.post(url, json=json, headers=headers)
            else:
                response = requests.post(url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"API call failed: {str(e)}", exc_info=True)
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Response content: {e.response.content}", exc_info=True)
        raise

def show_organizations(client, channel_id):
    parameters = {"customer_organization_id": 1}
    organizations = call_api("/organization/list", params=parameters)
    org_list = "\n".join([f"{org['id']}: {org['name']}" for org in organizations])
    client.chat_postMessage(
        channel=channel_id,
        text=f"Here are the available organizations:\n{org_list}\n\nPlease reply with:\n"
             f"- One or more organization IDs (comma-separated)\n"
             f"- 'new' to create a new organization\n"
             f"- 'none' to proceed without selecting any organizations"
    )

def show_users(client, channel_id):
    parameters = {"customer_organization_id": 1}  # Adjust this if needed
    users = call_api("/user/list", params=parameters)
    user_list = "\n".join([f"{user['id']}: {user['name']}" for user in users])
    client.chat_postMessage(
        channel=channel_id,
        text=f"Here are the available users:\n{user_list}\n\nPlease reply with:\n"
             f"- An existing user ID\n"
             f"- 'new' to create a new user"
    )

@app.command("/add_signal")
def handle_add_signal_command(ack, say, command, client):
    ack()
    try:
        dm = client.conversations_open(users=[command['user_id']])
        dm_channel_id = dm['channel']['id']
        
        show_organizations(client, dm_channel_id)
        
        conversation_states[command['user_id']] = {
            'state': 'awaiting_org_selection',
            'dm_channel_id': dm_channel_id,
            'selected_org_ids': []
        }
    except Exception as e:
        say(f"Error starting signal addition process: {str(e)}", ephemeral=True)

@app.command("/register_slack")
def handle_register_slack_command(ack, say, command, client):
    ack()
    try:
        dm = client.conversations_open(users=[command['user_id']])
        dm_channel_id = dm['channel']['id']
        
        show_users(client, dm_channel_id)
        
        conversation_states[command['user_id']] = {
            'state': 'awaiting_user_selection',
            'dm_channel_id': dm_channel_id,
            'slack_id': command['user_id']
        }
    except Exception as e:
        say(f"Error starting Slack registration process: {str(e)}", ephemeral=True)

@app.event("message")
def handle_message(event, say, client):
    user_id = event.get('user')
    channel_id = event.get('channel')
    
    if not user_id or not channel_id:
        return

    channel_info = client.conversations_info(channel=channel_id)
    if not channel_info['channel']['is_im']:
        return

    if user_id not in conversation_states:
        client.chat_postMessage(
            channel=channel_id,
            text="To start adding a signal, use the /add_signal command. To register with Slack, use the /register_slack command."
        )
        return

    state = conversation_states[user_id]['state']
    text = event['text'].strip()

    if state == 'awaiting_org_selection':
        if text.lower() == 'new':
            client.chat_postMessage(
                channel=channel_id,
                text="Please enter the name for the new organization:"
            )
            conversation_states[user_id]['state'] = 'awaiting_new_org_name'
        elif text.lower() == 'none':
            client.chat_postMessage(
                channel=channel_id,
                text="Proceeding without selecting any organizations. Please enter the signal text:"
            )
            conversation_states[user_id]['state'] = 'awaiting_signal'
        elif all(org_id.strip().isdigit() for org_id in text.split(',')):
            org_ids = [int(org_id.strip()) for org_id in text.split(',')]
            conversation_states[user_id]['selected_org_ids'].extend(org_ids)
            client.chat_postMessage(
                channel=channel_id,
                text=f"You've selected organization ID(s): {', '.join(map(str, org_ids))}. Please enter the signal text:"
            )
            conversation_states[user_id]['state'] = 'awaiting_signal'
        else:
            client.chat_postMessage(
                channel=channel_id,
                text="Invalid input. Please enter valid organization ID(s) (comma-separated), 'new', or 'none'."
            )

    elif state == 'awaiting_new_org_name':
        try:
            new_org = call_api("/organization/create", method="POST", json={"name": text, "Customer_Organization_id": 1})
            org_id = new_org['organization_id']
            client.chat_postMessage(
                channel=channel_id,
                text=f"New organization '{text}' created with ID: {org_id}."
            )
            show_organizations(client, channel_id)
            conversation_states[user_id]['state'] = 'awaiting_org_selection'
        except Exception as e:
            client.chat_postMessage(
                channel=channel_id,
                text=f"Error creating new organization: {str(e)}"
            )

    elif state == 'awaiting_signal':
        try:
            org_ids = conversation_states[user_id]['selected_org_ids']
            user_response = call_api("/user/slack", method="GET", params={"slack_id": str(user_id)})
            if 'user_id' not in user_response:
                client.chat_postMessage(
                    channel=channel_id,
                    text="It looks like your Slack ID is not registered. Let's get you registered first."
                )
                show_users(client, channel_id)
                conversation_states[user_id] = {
                    'state': 'awaiting_user_selection',
                    'dm_channel_id': channel_id,
                    'slack_id': user_id,
                    'pending_signal': {
                        'text': text,
                        'org_ids': org_ids
                    }
                }
            else:
                signal_response = call_api("/signal/create", method="POST", json={
                    "signal": text,
                    "organization_ids": org_ids,
                    "user_id": user_response['user_id'],
                    "source": "Slack",
                    "type": "manual"
                })
                client.chat_postMessage(
                    channel=channel_id,
                    text=f"Signal added successfully: {signal_response}"
                )
                del conversation_states[user_id]  # Clear the conversation state
        except Exception as e:
            client.chat_postMessage(
                channel=channel_id,
                text=f"Error adding signal: {str(e)}"
            )

    elif state == 'awaiting_user_selection':
        if text.lower() == 'new':
            client.chat_postMessage(
                channel=channel_id,
                text="Please enter the name for the new user:"
            )
            conversation_states[user_id]['state'] = 'awaiting_new_user_name'
        elif text.isdigit():
            try:
                client.chat_postMessage(
                    channel=channel_id,
                    text=f"Registering Slack ID {conversation_states[user_id]['slack_id']} with user ID {text}..."
                )
                register_response = call_api("/user/register", method="POST", params={
                    "slack_id": str(conversation_states[user_id]['slack_id']),
                    "user_id": int(text)
                })
                client.chat_postMessage(
                    channel=channel_id,
                    text=f"Slack registration successful. Your Slack ID {conversation_states[user_id]['slack_id']} has been linked to user ID {text}."
                )
                
                # Check if there's a pending signal
                if 'pending_signal' in conversation_states[user_id]:
                    pending_signal = conversation_states[user_id]['pending_signal']
                    signal_response = call_api("/signal/create", method="POST", json={
                        "signal": pending_signal['text'],
                        "organization_ids": pending_signal['org_ids'],
                        "user_id": int(text),
                        "source": "Slack",
                        "type": "manual"
                    })
                    client.chat_postMessage(
                        channel=channel_id,
                        text=f"Pending signal added successfully: {signal_response}"
                    )
                
                del conversation_states[user_id]  # Clear the conversation state
            except Exception as e:
                client.chat_postMessage(
                    channel=channel_id,
                    text=f"Error registering Slack ID: {str(e)}"
                )
        else:
            client.chat_postMessage(
                channel=channel_id,
                text="Invalid input. Please enter a valid user ID or 'new' to create a new user."
            )

    elif state == 'awaiting_new_user_name':
        try:
            new_user = call_api("/user/create", method="POST", json={
                "name": text,
                "Customer_Organization_id": 1  # Adjust this if needed
            })
            user_id = new_user['user_id']
            client.chat_postMessage(
                channel=channel_id,
                text=f"New user '{text}' created with ID: {user_id}. Now registering your Slack ID..."
            )
            register_response = call_api("/user/register", method="POST", params={
                "slack_id": str(conversation_states[user_id]['slack_id']),
                "user_id": user_id
            })
            client.chat_postMessage(
                channel=channel_id,
                text=f"Slack registration successful. Your Slack ID {conversation_states[user_id]['slack_id']} has been linked to the new user ID {user_id}."
            )
            
            # Check if there's a pending signal
            if 'pending_signal' in conversation_states[user_id]:
                pending_signal = conversation_states[user_id]['pending_signal']
                signal_response = call_api("/signal/create", method="POST", json={
                    "signal": pending_signal['text'],
                    "organization_ids": pending_signal['org_ids'],
                    "user_id": user_id,
                    "source": "Slack",
                    "type": "manual"
                })
                client.chat_postMessage(
                    channel=channel_id,
                    text=f"Pending signal added successfully: {signal_response}"
                )
            
            del conversation_states[user_id]  # Clear the conversation state
        except Exception as e:
            client.chat_postMessage(
                channel=channel_id,
                text=f"Error creating new user and registering Slack ID: {str(e)}"
            )

@app.command("/help")
def handle_help_command(ack, say, command, client):
    ack()
    try:
        client.chat_postMessage(
            channel=command['channel_id'],
            text="I can respond to the following commands:\n"
                 "- /add_signal: Start adding a signal to a customer organization\n"
                 "- /register_slack: Register your Slack ID with your user account\n"
                 "- /help: Show this help message"
        )
    except Exception as e:
        logger.error(f"Error sending help message: {str(e)}", exc_info=True)
        
if __name__ == "__main__":
    handler = SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN"))
    handler.start()