import asyncio
import datetime
from functools import lru_cache
from tempfile import TemporaryDirectory
from telethon.tl import types as tg_types
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telethon import TelegramClient

from config import config_data, db, global_logger
from modify import modify_pic, modify_video

app_scheduler = AsyncIOScheduler()


async def running(tg_client):
    global_logger.debug("running")


@lru_cache(maxsize=10)
def calc_part_size(file_size):
    return round(round(file_size / 10) / 262144) * 262144


def action_progress_callback(action, current, total):
    part = calc_part_size(total)
    if current % part == 0 or current == 262144:
        global_logger.debug(
            f"{action} {current/1024/1024:.2f}/{total/1024/1024:.2f} MB"
        )


async def modify_message(message):
    global_logger.debug(message)
    if not message.media:
        return message
    media = message.media
    with TemporaryDirectory() as tempdir:
        if isinstance(media, (tg_types.MessageMediaPhoto, tg_types.Photo)):
            download_file = await message.download_media(file=tempdir)
            changed_photo = await modify_pic(download_file)
            message = await message.client.send_file(
                config_data["backup"]["cache"], changed_photo, caption=message.text
            )
            global_logger.debug(changed_photo)
            return message
        elif isinstance(media, (tg_types.MessageMediaDocument, tg_types.Document)):
            download_file = await message.download_media(
                file=tempdir,
                progress_callback=lambda x, y: action_progress_callback(
                    "downloading", x, y
                ),
            )
            thumbnail = await message.download_media(file=tempdir, thumb=-1)
            changed_video = await modify_video(download_file, tempdir)
            changed_thumbnail = await modify_pic(thumbnail)
            message = await message.client.send_file(
                config_data["backup"]["cache"],
                changed_video,
                thumb=changed_thumbnail,
                caption=message.text,
                supports_streaming=True,
                progress_callback=lambda x, y: action_progress_callback(
                    "uploading", x, y
                ),
                formatting_entities=message.entities or None,
            )

            return message


async def backup_msgs(tg_client: TelegramClient, messages, to_entity=None):
    if not messages:
        return
    messages = await asyncio.gather(*[modify_message(message) for message in messages])
    messages = [message for message in messages if message]
    if not messages:
        return
    file_messages = [message for message in messages if message.file]
    if not file_messages:
        file_messages = None
    caption = None
    format_entities = None
    for message in messages:
        if message.message:
            caption = message.message
            format_entities = message.entities

    await tg_client.send_message(
        to_entity,
        file=file_messages,
        message=caption,
        formatting_entities=format_entities,
    )


async def backup_channel(tg_client: TelegramClient, from_entity=None, to_entity=None):
    next_msg_id = db.get_next_msg_id(from_entity)
    a = tg_client.iter_messages(
        entity=from_entity,
        ids=range(next_msg_id, next_msg_id + config_data["backup"]["batch_size"]),
    )
    queue = []
    last_grouped_id = None
    last_msg_id = next_msg_id - 1
    now_msg_id = last_msg_id
    async for message in a:
        now_msg_id += 1
        if not message:
            if now_msg_id - last_msg_id >= 9:
                await backup_msgs(tg_client, queue.copy(), to_entity)
                queue.clear()
                db.set_next_msg_id(from_entity, now_msg_id)
                last_msg_id = now_msg_id - 1
        else:
            if (
                message.grouped_id is None
                or message.grouped_id != last_grouped_id
                or now_msg_id - last_msg_id >= 9
            ):
                await backup_msgs(tg_client, queue.copy(), to_entity)
                queue.clear()
                db.set_next_msg_id(from_entity, now_msg_id)
            # 如果是文件且大于2G就跳过
            if (
                message.file
                and isinstance(message.file.media, tg_types.Document)
                and message.file.media.size > 2 * 1024 * 1024 * 1024
            ):
                global_logger.debug(message.file.media)
            else:
                queue.append(message)
            last_msg_id = now_msg_id - 1
            last_grouped_id = (
                message.grouped_id if message.grouped_id else last_grouped_id
            )


async def backup(tg_client: TelegramClient):
    await asyncio.gather(
        *[
            backup_channel(tg_client, d["from"], d["to"])
            for d in config_data["channels"]
        ]
    )


async def start_scheduler(tg_client):
    app_scheduler.start()

    # app_scheduler.add_job(running, "interval", seconds=10, args=(tg_client,))
    app_scheduler.add_job(
        backup,
        "interval",
        args=(tg_client,),
        weeks=config_data["backup"]["interval"]["weeks"],
        days=config_data["backup"]["interval"]["days"],
        hours=config_data["backup"]["interval"]["hours"],
        minutes=config_data["backup"]["interval"]["minutes"],
        seconds=config_data["backup"]["interval"]["seconds"],
        next_run_time=datetime.datetime.now() + datetime.timedelta(seconds=2),
    )

    # await backup(tg_client)
