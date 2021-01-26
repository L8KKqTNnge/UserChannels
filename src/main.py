from dotenv import load_dotenv
from .util import *
from .globals import client
from .events.admin_commands import *
from .events.chanel_events import *
from .events.user_commands import *

load_dotenv()

import logging

logging.basicConfig(
    format="[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s", level=logging.WARNING
)

with client as c:
    c.add_event_handler(album_channel_handler)
    c.add_event_handler(remove_ignoring_handler)
    c.add_event_handler(disable_hints_handler)
    c.add_event_handler(enable_hints_handler)
    c.add_event_handler(sub_cont_handler)
    c.add_event_handler(db_set_handler)
    c.add_event_handler(db_get_handler)
    c.add_event_handler(help_handler)
    c.add_event_handler(db_help_handler)
    c.add_event_handler(new_channel_handler)
    c.add_event_handler(delete_channel_handler)
    c.add_event_handler(edit_channel_handler)
    c.add_event_handler(start_user_handler)
    c.add_event_handler(stop_user_handler)
    c.run_until_disconnected()
