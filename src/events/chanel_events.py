from ..globals import limited_client
from ..util import notify_failure, validate_for_broadcast
from ..db import db
from telethon import events


@events.register(events.NewMessage(func=validate_for_broadcast))
async def new_channel_handler(event):
    print("New message")
    con = db.get()
    channel_message_id = event.message.id

    if event.message.grouped_id is not None:
        return  # this is an album

    ids_in_user_chat = await limited_client.broadcast(event.message)
    post_ids = {k: v[0] for k, v in ids_in_user_chat.items() if v}

    con["recent_messages"].insert(0, [channel_message_id, post_ids])
    con["recent_messages"] = con["recent_messages"][: con["recent_size"]]

    db.update(con)


# for some reason events decorator does not register
# @events.register(events.Album)
@events.register(events.Album(func=validate_for_broadcast))
async def album_channel_handler(event):
    print("got an album!")
    con = db.get()
    ids_in_user_chat = await limited_client.broadcast(event)
    channel_message_ids = map(lambda m: m.id, event.messages)
    for idx, id in enumerate(channel_message_ids):
        post_ids = {k: v[idx] for k, v in ids_in_user_chat.items()}
        con["recent_messages"].insert(0, [id, post_ids])
    db.update(con)


@events.register(events.MessageDeleted(func=validate_for_broadcast))
async def delete_channel_handler(event):
    con = db.get()

    for message_id in event.deleted_ids:
        if message_id in limited_client.temp_storage["recently_deleted"]:
            continue
        else:
            limited_client.temp_storage["recently_deleted"].append(message_id)
            print(
                "Delete callback: Recently deleted",
                limited_client.temp_storage["recently_deleted"],
            )

        if message_id not in limited_client.temp_storage["broadcast_in_process"]:
            delete_target = con["recent_messages"]
            message = list(filter(lambda m: m[0] == message_id, delete_target))

            if not message:
                await notify_failure(event, event.original_update.channel_id)
                continue
            _, recipients = message[0]
            for user_id, user_message_id in recipients.items():
                await limited_client.delete(user_id, user_message_id)

            filtered = list(filter(lambda m: m[0] != message_id, delete_target))
            con["recent_messages"] = filtered
    db.update(con)


@events.register(events.MessageEdited(func=validate_for_broadcast))
async def edit_channel_handler(event):
    client = event.client
    con = db.get()
    message_id = event.message.id

    limited_client.temp_storage["recently_updated"][message_id] = event.message.raw_text

    message = list(filter(lambda m: m[0] == message_id, con["recent_messages"]))
    # message
    if not message:
        # check if it is being broadcasted
        if message_id in limited_client.temp_storage["broadcast_in_process"]:
            return
        else:  # it has been broadcasted, but not found in the recent messages
            channel_id = event.message.peer_id.channel_id
            await notify_failure(client, channel_id)
            return

    # message was broadcasted and found
    _, recipients = message[0]
    for chat_id, user_message_id in recipients.items():
        chat_id = int(chat_id)
        await limited_client.edit(
            chat_id, user_message_id, message_id, event.message.raw_text
        )
