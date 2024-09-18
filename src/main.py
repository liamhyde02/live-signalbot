import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from config import SLACK_BOT_TOKEN, SLACK_APP_TOKEN
from commands import register_commands
from message_handler import register_message_handler

# Create the Slack app
app = App(token=SLACK_BOT_TOKEN)

# Register commands and message handler
register_commands(app)
register_message_handler(app)

if __name__ == "__main__":
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()