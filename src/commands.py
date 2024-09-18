from api_client import get_customer_org_id
from utils import show_organizations, show_users, show_customer_organizations
from config import conversation_states

def register_commands(app):
    @app.command("/add_signal")
    def handle_add_signal_command(ack, say, command, client):
        ack()
        try:
            team_id = command['team_id']
            customer_org_id = get_customer_org_id(team_id)
            if not customer_org_id:
                say("Your Slack workspace is not registered. Please use the /register_organization command first.")
                return

            dm = client.conversations_open(users=[command['user_id']])
            dm_channel_id = dm['channel']['id']
            
            show_organizations(client, dm_channel_id, customer_org_id)
            
            conversation_states[command['user_id']] = {
                'state': 'awaiting_org_selection',
                'dm_channel_id': dm_channel_id,
                'selected_org_ids': [],
                'customer_org_id': customer_org_id
            }
        except Exception as e:
            say(f"Error starting signal addition process: {str(e)}", ephemeral=True)

    @app.command("/register_user")
    def handle_register_user_command(ack, say, command, client):
        ack()
        try:
            team_id = command['team_id']
            customer_org_id = get_customer_org_id(team_id)
            if not customer_org_id:
                say("Your Slack workspace is not registered. Please use the /register_organization command first.")
                return

            dm = client.conversations_open(users=[command['user_id']])
            dm_channel_id = dm['channel']['id']
            
            show_users(client, dm_channel_id, customer_org_id)
            
            conversation_states[command['user_id']] = {
                'state': 'awaiting_user_selection',
                'dm_channel_id': dm_channel_id,
                'slack_id': command['user_id'],
                'customer_org_id': customer_org_id
            }
        except Exception as e:
            say(f"Error starting user registration process: {str(e)}", ephemeral=True)

    @app.command("/register_organization")
    def handle_register_organization_command(ack, say, command, client):
        ack()
        try:
            team_id = command['team_id']
            customer_org_id = get_customer_org_id(team_id)
            
            if customer_org_id is not None:
                say(f"Your Slack workspace is already registered with customer organization ID: {customer_org_id}")
                return

            dm = client.conversations_open(users=[command['user_id']])
            dm_channel_id = dm['channel']['id']
            
            show_customer_organizations(client, dm_channel_id)
            
            conversation_states[command['user_id']] = {
                'state': 'awaiting_customer_org_selection',
                'dm_channel_id': dm_channel_id,
                'team_id': team_id
            }
        except Exception as e:
            say(f"Error starting organization registration process: {str(e)}", ephemeral=True)
    
    @app.command("/help")
    def handle_help_command(ack, say, command, client):
        ack()
        try:
            client.chat_postMessage(
                channel=command['channel_id'],
                text="I can respond to the following commands:\n"
                     "- /add_signal: Start adding a signal to a customer organization\n"
                     "- /register_user: Register your Slack ID with your user account\n"
                     "- /register_organization: Register your Slack workspace with a customer organization\n"
                     "- /help: Show this help message"
            )
        except Exception as e:
            logger.error(f"Error sending help message: {str(e)}")