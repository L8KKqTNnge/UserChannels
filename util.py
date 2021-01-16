from collections import OrderedDict
from dotenv import load_dotenv
import os
import json
from threading import RLock

load_dotenv()


class DB:
    def __init__(self):
        self.lock = RLock()
        self.path = os.getenv("DB_PATH")

    def get(self):
        with self.lock:
            with open(self.path, "r") as f:
                return json.load(f)

    def update(self, val):
        with self.lock:
            with open(self.path, "r") as f:
                base = json.load(f)
                base.update(val)
            with open(self.path, "w") as f:
                json.dump(base, f)


db = DB()


def delete_sub(user_id):
    con = db.get()
    if user_id in con["subs"]:
        con["subs"].remove(user_id)
        db.update(con)
    else:
        print("Warning: user to delete was not found!")


async def notify_failure(client, channel_id):
    await client.send_message(
        channel_id,
        "<bot info> (not broadcasted)\n"
        "This message is too old and I do not have its references!",
    )


def validate_for_broadcast(event):
    return event.is_channel and "<bot info>" not in event.message.raw_text


class BoundedOrderedDict(OrderedDict):
    def __init__(self, maxsize=100):
        super(OrderedDict, self).__init__()
        self.maxsize = maxsize

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        if len(self) > self.maxsize:
            oldest = next(iter(self))
            del self[oldest]
