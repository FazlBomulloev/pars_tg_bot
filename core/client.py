from telethon import TelegramClient
from config import settings
from core.database import data_manager
from utils.logger import logger


client = None


async def init_client():
    global client
    data = data_manager.get_data()

    if (data["settings"]["use_account"] and
            data["settings"]["session_file"]):
        try:
            logger.info("Connecting to account...")
            client = TelegramClient(
                data["settings"]["session_file"],
                settings.API_ID,
                settings.API_HASH,
                device_model="Telegram Bot",
                system_version="1.0",
                app_version="1.0",
                lang_code="ru",
            )
            await client.connect()

            if not await client.is_user_authorized():
                logger.error("Account not authorized")
                data_manager.update_setting("use_account", False)
                return None
            else:
                logger.info("Account session restored successfully")
                return client
        except Exception as e:
            logger.error(f"Account connection error: {e}")
            data_manager.update_setting("use_account", False)
            return None

    client = TelegramClient("anon", settings.API_ID, settings.API_HASH)
    return client


def get_client():
    global client
    return client


def set_client(new_client):
    global client
    client = new_client