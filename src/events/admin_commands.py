import pprint
from telethon import events
from ..db import db, db_schema
from ..util import bot_channel_command


@events.register(
    events.NewMessage(pattern=r"^/remove_blacklisted_subs", func=bot_channel_command)
)
async def remove_ignoring_handler(event):
    client = event.client
    subs = db.get()["subs"]
    me = await client.get_entity("me")
    subs = db.get()["subs"]
    deleted = 0
    for i in subs:
        sub = await client.get_entity(i)
        if sub.status is None and sub.photo is None:
            db.delete_sub(sub.id)
            deleted += 1
    await event.reply("<bot info>: @{} deleted {} chats!".format(me.username, deleted))


@events.register(
    events.NewMessage(pattern=r"^/disable_hints", func=bot_channel_command)
)
async def disable_hints_handler(event):
    client = event.client
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


@events.register(events.NewMessage(pattern=r"^/enable_hints", func=bot_channel_command))
async def enable_hints_handler(event):
    client = event.client
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


@events.register(events.NewMessage(pattern=r"^/sub_count", func=bot_channel_command))
async def sub_cont_handler(event):
    client = event.client
    me = await client.get_entity("me")
    con = db.get()
    await event.reply(
        "<bot info> @{}\n subs: {}/{}".format(
            me.username, len(con["subs"]), con["max_sub_count"]
        )
    )


@events.register(events.NewMessage(pattern=r"^/db_set", func=bot_channel_command))
async def db_set_handler(event):
    client = event.client
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
        should_update = me.username[1:] == commands[1] or commands[1] == "@all"
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
    if field == "max_sub_count" and len(con["subs"]) >= value:
        await event.reply(
            f"<bot info>: sub count is less than people subscribed! Can't update..."
        )
        return
    con[field] = value
    db.update(con)
    await event.reply(
        f"<bot info>: updated @{me.username}'s db field {field} to value {value}"
    )


@events.register(events.NewMessage(pattern=r"^/db_get", func=bot_channel_command))
async def db_get_handler(event):
    client = event.client
    con = db.get()
    me = await client.get_entity("me")
    con["subs"] = "hidden from log"
    con["recent_messages"] = "hidden from log"
    await event.reply(
        "<bot info> @{} my db:\n {}".format(me.username, pprint.pformat(con))
    )


@events.register(events.NewMessage(pattern=r"^/help", func=bot_channel_command))
async def help_handler(event):
    hints_suppressed = db.get()["hints_suppressed"]
    client = event.client
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
