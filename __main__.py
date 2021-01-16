from telethon import TelegramClient, events, errors, hints
from dotenv import load_dotenv
import os
import shutil
import ratelimiter
import backoff
from util import *
from collections import deque
import pprint

load_dotenv()
# todo: check recently deleted before sending!

import logging

logging.basicConfig(
    format="[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s", level=logging.WARNING
)

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

db_schema = {"max_sub_count": int, "recent_size": int, "hints_suppressed": bool}

client = TelegramClient("anon", API_ID, API_HASH)
# this is rate limiter to avoid flooding
# max_calls is number of outgoing messages / updates
# period is in seconds
# sweet spot is 15-20 / 1
limiter = ratelimiter.RateLimiter(max_calls=15, period=1)
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
        except (errors.ForbiddenError):  # sub blacklisted the userchanel
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


@client.on(events.NewMessage(func=validate_for_broadcast))
async def new_channel_handler(event):
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
async def album_channel_handler(event):
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
        _, recipients = message[0]
        for user_id, user_message_id in recipients.items():
            await delete_ratelim(user_id, user_message_id)
        con["recent_messages"] = list(
            filter(lambda m: m[0] != message_id, con["recent_messages"])
        )
    db.update(con)


@client.on(events.MessageEdited(func=validate_for_broadcast))
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
            user_id,
            "You are now subbed to this channel! Send /stop to unsubscribe"
            "Warning: do not add me to your contacts and do not share your phone number with me",
        )
        db.update(con)
    else:
        await send_ratelim(user_id, "You are already subscribed! Use /stop to unsub")


@client.on(events.NewMessage(pattern=r"^/stop", func=lambda m: m.is_private))
async def stop_handler(event):
    user_id = event.original_update.user_id
    delete_sub(user_id)
    await send_ratelim(
        user_id, "Farewell! If you want to sub back, write /start to start again"
    )


@client.on(
    events.NewMessage(pattern=r"^/remove_blacklisted_subs", func=bot_channel_command)
)
async def remove_ignoring_handler(event):
    subs = db.get()["subs"]
    me = await client.get_entity("me")
    subs = db.get()["subs"]
    deleted = 0
    for i in subs:
        sub = await client.get_entity(i)
        if sub.status is None and sub.photo is None:
            delete_sub(sub.id)
            deleted += 1
    await event.reply("<bot info>: @{} deleted {} chats!".format(me.username, deleted))


@client.on(events.NewMessage(pattern=r"^/disable_hints", func=bot_channel_command))
async def remove_ignoring_handler(event):
    hints_suppressed = db.get()["hints_suppressed"]
    me = await client.get_entity("me")
    commands = event.message.raw_text.split()
    print(commands)
    if len(commands) != 2:
        if not hints_suppressed:
            await event.reply(
                "<bot info> @{}:\n command_usage: /disable_hints @bot_user_name".format(
                    me.username
                )
            )
        return
    target = commands[1]
    target = target[1:]
    print(target)
    if target == me.username:
        con = db.get()
        con["hints_suppressed"] = True
        hints_suppressed = True
        db.update(con)
        await event.reply(
            "<bot info>:\n @{0}: I will be quiet now \n"
            "use `/enable_hints @{0}` to enable me".format(me.username)
        )


@client.on(events.NewMessage(pattern=r"^/enable_hints", func=bot_channel_command))
async def enable_hints_handler(event):
    hints_suppressed = db.get()["hints_suppressed"]
    me = await client.get_entity("me")
    commands = event.message.raw_text.split()
    if len(commands) != 2:
        if not hints_suppressed:
            await event.reply(
                "<bot info> @{}:\n command_usage: /enable_hints @bot_user_name".format(
                    me.username
                )
            )
        return
    target = commands[1]
    target = target[1:]
    if target == me.username:
        con = db.get()
        con["hints_suppressed"] = False
        hints_suppressed = False
        db.update(con)
        await event.reply(
            "<bot info>:\n @{}: I will be the one informing you".format(me.username)
        )


@client.on(events.NewMessage(pattern=r"^/sub_count", func=bot_channel_command))
async def sub_cont_handler(event):
    me = await client.get_entity("me")
    con = db.get()
    await event.reply(
        "<bot info> @{}\n subs: {}/{}".format(
            me.username, len(con["subs"]), con["max_sub_count"]
        )
    )


@client.on(events.NewMessage(pattern=r"^/db_set", func=bot_channel_command))
async def db_set_handler(event):
    me = await client.get_entity("me")

    async def error():
        await event.reply(
            "<bot info> @{}:\n command_usage: /db_set @bot_user_name field value\n"
            "use @all to enforce db change to all of the bots!"
            "\nschema:\n {}".format(me.username, pprint.pformat(db_schema))
        )

    hints_suppressed = db.get()["hints_suppressed"]
    con = db.get()
    commands = event.message.raw_text.split()
    
    if len(commands) != 4:
        should_update = (me.username[1:] == commands[1] or commands[1] == "@all")
        if not should_update:
            if not hints_suppressed:
                await error()
            return
    field, value = commands[2], commands[3]
    if field not in db_schema:
        return
    if db_schema[field] is bool:
        if value in ["True", "true"]:
            value = True
        elif value in ["False", "false"]:
            value = False
        else:
            await error()
            return
    else:
        try:
            value = db_schema[field](value)
        except:
            await error()
            return
    if field == "max_sub_count" and len(con['subs']) >= value:
        await event.reply(f"<bot info>: sub count is less than people subscribed! Can't update...")
        return
    con[field] = value
    db.update(con)
    await event.reply(f"<bot info>: updated @{me.username}'s db field {field} to value {value}")


@client.on(events.NewMessage(pattern=r"^/db_get", func=bot_channel_command))
async def db_get_handler(event):
    con = db.get()
    me = await client.get_entity("me")
    con['subs'] = "hidden from log"
    con['recent_messages'] = "hidden from log"
    await event.reply("<bot info> @{} my db:\n {}".format(me.username, pprint.pformat(con)))




@client.on(events.NewMessage(pattern=r"^/help", func=bot_channel_command))
async def help_ignoring_handler(event):
    hints_suppressed = db.get()["hints_suppressed"]
    if hints_suppressed:
        return
    me = await client.get_entity("me")
    event.reply(
        f"<bot info>: @{me.username}\n"
        "Admin Commands: \n"
        "`/help` - show this list \n"
        "`/enable_hints @bot_user_name` - enables verbose from the bot. Keep only one bot verbose\n"
        "`/disable_hints @bot_user_name` - disables verbose from the bot. \n"
        "`/remove_blacklisted_subs` - remove subs, who have blacklisted the bot"
        "FAQ:\n"
        "Multiple bots reply on `/help`, etc: use `/disable_hints` with their username"
    )


client.start()
client.run_until_disconnected()
