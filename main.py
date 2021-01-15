from telethon import TelegramClient, events, errors
from dotenv import load_dotenv
import os
import shutil
import ratelimiter
import backoff
from util import db, delete_sub

load_dotenv()

import logging

logging.basicConfig(
    format="[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s", level=logging.WARNING
)

api_id = os.getenv("API_ID")
api_hash = os.getenv("API_HASH")
channel_title = "testingchannel"
client = TelegramClient("anon", api_id, api_hash)
limiter = ratelimiter.RateLimiter(max_calls=15, period=1)

if not os.path.exists("./db.json"):
    shutil.copyfile("./db_template.json", "./db.json")

# limiting


@backoff.on_exception(backoff.expo, errors.FloodError, max_tries=8)
async def send_ratelim(user_id, message, is_album=False):
    with limiter:
        try:
            if not is_album:
                message = await client.send_message(user_id, message)
                ids = [message.id]
            else:
                message = await client.send_message(
                    user_id,
                    file=message.messages,
                    message=message.original_update.message.message,
                )
                ids = list(map(lambda x: getattr(x, 'id'), message))
                
            return ids
        except errors.ForbiddenError:
            delete_sub(user_id)

@backoff.on_exception(backoff.expo, errors.FloodError, max_tries=8)
async def delete_ratelim(user_id, message_id):
    with limiter:
        try:
            if not isinstance(user_id, int):
                user_id = int(user_id)
            await client.delete_messages(user_id, message_id)
        except:
            pass # idk what to do

@backoff.on_exception(backoff.expo, errors.FloodError, max_tries=8)
async def edit_ratelim(user_id, message_id, text_raw):
    with limiter:
        try:
            if not isinstance(user_id, int):
                user_id = int(user_id)
            await client.edit_message(user_id, message_id, text_raw)
        except:
            pass # idk what to d

# broadcasting


async def broadcast(event, is_album=False):
    con = db.get()
    event_ids = {}
    for chat_id in con["subs"]:
        local_event_id = await send_ratelim(chat_id, event, is_album)
        event_ids[chat_id] = local_event_id
    if not is_album:
        event_id = event.id
        con["recent_messages"].insert(0, [event_id, event_ids])
    else: 
        local_event_ids = map(lambda m: m.id, event.messages)
        for id in local_event_ids:
            con["recent_messages"].insert(0, [id, event_ids])
    con["recent_messages"] = con["recent_messages"][: con["recent_size"]]
    db.update(con)


@client.on(
    events.NewMessage(func=lambda m: m.is_channel and m.chat.title == channel_title)
)
async def new_channel_handeler(event):
    if event.message.grouped_id is not None:
        return  # this is an album
    await broadcast(event.message)


@client.on(events.Album(func=lambda m: m.is_channel and m.chat.title == channel_title))
async def albim_channel_handeler(event):
    await broadcast(event, is_album=True)


@client.on(events.MessageDeleted(func=lambda m: m.is_channel))
async def delete_channel_handler(event):
    con = db.get()
    for message_id in event.deleted_ids:
        if message_id in con['recently_deleted']:
            continue
        message = list(filter(lambda m: m[0] == message_id, con["recent_messages"]))
        if not message:
            await client.send_message(
                event.original_update.channel_id,
                "Bot info (not broadcasted)\n"
                "Attention: this message is too old and I do not have its references!"
                "Set 'recent_size' in bot settings to a higher value "
                "in order to increase recent messages references"
                "There is also a bug with album deletion, ignore if you deleted an album",
            )
            continue
        _, recipiants = message[0]
        for chat_id, message_in_chat_id in recipiants.items():
            await delete_ratelim(chat_id, message_in_chat_id)
        con["recently_deleted"] = (con["recently_deleted"] + [message_id])[:20]
        con["recent_messages"] = list(
            filter(lambda m: m[0] != message_id, con["recent_messages"])
        )
    db.update(con)


@client.on(
    events.MessageEdited(func=lambda m: m.is_channel and m.chat.title == channel_title)
)
async def update_channel_handler(event):
    con = db.get()
    message_id = event.message.id
    message = list(filter(lambda m: m[0] == message_id, con["recent_messages"]))
    if not message:
        await client.send_message(
            event.original_update.channel_id,
            "Bot info (not broadcasted)\n"
            "Attention: this message is too old and I do not have its references!"
            "Set 'recent_size' in bot settings to a higher value "
            "in order to increase recent messages references",
        )
        return
    _, recipients = message[0]
    for chat_id, message_id_in_chat in recipients.items():
        chat_id = int(chat_id)
        message_id_in_chat = message_id_in_chat[0]
        await edit_ratelim(chat_id, message_id_in_chat, event.message.raw_text)


# commands


@client.on(events.NewMessage(pattern=r"^/start", func=lambda m: m.is_private))
async def start_handler(event):
    print("start")
    user_id = event.chat_id
    con = db.get()
    if con['max_subs_count'] + 1 > len(con['subs']):
        await send_ratelim(
            user_id, "We are full! Head over to @UserChannels and find another mirror!"
        )
        return
    if user_id not in con["subs"]:
        con["subs"].append(user_id)
        await send_ratelim(
            user_id, "You are now subbed to this channel! Send /stop to unsubscribe"
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
