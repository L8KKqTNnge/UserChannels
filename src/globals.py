from json import load
from .limited_client import LimitedClientWrapper
from .db import db
import ratelimiter
import os
from telethon import TelegramClient
from dotenv import load_dotenv

load_dotenv()

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
DB_PATH = os.getenv("DB_PATH")
MAX_CALLS = int(os.getenv("MAX_CALLS_PER_TIME_PERIOD"))
TIME_PERIOD = int(os.getenv("TIME_PERIOD"))


client = TelegramClient("anon", API_ID, API_HASH)
limiter = ratelimiter.RateLimiter(max_calls=MAX_CALLS, period=TIME_PERIOD)
limited_client = LimitedClientWrapper(client, limiter)
