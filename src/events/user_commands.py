from telethon import events
from ..db import db
from ..globals import limited_client


@events.register(events.NewMessage(pattern=r"^/start", func=lambda m: m.is_private))
async def start_user_handler(event):
    print("start")
    user_id = event.chat_id
    con = db.get()
    if con["max_sub_count"] <= len(con["subs"]):
        await limited_client.send(
            user_id, "We are full! Head over to @UserChannels and find another mirror!"
        )
        return
    if user_id not in con["subs"]:
        con["subs"].append(user_id)
        db.update(con)
        await limited_client.send(
            user_id,
            "You are now subbed to this channel! Send /stop to unsubscribe"
            "Warning: do not add me to your contacts and do not share your phone number with me",
        )
        print("updated", con)
    else:
        await limited_client.send(
            user_id, "You are already subscribed! Use /stop to unsub"
        )


@events.register(events.NewMessage(pattern=r"^/stop", func=lambda m: m.is_private))
async def stop_user_handler(event):
    user_id = event.original_update.user_id
    db.delete_sub(user_id)
    await limited_client.send(
        user_id, "Farewell! If you want to sub back, write /start to start again"
    )
