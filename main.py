import asyncio
from core.bot import bot, dp
from core.client import init_client, get_client
from core.database import data_manager
from utils.logger import logger

from handlers import admin, sources, keywords, settings


async def on_startup():
    logger.info("Bot initialization started")

    data_manager.get_data()
    logger.info("Data loaded successfully")

    client = await init_client()
    if client:
        logger.info("Telethon client initialized")

        if not client.is_connected():
            await client.connect()
            logger.info("Telethon client connected")

        if client.is_connected():
            if await client.is_user_authorized():
                logger.info("User authorized in Telethon")

                from handlers.monitor import setup_monitor
                await setup_monitor()
            else:
                logger.warning("User not authorized in Telethon")
        else:
            logger.warning("Telethon client not connected")
    else:
        logger.warning("Telethon client not initialized")

    logger.info("Handlers registered")

    settings_data = data_manager.get_setting("is_running")
    if settings_data:
        logger.info("Parsing enabled")
    else:
        logger.warning("Parsing disabled")


async def run_telethon():
    """Запускает telethon client в фоне"""
    client = get_client()
    if client and client.is_connected():
        logger.info("Starting Telethon client loop...")
        await client.run_until_disconnected()
    else:
        logger.warning("Telethon client not available for running")


async def main():
    try:
        await on_startup()
        logger.info("Bot started successfully")
        
        # Запускаем aiogram и telethon параллельно
        client = get_client()
        if client and client.is_connected():
            logger.info("Running both aiogram and telethon...")
            await asyncio.gather(
                dp.start_polling(bot),
                run_telethon()
            )
        else:
            logger.warning("Running only aiogram (telethon not available)")
            await dp.start_polling(bot)
            
    except Exception as e:
        logger.error(f"Bot startup error: {e}")
    finally:
        # Закрываем соединения при остановке
        client = get_client()
        if client and client.is_connected():
            await client.disconnect()
            logger.info("Telethon client disconnected")


if __name__ == "__main__":
    asyncio.run(main())
