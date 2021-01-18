from collections import OrderedDict
from dotenv import load_dotenv
import os

load_dotenv()

CHANNEL_NAME = os.getenv("CHANNEL_NAME")


async def notify_failure(client, channel_id):
    print("failed to send", channel_id)
    await client.send_message(
        channel_id,
        "<bot info> (not broadcasted)\n"
        "This message is too old and I do not have its references!",
    )


def validate_for_broadcast(event):
    if CHANNEL_NAME and event.chat and event.chat.title != CHANNEL_NAME:
        return False
    if event.message.raw_text and event.message.raw_text[0] == "/":
        return False
    return event.is_channel and "<bot info>" not in event.message.raw_text


def bot_channel_command(event):
    return not validate_for_broadcast(event) and event.is_channel


class BoundedOrderedDict(OrderedDict):
    def __init__(self, maxsize=100):
        super(OrderedDict, self).__init__()
        self.maxsize = maxsize

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        if len(self) > self.maxsize:
            oldest = next(iter(self))
            del self[oldest]
