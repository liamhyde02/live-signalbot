from config import conversation_states
from api_client import call_api, get_customer_org_id
from utils import show_organizations, show_users

def handle_org_selection(user_id, channel_id, text, client):
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

def handle_new_org_name(user_id, channel_id, text, client):
    try:
        new_org = call_api("/organization/create", method="POST", json={
            "name": text, 
            "Customer_Organization_id": conversation_states[user_id]['customer_org_id']
        })
        org_id = new_org['organization_id']
        client.chat_postMessage(
            channel=channel_id,
            text=f"New organization '{text}' created with ID: {org_id}."
        )
        show_organizations(client, channel_id, conversation_states[user_id]['customer_org_id'])
        conversation_states[user_id]['state'] = 'awaiting_org_selection'
    except Exception as e:
        client.chat_postMessage(
            channel=channel_id,
            text=f"Error creating new organization: {str(e)}"
        )

def handle_signal(user_id, channel_id, text, client):
    try:
        org_ids = conversation_states[user_id]['selected_org_ids']
        user_response = call_api("/user/slack", method="GET", params={"slack_id": str(user_id)})
        if 'user_id' not in user_response:
            client.chat_postMessage(
                channel=channel_id,
                text="It looks like your Slack ID is not registered. Let's get you registered first."
            )
            show_users(client, channel_id, conversation_states[user_id]['customer_org_id'])
            conversation_states[user_id]['state'] = 'awaiting_user_selection'
            conversation_states[user_id]['pending_signal'] = {
                'text': text,
                'org_ids': org_ids
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

def handle_user_selection(user_id, channel_id, text, client):
    if text.lower() == 'new':
        client.chat_postMessage(
            channel=channel_id,
            text="Please enter the name for the new user:"
        )
        conversation_states[user_id]['state'] = 'awaiting_new_user_name'
    elif text.isdigit():
        try:
            register_response = call_api("/user/register", method="POST", json={
                "slack_id": str(conversation_states[user_id]['slack_id']),
                "user_id": int(text)
            })
            client.chat_postMessage(
                channel=channel_id,
                text=f"User registration successful. Your Slack ID {conversation_states[user_id]['slack_id']} has been linked to user ID {text}."
            )
            
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
                text=f"Error registering user: {str(e)}"
            )
    else:
        client.chat_postMessage(
            channel=channel_id,
            text="Invalid input. Please enter a valid user ID or 'new' to create a new user."
        )

def handle_new_user_name(user_id, channel_id, text, client):
    try:
        new_user = call_api("/user/create", method="POST", json={
            "name": text,
            "Customer_Organization_id": conversation_states[user_id]['customer_org_id']
        })
        if new_user and 'user_id' in new_user:
            created_user_id = new_user['user_id']
            register_response = call_api("/user/register", method="POST", params={
                "slack_id": str(conversation_states[user_id]['slack_id']),
                "user_id": created_user_id
            })
            if register_response is not None:
                client.chat_postMessage(
                    channel=channel_id,
                    text=f"New user '{text}' created with ID: {created_user_id} and user registration successful."
                )
                
                if 'pending_signal' in conversation_states[user_id]:
                    pending_signal = conversation_states[user_id]['pending_signal']
                    signal_response = call_api("/signal/create", method="POST", json={
                        "signal": pending_signal['text'],
                        "organization_ids": pending_signal['org_ids'],
                        "user_id": created_user_id,
                        "source": "Slack",
                        "type": "manual"
                    })
                    if signal_response is not None:
                        client.chat_postMessage(
                            channel=channel_id,
                            text=f"Pending signal added successfully: {signal_response}"
                        )
                    else:
                        client.chat_postMessage(
                            channel=channel_id,
                            text="Failed to add pending signal. Please try adding the signal again."
                        )
                
                del conversation_states[user_id]  # Clear the conversation state
            else:
                client.chat_postMessage(
                    channel=channel_id,
                    text="User created but registration failed. Please try registering again using the /register_user command."
                )
        else:
            client.chat_postMessage(
                channel=channel_id,
                text="Failed to create new user. Please try again or contact support."
            )
    except Exception as e:
        client.chat_postMessage(
            channel=channel_id,
            text=f"Error creating new user and registering: {str(e)}"
        )

def handle_customer_org_selection(user_id, channel_id, text, client):
    if text.lower() == 'new':
        client.chat_postMessage(
            channel=channel_id,
            text="Please enter the name for the new customer organization:"
        )
        conversation_states[user_id]['state'] = 'awaiting_new_customer_org_name'
    elif text.isdigit():
        try:
            register_response = call_api("/customerorganization/register", method="POST", params={
                "slack_id": str(conversation_states[user_id]['team_id']),
                "customer_organization_id": int(text)
            })
            if register_response is not None:
                client.chat_postMessage(
                    channel=channel_id,
                    text=f"Customer organization registration successful. Your Slack workspace has been linked to customer organization ID {text}."
                )
                del conversation_states[user_id]  # Clear the conversation state
            else:
                client.chat_postMessage(
                    channel=channel_id,
                    text="Failed to register customer organization. Please try again or contact support."
                )
        except Exception as e:
            client.chat_postMessage(
                channel=channel_id,
                text=f"Error registering customer organization: {str(e)}"
            )
    else:
        client.chat_postMessage(
            channel=channel_id,
            text="Invalid input. Please enter a valid customer organization ID or 'new' to create a new customer organization."
        )

def handle_new_customer_org_name(user_id, channel_id, text, client):
    try:
        new_org = call_api("/customerorganization/create", method="POST", json={
            "name": text
        })
        if new_org and 'customerorganization_id' in new_org:
            org_id = new_org['customerorganization_id']
            register_response = call_api("/customerorganization/register", method="POST", params={
                "slack_id": str(conversation_states[user_id]['team_id']),
                "customer_organization_id": org_id
            })
            if register_response is not None:
                client.chat_postMessage(
                    channel=channel_id,
                    text=f"New customer organization '{text}' created with ID: {org_id} and registered with your Slack workspace."
                )
                del conversation_states[user_id]  # Clear the conversation state
            else:
                client.chat_postMessage(
                    channel=channel_id,
                    text="Customer organization created but registration failed. Please try registering again using the /register_organization command."
                )
        else:
            client.chat_postMessage(
                channel=channel_id,
                text="Failed to create new customer organization. Please try again or contact support."
            )
    except Exception as e:
        client.chat_postMessage(
            channel=channel_id,
            text=f"Error creating and registering new customer organization: {str(e)}"
        )