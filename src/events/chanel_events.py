from ..globals import limited_client
from ..util import validate_for_broadcast, notify_failure
from ..db import db
from telethon import events


@events.register(events.NewMessage(func=validate_for_broadcast))
async def new_channel_handler(event):
    con = db.get()
    if event.message.grouped_id is not None:
        return  # this is an album
    channel_message_id = event.message.id
    ids_in_user_chat = await limited_client.broadcast(event.message)
    post_ids = {k: v[0] for k, v in ids_in_user_chat.items() if v}
    con["recent_messages"].insert(0, [channel_message_id, post_ids])
    con["recent_messages"] = con["recent_messages"][: con["recent_size"]]
    db.update(con)


@events.register(events.Album(func=validate_for_broadcast))
async def album_channel_handler(event):
    con = db.get()
    ids_in_user_chat = await limited_client.broadcast(event, is_album=True)
    channel_message_ids = map(lambda m: m.id, event)
    for idx, id in enumerate(channel_message_ids):
        post_ids = {k: v[idx] for k, v in ids_in_user_chat.items()}
        con["recent_messages"].insert(0, [id, post_ids])
    db.update(con)


@events.register(events.MessageDeleted(func=validate_for_broadcast))
async def delete_channel_handler(event):
    client = event.client
    con = db.get()
    temp_storage = limited_client.temp_storage
    for message_id in event.deleted_ids:
        if message_id in temp_storage["recently_deleted"]:
            continue
        else:
            temp_storage["recently_deleted"].append(message_id)
        if message_id in temp_storage["broadcast_in_process"]:
            delete_target = temp_storage["broadcast_in_process"]
        else:
            delete_target = con["recent_messages"]
        # todo !
        message = list(filter(lambda m: m[0] == message_id, con["recent_messages"]))
        if not message:
            await notify_failure(client, event.original_update.channel_id)
            continue
        _, recipients = message[0]
        for user_id, user_message_id in recipients.items():
            await limited_client.delete(user_id, user_message_id)
        con["recent_messages"] = list(
            filter(lambda m: m[0] != message_id, con["recent_messages"])
        )
    db.update(con)


@events.register(events.MessageEdited(func=validate_for_broadcast))
async def edit_channel_handler(event):
    client = event.client
    temp_storage = limited_client['temp_storage']
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
        await limited_client.edit(
            chat_id, user_message_id, message_id, event.message.raw_text
        )

