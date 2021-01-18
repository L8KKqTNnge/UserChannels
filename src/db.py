import json
from threading import RLock
import fcntl
import os
import shutil
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("DB_PATH")

db_schema = {"max_sub_count": int, "recent_size": int, "hints_suppressed": bool}

if not os.path.exists(DB_PATH):
    shutil.copyfile("/".join(DB_PATH.split()[:-1]) + "db_template.json", DB_PATH)

"""
class DB:
    def __init__(self):
        self.lock = RLock()
        self.path = os.getenv("DB_PATH")
        # self._handle = open(self.path, "r+")

    def get(self):
        with self.lock:
            with open(self.path, "r") as handle:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                handle.seek(0)
                contents = json.load(handle)
                fcntl.flock(handle, fcntl.LOCK_UN)
                return contents

    def update(self, new):
        with self.lock:
            with open(self.path, "w") as handle:
                base = self.get()
                base.update(new)
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                handle.seek(0)
                json.dump(base,handle)
                print("just updated, !", base)
                fcntl.flock(handle, fcntl.LOCK_UN)
                os.fsync(handle.fileno())

    def delete_sub(self, user_id):
        con = self.get()
        if user_id in con["subs"]:
            con["subs"].remove(user_id)
            self.update(con)
        else:
            print("Warning: user to delete was not found!")
"""

class DB:
    def __init__(self):
        self.lock = RLock()
        self.path = os.getenv("DB_PATH")

    def get(self):
        with self.lock:
            with open(self.path, "r") as f:
                fcntl.flock(f, fcntl.LOCK_EX)
                contents = json.load(f)
                fcntl.flock(f, fcntl.LOCK_UN)
                return contents

    def update(self, val):
        with self.lock:
            with open(self.path, "r") as f:
                fcntl.flock(f, fcntl.LOCK_EX)
                base = json.load(f)
                base.update(val)
                fcntl.flock(f, fcntl.LOCK_UN)
            with open(self.path, "w") as f:
                fcntl.flock(f, fcntl.LOCK_EX)
                json.dump(base, f)
                fcntl.flock(f, fcntl.LOCK_UN)
    
    def delete_sub(self, user_id):
        con = self.get()
        if user_id in con["subs"]:
            con["subs"].remove(user_id)
            self.update(con)
        else:
            print("Warning: user to delete was not found!")


db = DB()