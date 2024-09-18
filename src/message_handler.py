from config import conversation_states
from conversation_handlers import (
    handle_org_selection,
    handle_new_org_name,
    handle_signal,
    handle_user_selection,
    handle_new_user_name,
    handle_customer_org_selection,
    handle_new_customer_org_name
)

def register_message_handler(app):
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
                text="To start adding a signal, use the /add_signal command. "
                     "To register a user, use the /register_user command. "
                     "To register your organization, use the /register_organization command."
            )
            return

        state = conversation_states[user_id]['state']
        text = event['text'].strip()

        if state == 'awaiting_org_selection':
            handle_org_selection(user_id, channel_id, text, client)
        elif state == 'awaiting_new_org_name':
            handle_new_org_name(user_id, channel_id, text, client)
        elif state == 'awaiting_signal':
            handle_signal(user_id, channel_id, text, client)
        elif state == 'awaiting_user_selection':
            handle_user_selection(user_id, channel_id, text, client)
        elif state == 'awaiting_new_user_name':
            handle_new_user_name(user_id, channel_id, text, client)
        elif state == 'awaiting_customer_org_selection':
            handle_customer_org_selection(user_id, channel_id, text, client)
        elif state == 'awaiting_new_customer_org_name':
            handle_new_customer_org_name(user_id, channel_id, text, client)