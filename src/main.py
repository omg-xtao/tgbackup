import telethon
from telethon import TelegramClient
from telethon.events import NewMessage

import scheduler
from config import config_data, db
from scheduler import start_scheduler, backup_channel

used_proxy = (
    {
        "proxy_type": config_data["proxy"][
            "proxy_type"
        ],  # (mandatory) protocol to use (see above)
        "addr": config_data["proxy"]["addr"],  # (mandatory) proxy IP address
        "port": config_data["proxy"]["port"],  # (mandatory) proxy port number
    }
    if config_data["proxy"]["enable"]
    else None
)

client = TelegramClient(
    config_data["session_file"],
    config_data["API_ID"],
    config_data["API_HASH"],
    proxy=used_proxy,
).start(bot_token=config_data["bot_token"])


@client.on(NewMessage(chats=[d["from"] for d in config_data["channels"]]))
async def rollback_next_msg_id(event):
    peer_id = telethon.utils.get_peer_id(event.message.input_chat)
    if db.get_next_msg_id(peer_id) > event.message.id:
        db.set_next_msg_id(peer_id, event.message.id)


@client.on(NewMessage(pattern=r"^/run_once", incoming=True))
async def run_once(event):
    await scheduler.backup(event.client)


if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(start_scheduler(client))
        client.run_until_disconnected()
