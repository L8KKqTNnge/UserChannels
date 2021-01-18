import backoff
from ratelimiter import RateLimiter
from telethon import errors
from telethon.client import TelegramClient
from collections import deque
from .util import BoundedOrderedDict
from .db import db


class LimitedClientWrapper:
    def __init__(self, client: TelegramClient, limiter: RateLimiter) -> None:
        super().__init__()
        self.limiter = limiter
        self.client = client
        self.temp_storage = {
            "recently_deleted": deque(maxlen=100),
            "recently_updated": BoundedOrderedDict(100),
            "broadcast_in_process": BoundedOrderedDict(10),
        }

    @backoff.on_exception(
        backoff.expo, errors.FloodError, max_tries=100, jitter=backoff.random_jitter
    )
    async def send(self, user_id, message, is_album=False):
        global temp_storage
        async with self.limiter:
            try:
                if not is_album:
                    if (
                        not isinstance(message, str)
                        and message.id in self.temp_storage["recently_deleted"]
                    ):
                        return []  # send nothing and return nothing
                    message = await self.client.send_message(user_id, message)
                    ids = [message.id]
                else:
                    message.messages = [
                        m
                        for m in message.messages
                        if m.id not in self.temp_storage["recently_deleted"]
                    ]
                    message = await self.client.send_message(
                        user_id,
                        file=message.messages,
                        message=message.original_update.message.message,
                    )
                    ids = list(map(lambda x: getattr(x, "id"), message))
                return ids
            except (errors.ForbiddenError):  # sub blacklisted the userchanel
                db.delete_sub(user_id)

    @backoff.on_exception(
        backoff.expo, errors.FloodError, max_tries=100, jitter=backoff.random_jitter
    )
    async def delete(self, user_id, user_message_id):
        async with self.limiter:
            try:
                if not isinstance(user_id, int):
                    user_id = int(user_id)
                await self.client.delete_messages(user_id, user_message_id)
            except:
                pass  # idk what to do

    @backoff.on_exception(
        backoff.expo, errors.FloodError, max_tries=100, jitter=backoff.random_jitter
    )
    async def edit(self, user_id, user_message_id, channel_message_id, text_raw):
        async with self.limiter:
            try:
                if not isinstance(user_id, int):
                    user_id = int(user_id)
                if channel_message_id in self.temp_storage["recently_updated"]:
                    text_raw = self.temp_storage["recently_updated"][channel_message_id]
                await self.client.edit_message(user_id, user_message_id, text_raw)
            except:
                pass  # idk what to do, might add a callback later

    async def broadcast(self, message, is_album=False):
        con = db.get()
        ids_in_user_chat = {}
        if not is_album:
            channel_message_ids = [message.id]
        else:
            channel_message_ids = [m.id for m in message.messages]
        for i in channel_message_ids:
            self.temp_storage["broadcast_in_process"][i] = dict()
        for chat_id in con["subs"]:
            user_message_ids = await self.send(chat_id, message, is_album)
            ids_in_user_chat[chat_id] = user_message_ids

            for i in channel_message_ids:
                self.temp_storage["broadcast_in_process"][i][chat_id] = user_message_ids

        for i in channel_message_ids:
            del self.temp_storage["broadcast_in_process"][i]
        return ids_in_user_chat
