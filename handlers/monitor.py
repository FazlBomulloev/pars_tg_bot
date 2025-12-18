from telethon import events
from core.client import get_client
from core.database import data_manager
from core.bot import bot
from services.keyword_matcher import find_keyword_in_text
from services.notification import format_notification
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


async def handle_new_message(event):
    try:
        data = data_manager.get_data()

        if not data["settings"]["is_running"]:
            return

        if not data["settings"]["notifications"]:
            return

        message = event.message
        chat_id = message.chat_id

        if str(chat_id) not in data["sources"]:
            return

        text = getattr(message, "message", None)
        if not text:
            return

        keywords = data_manager.get_keywords()
        if not keywords:
            return

        keyword = find_keyword_in_text(text, keywords)
        if not keyword:
            return

        logger.info(f"Keyword '{keyword}' found in message {message.id}")

        try:
            client = get_client()
            sender = await message.get_sender()
            sender_id = message.sender_id
            sender_name = getattr(sender, "first_name", "Unknown")
            last_name = getattr(sender, "last_name", "")
            if last_name:
                sender_name += f" {last_name}"
            sender_username = getattr(sender, "username", None)

            source_data = data["sources"][str(chat_id)]
            message_link = await get_message_link(client, message)

            parent_channel = None
            if source_data["type"] == "discussion":
                parent_id = source_data.get("parent_channel")
                if parent_id:
                    parent_data = data["sources"].get(str(parent_id))
                    if parent_data:
                        parent_channel = parent_data["title"]

            notification_text, keyboard = format_notification(
                keyword=keyword,
                sender_id=sender_id,
                sender_name=sender_name,
                sender_username=sender_username,
                source_type=source_data["type"],
                source_title=source_data["title"],
                source_username=source_data.get("username"),
                message_text=text,
                message_link=message_link,
                parent_channel=parent_channel
            )

            for admin_id in data["settings"]["admins"]:
                try:
                    await bot.send_message(
                        admin_id,
                        notification_text,
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
                    logger.info(f"Notification sent to admin {admin_id}")
                except Exception as e:
                    logger.error(
                        f"Error sending notification to {admin_id}: {e}"
                    )

        except Exception as e:
            logger.error(f"Error processing message notification: {e}")

    except Exception as e:
        logger.error(f"Error in message handler: {e}")


async def setup_monitor():
    client = get_client()
    if not client:
        logger.error("Client not initialized")
        return

    if not client.is_connected():
        logger.warning("Client not connected, trying to connect...")
        try:
            await client.connect()
            logger.info("Client connected successfully")
        except Exception as e:
            logger.error(f"Client connection error: {e}")
            return

    is_authorized = await client.is_user_authorized()
    logger.info(f"Client authorized: {is_authorized}")

    source_ids = data_manager.get_all_source_ids()
    logger.info(f"Registered sources for monitoring: {len(source_ids)}")

    if not source_ids:
        logger.warning("No sources to monitor!")
        return

    if not data_manager.get_setting("is_running"):
        logger.info("Enabling parsing...")
        data_manager.update_setting("is_running", True)

    try:
        client.remove_event_handler(
            handle_new_message,
            events.NewMessage
        )
    except Exception:
        pass

    client.add_event_handler(
        handle_new_message,
        events.NewMessage(chats=source_ids)
    )
    logger.info("Message handler registered successfully")