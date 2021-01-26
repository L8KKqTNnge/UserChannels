import pprint
from telethon import events
from ..db import db, db_schema, db_description
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
    muted = db.get()["muted"]
    me = await client.get_entity("me")
    commands = event.message.raw_text.split()
    print(commands)
    if len(commands) != 2:
        if not muted:
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
        con["muted"] = True
        muted = True
        db.update(con)
        await event.reply(
            "<bot info>:\n @{0}: I will be quiet now \n"
            "use `/enable_hints @{0}` to enable me".format(me.username)
        )


@events.register(events.NewMessage(pattern=r"^/enable_hints", func=bot_channel_command))
async def enable_hints_handler(event):
    client = event.client
    muted = db.get()["muted"]
    me = await client.get_entity("me")
    commands = event.message.raw_text.split()
    if len(commands) != 2:
        if not muted:
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
        con["muted"] = False
        muted = False
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

    muted = db.get()["muted"]
    con = db.get()
    commands = event.message.raw_text.split()

    if len(commands) != 4:
        should_update = me.username[1:] == commands[1] or commands[1] == "@all"
        if not should_update:
            if not muted:
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

    commands = event.message.raw_text.split()
    con["subs"] = "hidden from log"
    con["recent_messages"] = "hidden from log"

    if me.username[1:] == commands[1] or commands[1] == "@all":
        await event.reply(
            "<bot info> @{} my db:\n {}".format(me.username, pprint.pformat(con))
        )


@events.register(events.NewMessage(pattern=r"^/help", func=bot_channel_command))
async def help_handler(event):
    muted = db.get()["muted"]
    client = event.client
    if muted:
        return

    me = await client.get_entity("me")
    await event.reply(
        f"<bot info>: @{me.username}\n"
        "Admin Commands: \n"
        "`/help` - show this list \n"
        "`/unmute @bot_user_name` - enables verbose from the bot. Keep only one bot unmuted\n"
        "`/mute @bot_user_name` - disables verbose from the bot \n"
        "`/remove_blacklisted_subs` - remove subs, who have blacklisted the bot\n"
        "`/db_help - display a help for settings / db\n"
        "FAQ:\n"
        "Multiple bots reply on `/help` or other command: use `/mute` with their username"
    )


@events.register(events.NewMessage(pattern=r"^/db_help", func=bot_channel_command))
async def db_help_handler(event):
    muted = db.get()["muted"]
    client = event.client
    if muted:
        return

    me = await client.get_entity("me")
    db_fields = "\n".join([f"`{k}`" + " - " + v for k, v in db_description.items()])
    await event.reply(
        f"<bot info>: @{me.username}\n"
        "Admin Commands: \n"
        "Settings are stored here. Today the settings are the following:\n"
        f"{db_fields}\n"
        "\nCommands:\n"
        "`/db_help` - show this list \n"
        "`/db_set @bot_user_name field value` - sets a value to the bot. Use a username `@all` to set some value to all bots\n"
        "`/db_get @bot_user_name` - gets the database from the bot. Use a username `@all` to set some value to all bots\n"
        "Example: `/db_set @all max_sub_count 100`"
    )
