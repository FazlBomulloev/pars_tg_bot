import asyncio
import re
from aiogram import types, F
from aiogram.fsm.context import FSMContext
from core.bot import dp
from core.client import get_client
from core.database import data_manager
from keyboards.inline import (
    get_sources_menu,
    get_back_button,
    get_admin_menu
)
from utils.states import AdminStates
from filters.admin import AdminFilter
from services.history_processor import process_source_history
from utils.logger import logger
from telethon.tl.functions.channels import JoinChannelRequest, GetFullChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.errors import (
    UserAlreadyParticipantError,
    UsernameNotOccupiedError,
    UsernameInvalidError,
    ChannelPrivateError,
    FloodWaitError,
    InviteHashExpiredError,
    InviteHashInvalidError
)


def extract_invite_hash(invite_link: str) -> str:
    """Извлекает хеш из инвайт ссылки"""
    patterns = [
        r't\.me/\+([A-Za-z0-9_-]+)',          # https://t.me/+HASH
        r't\.me/joinchat/([A-Za-z0-9_-]+)',   # https://t.me/joinchat/HASH
    ]
    
    for pattern in patterns:
        match = re.search(pattern, invite_link)
        if match:
            return match.group(1)
    
    return None


def is_invite_link(source_input: str) -> bool:
    """Проверяет, является ли ввод инвайт-ссылкой"""
    return 't.me/+' in source_input or 't.me/joinchat/' in source_input


async def join_by_invite_link(client, invite_link: str):
    """Вступает в группу/канал по инвайт ссылке"""
    invite_hash = extract_invite_hash(invite_link)
    
    if not invite_hash:
        raise ValueError("Некорректная инвайт ссылка")
    
    logger.info(f"🔗 Вступаем по инвайт ссылке: {invite_hash}")
    
    try:
        result = await client(ImportChatInviteRequest(invite_hash))
        
        # Результат может быть разным в зависимости от типа
        if hasattr(result, 'chats') and result.chats:
            chat = result.chats[0]
            return chat
        else:
            raise Exception("Не удалось получить информацию о чате")
            
    except UserAlreadyParticipantError:
        logger.info("ℹ️ Уже участник этой группы/канала")
        # Пытаемся получить entity другим способом
        # Нужно будет найти в диалогах
        raise Exception("Вы уже участник. Используйте username или ID для добавления")


async def subscribe_to_source(client, entity, account_number: str = "bot"):
    """Подписка на канал/группу"""
    try:
        # Если это канал
        if hasattr(entity, 'broadcast') and entity.broadcast:
            await client(JoinChannelRequest(entity))
            logger.info(f"[{account_number}] Subscribed to channel {entity.id}")
            return True
        # Если это группа/супергруппа
        elif hasattr(entity, 'megagroup'):
            await client(JoinChannelRequest(entity))
            logger.info(f"[{account_number}] Joined group {entity.id}")
            return True
        else:
            logger.warning(f"[{account_number}] Cannot auto-join regular chat {entity.id}")
            return False
    except UserAlreadyParticipantError:
        logger.info(f"[{account_number}] Already member of {entity.id}")
        return True
    except Exception as e:
        logger.error(f"[{account_number}] Error subscribing to {entity.id}: {e}")
        return False


async def find_discussion_group(client, channel_entity):
    """
    Находит группу обсуждений для канала
    Возвращает: (discussion_chat_id, discussion_title) или (None, None)
    """
    try:
        logger.info(f"🔍 Получаем полную информацию о канале {channel_entity.id}...")
        
        full_channel = await client(GetFullChannelRequest(channel=channel_entity))
        
        discussion_chat_id = getattr(full_channel.full_chat, "linked_chat_id", None)
        
        if discussion_chat_id:
            logger.info(f"💬 Found linked discussion group: {discussion_chat_id}")
            try:
                if discussion_chat_id < 0:
                    discussion_chat_id = abs(discussion_chat_id)
                
                discussion_entity = await client.get_entity(discussion_chat_id)
                discussion_title = getattr(discussion_entity, "title", "Discussion")
                
                final_id = -1000000000000 - discussion_chat_id if discussion_chat_id > 0 else discussion_chat_id
                
                return final_id, discussion_title
            except Exception as e:
                logger.error(f"❌ Error getting discussion entity: {e}")
                return None, None
        
        logger.info("ℹ️ No linked discussion group found for channel")
        return None, None
        
    except Exception as e:
        logger.error(f"❌ Error finding discussion group: {e}")
        return None, None


@dp.callback_query(F.data == "manage_sources", AdminFilter())
async def manage_sources(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "👥 Управление источниками:",
        reply_markup=get_sources_menu()
    )


@dp.callback_query(F.data == "add_source", AdminFilter())
async def add_source_start(
    callback: types.CallbackQuery,
    state: FSMContext
):
    await callback.message.edit_text(
        "📝 Отправьте username, ID или инвайт ссылку:\n\n"
        "Примеры:\n"
        "• @channel_name\n"
        "• -1001234567890\n"
        "• https://t.me/+xxxxxxxxxxx\n"
        "• https://t.me/joinchat/xxxxxxx"
    )
    await state.set_state(AdminStates.waiting_for_source)


@dp.message(AdminStates.waiting_for_source, AdminFilter())
async def process_add_source(
    message: types.Message,
    state: FSMContext
):
    source_input = message.text.strip()
    client = get_client()

    if not client or not client.is_connected():
        await message.answer(
            "❌ Сначала подключите аккаунт через настройки!"
        )
        await state.clear()
        await message.answer(
            "👋 Главное меню:",
            reply_markup=get_admin_menu()
        )
        return

    if not await client.is_user_authorized():
        await message.answer(
            "❌ Аккаунт не авторизован! Войдите через настройки."
        )
        await state.clear()
        await message.answer(
            "👋 Главное меню:",
            reply_markup=get_admin_menu()
        )
        return

    try:
        entity = None
        
        # Проверяем, инвайт ссылка ли это
        if is_invite_link(source_input):
            logger.info(f"🔗 Обнаружена инвайт ссылка")
            
            try:
                # Вступаем по инвайт ссылке
                entity = await join_by_invite_link(client, source_input)
                logger.info(f"✅ Успешно вступили через инвайт ссылку")
                
                # Небольшая задержка
                await asyncio.sleep(2)
                
            except InviteHashExpiredError:
                await message.answer("❌ Инвайт ссылка истекла")
                await state.clear()
                await message.answer("👋 Главное меню:", reply_markup=get_admin_menu())
                return
            except InviteHashInvalidError:
                await message.answer("❌ Инвайт ссылка недействительна")
                await state.clear()
                await message.answer("👋 Главное меню:", reply_markup=get_admin_menu())
                return
            except Exception as e:
                logger.error(f"❌ Ошибка при вступлении по инвайт ссылке: {e}")
                await message.answer(f"❌ Ошибка: {e}")
                await state.clear()
                await message.answer("👋 Главное меню:", reply_markup=get_admin_menu())
                return
        else:
            # Обычный username или ID
            entity = await client.get_entity(source_input)
            
            # Подписываемся
            logger.info(f"🔗 Подписываемся на {entity.title}...")
            subscription_result = await subscribe_to_source(client, entity, "bot")
            
            # Небольшая задержка после подписки
            await asyncio.sleep(2)

        # Получаем информацию об entity
        entity_id = entity.id
        entity_title = getattr(entity, "title", "Unknown")
        entity_username = getattr(entity, "username", None)

        is_channel = hasattr(entity, "broadcast") and entity.broadcast

        if is_channel:
            logger.info(f"📺 Обрабатываем канал: {entity_title}")
            
            # Ищем группу обсуждений
            discussion_chat_id, discussion_title = await find_discussion_group(client, entity)
            
            if discussion_chat_id:
                logger.info(f"💬 Найдена группа обсуждений: {discussion_title} (ID: {discussion_chat_id})")
                
                # Добавляем канал
                data_manager.add_source(
                    entity_id,
                    "channel",
                    entity_title,
                    entity_username,
                    discussion_chat_id=discussion_chat_id
                )

                try:
                    discussion_entity = await client.get_entity(discussion_chat_id)
                    discussion_title = getattr(discussion_entity, "title", "Discussion")
                    
                    # Подписываемся на группу обсуждений
                    logger.info(f"🔗 Подписываемся на группу обсуждений...")
                    discussion_subscription = await subscribe_to_source(
                        client, discussion_entity, "bot"
                    )
                    
                    # Добавляем группу обсуждений как отдельный источник
                    data_manager.add_source(
                        discussion_chat_id,
                        "discussion",
                        discussion_title,
                        None,
                        parent_channel=entity_id
                    )

                    await message.answer(
                        f"✅ Канал {entity_title} добавлен!\n"
                        f"├ ID: {entity_id}\n"
                        f"├ Username: @{entity_username or 'Нет'}\n"
                        f"└ Обсуждение: {discussion_title}\n"
                        f"   ├ ID: {discussion_chat_id}\n"
                        f"   └ {'✅ Подписка на обсуждение выполнена' if discussion_subscription else '⚠️ Не удалось подписаться на обсуждение'}\n\n"
                        "⏳ Обрабатываю историю комментариев..."
                    )

                    asyncio.create_task(
                        process_source_history(
                            client,
                            discussion_chat_id,
                            message.from_user.id
                        )
                    )
                    
                except Exception as e:
                    logger.error(f"❌ Ошибка обработки группы обсуждений: {e}")
                    await message.answer(
                        f"⚠️ Канал {entity_title} добавлен, но возникли проблемы с группой обсуждений:\n{e}"
                    )
            else:
                # Канал без обсуждений
                data_manager.add_source(
                    entity_id,
                    "channel",
                    entity_title,
                    entity_username
                )
                
                await message.answer(
                    f"✅ Канал {entity_title} добавлен!\n"
                    f"├ ID: {entity_id}\n"
                    f"├ Username: @{entity_username or 'Нет'}\n\n"
                    f"ℹ️ У канала нет группы обсуждений.\n"
                    "💡 Можете добавить её вручную как отдельный источник!"
                )
        else:
            # Это группа/чат
            logger.info(f"📱 Обрабатываем группу: {entity_title}")
            
            # Конвертируем ID в правильный формат
            if entity_id > 0:
                entity_id = -1000000000000 - entity_id
            
            data_manager.add_source(
                entity_id,
                "chat",
                entity_title,
                entity_username
            )

            await message.answer(
                f"✅ Группа {entity_title} добавлена!\n"
                f"├ ID: {entity_id}\n"
                f"├ Username: @{entity_username or 'Нет'}\n\n"
                "⏳ Обрабатываю историю сообщений..."
            )

            asyncio.create_task(
                process_source_history(
                    client,
                    entity_id,
                    message.from_user.id
                )
            )

    except UsernameNotOccupiedError:
        logger.error(f"Username не существует: {source_input}")
        await message.answer(f"❌ Источник {source_input} не существует")
    except UsernameInvalidError:
        logger.error(f"Некорректный username: {source_input}")
        await message.answer(f"❌ Некорректный username: {source_input}")
    except ChannelPrivateError:
        logger.error(f"Канал приватный: {source_input}")
        await message.answer(f"❌ Канал {source_input} приватный или недоступен")
    except FloodWaitError as e:
        logger.warning(f"FloodWait: нужно подождать {e.seconds} секунд")
        await message.answer(f"⏳ Нужно подождать {e.seconds} секунд перед добавлением источника")
    except Exception as e:
        logger.error(f"❌ Error adding source: {e}")
        await message.answer(f"❌ Ошибка при добавлении источника: {e}")

    await state.clear()
    await message.answer(
        "👋 Главное меню:",
        reply_markup=get_admin_menu()
    )


@dp.callback_query(F.data == "list_sources", AdminFilter())
async def list_sources(callback: types.CallbackQuery):
    data = data_manager.get_data()
    sources = data["sources"]

    if not sources:
        await callback.message.edit_text(
            "📝 Список источников пуст",
            reply_markup=get_back_button("manage_sources")
        )
        return

    text = "📝 Источники для мониторинга:\n\n"

    for i, (source_id, source_data) in enumerate(sources.items(), 1):
        source_type = source_data["type"]
        title = source_data["title"]
        username = source_data.get("username")
        processed = source_data.get("processed", False)

        if source_type == "chat":
            emoji = "📱"
            type_text = "Группа"
        elif source_type == "channel":
            emoji = "📺"
            type_text = "Канал"
        elif source_type == "discussion":
            emoji = "💬"
            type_text = "Обсуждение"
            parent_id = source_data.get("parent_channel")
            if parent_id and str(parent_id) in sources:
                parent_title = sources[str(parent_id)]["title"]
                type_text += f" ({parent_title})"
        else:
            emoji = "❓"
            type_text = "Неизвестно"

        text += f"{i}. {emoji} {title}"
        if username:
            text += f" (@{username})"
        text += f"\n   └ Тип: {type_text}\n"
        text += f"   └ История: {'✅' if processed else '❌'}\n\n"

    if len(text) > 4096:
        text = text[:4090] + "..."

    await callback.message.edit_text(
        text,
        reply_markup=get_back_button("manage_sources")
    )


@dp.callback_query(F.data == "delete_source", AdminFilter())
async def delete_source_start(
    callback: types.CallbackQuery,
    state: FSMContext
):
    data = data_manager.get_data()
    sources = data["sources"]

    if not sources:
        await callback.message.edit_text(
            "❌ Список источников пуст",
            reply_markup=get_back_button("manage_sources")
        )
        return

    text = "❌ Введите номер источника для удаления:\n\n"

    for i, (source_id, source_data) in enumerate(sources.items(), 1):
        title = source_data["title"]
        username = source_data.get("username")
        text += f"{i}. {title}"
        if username:
            text += f" (@{username})"
        text += "\n"

    await callback.message.edit_text(text)
    await state.set_state(AdminStates.waiting_for_source_delete)


@dp.message(AdminStates.waiting_for_source_delete, AdminFilter())
async def process_delete_source(
    message: types.Message,
    state: FSMContext
):
    try:
        index = int(message.text) - 1
        sources = list(data_manager.get_data()["sources"].keys())

        if 0 <= index < len(sources):
            source_id = sources[index]
            source_data = data_manager.get_data()["sources"][source_id]
            title = source_data["title"]

            if data_manager.remove_source(source_id):
                await message.answer(
                    f"✅ Источник '{title}' удален!"
                )
            else:
                await message.answer("❌ Ошибка при удалении источника!")
        else:
            await message.answer("❌ Неверный номер источника!")
    except ValueError:
        await message.answer("❌ Пожалуйста, введите корректный номер")

    await state.clear()
    await message.answer(
        "👋 Главное меню:",
        reply_markup=get_admin_menu()
    )
