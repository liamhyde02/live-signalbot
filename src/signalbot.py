import os
import logging
import requests
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_bolt.logger import logger
# Set up logging
logging.basicConfig(level=logging.DEBUG)

load_dotenv()

# Print environment variables for debugging
print(f"SLACK_BOT_TOKEN: {os.environ.get('SLACK_BOT_TOKEN')[:10]}...")
print(f"SLACK_APP_TOKEN: {os.environ.get('SLACK_APP_TOKEN')[:10]}...")

app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

# Update the API_BASE_URL to your Vercel-deployed FastAPI app
API_BASE_URL = "https://live-db-kohl.vercel.app"

# Function to call the API
def call_api(endpoint, method="GET", params=None, json=None):
    url = f"{API_BASE_URL}{endpoint}"
    headers = {"access_token": os.environ.get("API_KEY")}
    try:
        if method == "GET":
            response = requests.get(url, params=params, headers=headers)
        elif method == "POST":
            response = requests.post(url, json=json, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"API call failed: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Response content: {e.response.content}")
        raise

@app.command("/add_signal")
def handle_add_signal_command(ack, say, command):
    ack()
    try:
        # Fetch organizations
        organizations = call_api("/organizations/list")
        org_list = "\n".join([f"{org['id']}: {org['name']}" for org in organizations])
        say(f"Here are the available organizations:\n{org_list}\n\nPlease reply with an organization ID or 'new' to create a new organization.")
    except Exception as e:
        say(f"Error fetching organizations: {str(e)}")

@app.message("new")
def handle_new_organization(message, say):
    say("Please enter the name for the new organization:")

@app.message(r"^\d+$")
def handle_organization_selection(message, say):
    org_id = message['text']
    say(f"You've selected organization ID: {org_id}. Please enter the signal text:")

@app.message()
def handle_user_input(message, say, client):
    channel_id = message['channel']
    thread_ts = message.get('thread_ts', message['ts'])
    
    # Fetch conversation history
    result = client.conversations_replies(channel=channel_id, ts=thread_ts)
    messages = result['messages']
    
    if len(messages) == 2:  # New organization name
        org_name = message['text']
        try:
            new_org = call_api("/organizations/create", method="POST", json={"name": org_name})
            say(f"New organization '{org_name}' created with ID: {new_org['organization_id']}. Please enter the signal text:")
        except Exception as e:
            say(f"Error creating new organization: {str(e)}")
    elif len(messages) == 3:  # Signal text
        signal_text = message['text']
        org_id = messages[1]['text']
        try:
            # Assuming you have an endpoint to add a signal
            signal_response = call_api("/signals/create", method="POST", json={"organization_id": org_id, "signal": signal_text})
            say(f"Signal added successfully: {signal_response}")
        except Exception as e:
            say(f"Error adding signal: {str(e)}")
    else:
        say("I'm not sure how to process that. Please start over with the /add_signal command.")


@app.command("/hello")
def handle_hello_command(ack, say):
    ack()
    say("Hello! I'm your Slack bot connected to the livePM database via Vercel.")
    logging.debug("/hello command was triggered")

@app.command("/get_vision")
def handle_get_vision_command(ack, say, command):
    ack()
    try:
        response = call_api("/vision")
        say(f"Vision: {response['data']['vision']}")
    except Exception as e:
        say(f"Error fetching vision: {str(e)}")
    logging.debug("/get_vision command was triggered")

@app.command("/get_mission")
def handle_get_mission_command(ack, say, command):
    ack()
    try:
        response = call_api("/mission")
        say(f"Mission: {response['data']['mission']}")
    except Exception as e:
        say(f"Error fetching mission: {str(e)}")
    logging.debug("/get_mission command was triggered")

@app.command("/list_users")
def handle_list_users_command(ack, say, command):
    ack()
    try:
        # Parse the customer_organization_id from the command text
        cmd_parts = command['text'].split()
        if len(cmd_parts) > 0 and cmd_parts[0].isdigit():
            customer_org_id = int(cmd_parts[0])
        else:
            customer_org_id = 1  # Default to 1 if no valid ID is provided

        params = {"customer_organization_id": customer_org_id}
        response = call_api("/user/list", params=params)
        users = response

        if users:
            user_list = "\n".join([f"- ID: {user['id']}, Name: {user['name']}" for user in users])
            say(f"Users for Customer Organization {customer_org_id}:\n{user_list}")
        else:
            say(f"No users found for Customer Organization {customer_org_id}.")
    except Exception as e:
        error_message = f"Error fetching users: {str(e)}"
        logger.error(error_message)
        say(error_message)
    logger.debug(f"/list_users command was triggered for org ID: {customer_org_id}")


@app.message("help")
def handle_help_message(message, say):
    say("I can respond to the following commands:\n"
        "- /hello: Say hello\n"
        "- /get_vision: Get the company vision\n"
        "- /get_mission: Get the company mission\n"
        "- /list_users: Get a list of users for Customer Organization 1\n"
        "- help: Show this help message")
    logging.debug("help message was triggered")

@app.event("app_mention")
def handle_app_mention(event, say):
    say(f"Hi there, <@{event['user']}>! You can use /hello, /get_vision, /get_mission, or /list_users to interact with me.")
    logging.debug(f"Bot was mentioned by user {event['user']}")

if __name__ == "__main__":
    handler = SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN"))
    handler.start()