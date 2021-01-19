from collections import OrderedDict
from dotenv import load_dotenv
from .globals import client
import os

load_dotenv()

CHANNEL_NAME = os.getenv("CHANNEL_NAME")


async def notify_failure(event, channel_id):
    me = await client.get_entity("me")
    await event.reply(
        channel_id,
        f"<bot info>: @{me.username} (not broadcasted)\n"
        "This message is too old and I do not have its references!",
    )


def validate_for_broadcast(event):
    if CHANNEL_NAME and event.chat and event.chat.title != CHANNEL_NAME:
        return False
    if hasattr(event, 'message') and event.message.raw_text :
        if event.message.raw_text[0] == '/' or "<bot info>" in event.message.raw_text:
            return False
    return event.is_channel


def bot_channel_command(event):
    return not validate_for_broadcast(event) and event.is_channel


