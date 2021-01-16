from telethon import TelegramClient, events, errors
from dotenv import load_dotenv
import os
import shutil
import ratelimiter
import backoff
from telethon.errors.rpcerrorlist import ChannelInvalidError
from util import *
from collections import deque

load_dotenv()
# todo: check recently deleted before sending!

import logging

logging.basicConfig(
    format="[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s", level=logging.WARNING
)

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

client = TelegramClient("anon", API_ID, API_HASH)

# this is rate limiter to avoid flooding
# max_calls is number of outgoing messages / updates
# period is in seconds
# sweet spot is 15-20 / 1
limiter = ratelimiter.RateLimiter(max_calls=1, period=3)
temp_storage = {
    "recently_deleted": deque(maxlen=100),
    "recently_updated": BoundedOrderedDict(100),
    "broadcast_in_process": BoundedOrderedDict(10),
}

if not os.path.exists("./db.json"):
    shutil.copyfile("./db_template.json", "./db.json")


# limiting


@backoff.on_exception(
    backoff.expo, errors.FloodError, max_tries=100, jitter=backoff.random_jitter
)
async def send_ratelim(user_id, message, is_album=False):
    global temp_storage
    async with limiter:
        try:
            if not is_album:
                if (
                    not isinstance(message, str)
                    and message.id in temp_storage["recently_deleted"]
                ):
                    return []  # send nothing and return nothing
                message = await client.send_message(user_id, message)
                ids = [message.id]
            else:
                message.messages = [
                    m
                    for m in message.messages
                    if m.id not in temp_storage["recently_deleted"]
                ]
                message = await client.send_message(
                    user_id,
                    file=message.messages,
                    message=message.original_update.message.message,
                )
                ids = list(map(lambda x: getattr(x, "id"), message))
            return ids
        except errors.ForbiddenError:  # sub blacklisted the userchanel
            delete_sub(user_id)


@backoff.on_exception(
    backoff.expo, errors.FloodError, max_tries=100, jitter=backoff.random_jitter
)
async def delete_ratelim(user_id, user_message_id):
    async with limiter:
        try:
            if not isinstance(user_id, int):
                user_id = int(user_id)
            await client.delete_messages(user_id, user_message_id)
        except:
            pass  # idk what to do


@backoff.on_exception(
    backoff.expo, errors.FloodError, max_tries=100, jitter=backoff.random_jitter
)
async def edit_ratelim(user_id, user_message_id, channel_message_id, text_raw):
    global temp_storage
    async with limiter:
        try:
            if not isinstance(user_id, int):
                user_id = int(user_id)
            if channel_message_id in temp_storage["recently_updated"]:
                text_raw = temp_storage["recently_updated"][channel_message_id]
            await client.edit_message(user_id, user_message_id, text_raw)
        except:
            pass  # idk what to do, might add a callback later


# broadcasting


async def broadcast(message, is_album=False):
    global temp_storage
    con = db.get()
    ids_in_user_chat = {}
    if not is_album:
        channel_message_ids = [message.id]
    else:
        channel_message_ids = [m.id for m in message.messages]
    for i in channel_message_ids:
        temp_storage["broadcast_in_process"][i] = dict()
    for chat_id in con["subs"]:
        user_message_ids = await send_ratelim(chat_id, message, is_album)
        ids_in_user_chat[chat_id] = user_message_ids

        for i in channel_message_ids:
            temp_storage["broadcast_in_process"][i][chat_id] = user_message_ids

    for i in channel_message_ids:
        del temp_storage["broadcast_in_process"][i]
    return ids_in_user_chat


@client.on(
    events.NewMessage(
        func=validate_for_broadcast
    )
)
async def new_channel_handeler(event):
    print("Broadcasting!!1")
    con = db.get()
    if event.message.grouped_id is not None:
        return  # this is an album

    channel_message_id = event.message.id
    ids_in_user_chat = await broadcast(event.message)
    post_ids = {k: v[0] for k, v in ids_in_user_chat.items() if v}
    con["recent_messages"].insert(0, [channel_message_id, post_ids])
    con["recent_messages"] = con["recent_messages"][: con["recent_size"]]
    db.update(con)


@client.on(events.Album(func=validate_for_broadcast))
async def album_channel_handeler(event):
    con = db.get()
    ids_in_user_chat = await broadcast(event, is_album=True)
    channel_message_ids = map(lambda m: m.id, event)
    for idx, id in enumerate(channel_message_ids):
        post_ids = {k: v[idx] for k, v in ids_in_user_chat.items()}
        con["recent_messages"].insert(0, [id, post_ids])
    db.update(con)


@client.on(events.MessageDeleted(func=validate_for_broadcast))
async def delete_channel_handler(event):
    print("deleting!!!")
    global temp_storage
    con = db.get()
    for message_id in event.deleted_ids:
        if message_id in temp_storage["recently_deleted"]:
            continue
        else:
            temp_storage["recently_deleted"].append(message_id)
        if message_id in temp_storage["broadcast_in_process"]:
            delete_target = temp_storage["broadcast_in_process"]
        else:
            delete_target = con["recent_messages"]
        message = list(filter(lambda m: m[0] == message_id, con["recent_messages"]))
        if not message:
            await notify_failure(client, event.original_update.channel_id)
            continue
        _, recipiants = message[0]
        for user_id, user_message_id in recipiants.items():
            await delete_ratelim(user_id, user_message_id)
        con["recent_messages"] = list(
            filter(lambda m: m[0] != message_id, con["recent_messages"])
        )
    db.update(con)


@client.on(
    events.MessageEdited(func=validate_for_broadcast)
)
async def edit_channel_handler(event):
    global temp_storage
    print(event.stringify())
    con = db.get()
    message_id = event.message.id
    temp_storage["recently_updated"][message_id] = event.message.raw_text
    message = list(filter(lambda m: m[0] == message_id, con["recent_messages"]))
    if not message:
        channel_id = event.message.peer_id.channel_id
        await notify_failure(client, channel_id)
        return
    _, recipients = message[0]
    for chat_id, user_message_id in recipients.items():
        chat_id = int(chat_id)
        await edit_ratelim(chat_id, user_message_id, message_id, event.message.raw_text)


# commands


@client.on(events.NewMessage(pattern=r"^/start", func=lambda m: m.is_private))
async def start_handler(event):
    print("start")
    user_id = event.chat_id
    con = db.get()
    if con["max_sub_count"] <= len(con["subs"]):
        await send_ratelim(
            user_id, "We are full! Head over to @UserChannels and find another mirror!"
        )
        return
    if user_id not in con["subs"]:
        con["subs"].append(user_id)
        await send_ratelim(
            user_id, "You are now subbed to this channel! Send /stop to unsubscribe"
            "Warning: do not add me to your contacts and do not share your phone number with me"
        )
        db.update(con)
    else:
        await send_ratelim(user_id, "You are already subscribed! Use /stop to unsub")


@client.on(events.NewMessage(pattern=r"^/stop", func=lambda m: m.is_private))
async def stop_handler(event):
    user_id = event.original_update.user_id
    delete_sub(user_id)
    await send_ratelim(
        user_id, "Farawell! If you want to sub back, write /start to start again"
    )

client.start()
client.run_until_disconnected()
