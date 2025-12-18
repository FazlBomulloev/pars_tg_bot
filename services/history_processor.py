import asyncio
from typing import Dict
from telethon import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest
from config import settings
from core.database import data_manager
from services.keyword_matcher import find_keyword_in_text
from services.notification import format_notification
from core.bot import bot
from utils.logger import logger


async def get_message_link(client, message) -> str:
    try:
        chat = await client.get_entity(message.chat_id)
        username = getattr(chat, "username", None)

        if username:
            return f"https://t.me/{username}/{message.id}"
        else:
            chat_id_str = str(message.chat_id).replace("-100", "")
            return f"https://t.me/c/{chat_id_str}/{message.id}"
    except Exception:
        return None


async def process_source_history(
    client: TelegramClient,
    source_id: int,
    admin_id: int
) -> Dict[str, int]:

    logger.info(f"Processing history for source {source_id}")

    result = {"processed": 0, "matches": 0}

    if data_manager.is_source_processed(source_id):
        logger.info(f"Source {source_id} already processed")
        return result

    try:
        source_data = data_manager.get_data()["sources"].get(
            str(source_id)
        )
        if not source_data:
            logger.error(f"Source {source_id} not found")
            return result

        keywords = data_manager.get_keywords()
        if not keywords:
            logger.warning("No keywords to search")
            return result

        offset_id = 0
        total_processed = 0

        while total_processed < settings.HISTORY_MESSAGES_LIMIT:
            try:
                history = await client(
                    GetHistoryRequest(
                        peer=source_id,
                        offset_id=offset_id,
                        offset_date=None,
                        add_offset=0,
                        limit=settings.MAX_MESSAGES_PER_REQUEST,
                        max_id=0,
                        min_id=0,
                        hash=0,
                    )
                )

                if not history.messages:
                    break

                for message in history.messages:
                    total_processed += 1
                    result["processed"] += 1

                    text = getattr(message, "message", None)
                    if not text:
                        continue

                    keyword = find_keyword_in_text(text, keywords)
                    if keyword:
                        result["matches"] += 1

                        try:
                            sender = await message.get_sender()
                            sender_id = message.sender_id
                            sender_name = getattr(
                                sender, "first_name", "Unknown"
                            )
                            last_name = getattr(sender, "last_name", "")
                            if last_name:
                                sender_name += f" {last_name}"
                            sender_username = getattr(
                                sender, "username", None
                            )

                            message_link = await get_message_link(
                                client, message
                            )

                            parent_channel = None
                            if source_data["type"] == "discussion":
                                parent_id = source_data.get(
                                    "parent_channel"
                                )
                                if parent_id:
                                    parent_data = data_manager.get_data()[
                                        "sources"
                                    ].get(str(parent_id))
                                    if parent_data:
                                        parent_channel = parent_data[
                                            "title"
                                        ]

                            notification_text, keyboard = (
                                format_notification(
                                    keyword=keyword,
                                    sender_id=sender_id,
                                    sender_name=sender_name,
                                    sender_username=sender_username,
                                    source_type=source_data["type"],
                                    source_title=source_data["title"],
                                    source_username=source_data.get(
                                        "username"
                                    ),
                                    message_text=text,
                                    message_link=message_link,
                                    parent_channel=parent_channel
                                )
                            )

                            await bot.send_message(
                                admin_id,
                                notification_text,
                                parse_mode="HTML",
                                reply_markup=keyboard
                            )

                        except Exception as e:
                            logger.error(
                                f"Error sending notification: {e}"
                            )

                if len(history.messages) < (
                    settings.MAX_MESSAGES_PER_REQUEST
                ):
                    break

                offset_id = history.messages[-1].id

                if total_processed >= settings.HISTORY_MESSAGES_LIMIT:
                    break

                await asyncio.sleep(settings.BATCH_DELAY)

            except Exception as e:
                logger.error(f"Error fetching history batch: {e}")
                break

        data_manager.mark_source_processed(source_id)
        logger.info(
            f"History processed: {result['processed']} messages, "
            f"{result['matches']} matches"
        )

        try:
            await bot.send_message(
                admin_id,
                f"✅ <b>Обработка истории завершена</b>\n\n"
                f"📊 Источник: {source_data['title']}\n"
                f"📝 Обработано сообщений: {result['processed']}\n"
                f"🔍 Найдено совпадений: {result['matches']}",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Error sending summary: {e}")

    except Exception as e:
        logger.error(f"Error processing history for {source_id}: {e}")

    return result