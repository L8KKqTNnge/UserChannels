import json
from threading import RLock
import fcntl
import os
import shutil
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("DB_PATH")

db_schema = {"max_sub_count": int, "recent_size": int, "muted": bool}
db_description = {
    "max_sub_count": "Max number of the people subscribed, Integer",
    "recent_size": "Number of the recent messages. You can delete/edit only these messages, Integer",
    "muted": "Whether additional verbose replies of the bot are muted. Keep only one bot unmuted, Boolean",
}

if not os.path.exists(DB_PATH):
    shutil.copyfile("/".join(DB_PATH.split()[:-1]) + "db_template.json", DB_PATH)


class DB:
    def __init__(self):
        self.lock = RLock()
        self.path = os.getenv("DB_PATH")
        self._handle = open(self.path, "r+")

    def get(self):
        with self.lock:
            fcntl.flock(self._handle, fcntl.LOCK_EX)
            self._handle.seek(0)
            contents = json.load(self._handle)
            fcntl.flock(self._handle, fcntl.LOCK_UN)
            return contents

    def update(self, val):
        with self.lock:
            fcntl.flock(self._handle, fcntl.LOCK_EX)
            self._handle.seek(0)
            base = json.load(self._handle)
            base.update(val)
            self._handle.seek(0)
            json.dump(base, self._handle)
            self._handle.flush()
            self._handle.truncate()
            fcntl.flock(self._handle, fcntl.LOCK_UN)

    def delete_sub(self, user_id):
        con = self.get()
        if user_id in con["subs"]:
            con["subs"].remove(user_id)
            self.update(con)
        else:
            print("Warning: user to delete was not found!")


db = DB()
