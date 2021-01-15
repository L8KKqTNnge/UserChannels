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
