import backoff
from ratelimiter import RateLimiter
from telethon import errors, events
from telethon.client import TelegramClient
from collections import OrderedDict, deque
from .db import db


class MessageDeleted(Exception):
    def __init__(self, *args: object) -> None:
        super(Exception, self).__init__(*args)


class BoundedOrderedDict(OrderedDict):
    def __init__(self, maxsize=100):
        super(OrderedDict, self).__init__()
        self.maxsize = maxsize

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        if len(self) > self.maxsize:
            oldest = next(iter(self))
            del self[oldest]


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
        async with self.limiter:
            try:

                if not is_album:
                    if (
                        not isinstance(message, str)
                        and message.id in self.temp_storage["recently_deleted"]
                    ):
                        return []  # send nothing and return nothing
                    if (
                        not isinstance(message, str)
                        and message.id in self.temp_storage["recently_updated"]
                    ):
                        message.raw_text = self.temp_storage["recently_updated"][
                            message.id
                        ]

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

    @backoff.on_exception(
        backoff.expo, errors.FloodError, max_tries=100, jitter=backoff.random_jitter
    )
    async def broadcast(self, message):
        channel_message_id = 0
        ids_in_user_chat = 0
        try:
            con = db.get()
            ids_in_user_chat = {}
            channel_message_id = message.id
            self.temp_storage["broadcast_in_process"][channel_message_id] = dict()
            for chat_id in con["subs"]:
                user_message_ids = await self.send(chat_id, message)
                ids_in_user_chat[chat_id] = user_message_ids
                if channel_message_id in self.temp_storage["recently_deleted"]:
                    raise MessageDeleted
                else:
                    self.temp_storage["broadcast_in_process"][channel_message_id][
                        chat_id
                    ] = user_message_ids
        except MessageDeleted:
            for i in self.temp_storage["recently_deleted"]:
                if i in self.temp_storage["broadcast_in_process"]:
                    for chat_id, user_message_ids in self.temp_storage[
                        "broadcast_in_process"
                    ].items():
                        await self.delete(chat_id, user_message_ids)
        finally:
            if channel_message_id in self.temp_storage["broadcast_in_process"]:
                del self.temp_storage["broadcast_in_process"][channel_message_id]
            print(channel_message_id, ids_in_user_chat)
            return ids_in_user_chat

    async def broadcast_album(self, message):
        pass
