from aiogram import types, F
from aiogram.fsm.context import FSMContext
from telethon import TelegramClient
from core.bot import dp
from core.client import get_client, set_client
from core.database import data_manager
from keyboards.inline import (
    get_settings_menu,
    get_admin_menu,
    get_back_button
)
from utils.states import AdminStates
from filters.admin import AdminFilter
from config import settings
from utils.logger import logger


@dp.callback_query(F.data == "settings", AdminFilter())
async def show_settings(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "⚙️ Настройки:",
        reply_markup=get_settings_menu()
    )


@dp.callback_query(F.data == "toggle_notifications", AdminFilter())
async def toggle_notifications(callback: types.CallbackQuery):
    current = data_manager.get_setting("notifications")
    new_value = not current
    data_manager.update_setting("notifications", new_value)

    await callback.answer(
        f"{'🔔' if new_value else '🔕'} Уведомления "
        f"{'включены' if new_value else 'выключены'}"
    )

    await callback.message.edit_text(
        "⚙️ Настройки:",
        reply_markup=get_settings_menu()
    )


@dp.callback_query(F.data == "export_data", AdminFilter())
async def export_data(callback: types.CallbackQuery):
    try:
        with open(settings.DATA_FILE, "r", encoding="utf-8") as f:
            await callback.message.answer_document(
                types.BufferedInputFile(
                    f.read().encode(),
                    filename="data_export.json"
                ),
                caption="📤 Экспорт данных",
            )
    except Exception as e:
        await callback.answer(f"❌ Ошибка при экспорте: {str(e)}")


@dp.callback_query(F.data == "toggle_account", AdminFilter())
async def toggle_account(
    callback: types.CallbackQuery,
    state: FSMContext
):
    use_account = data_manager.get_setting("use_account")

    if not use_account:
        await callback.message.edit_text(
            "📱 Подключение аккаунта\n\n"
            "⚠️ Важно знать:\n"
            "• Это безопасное подключение\n"
            "• Не выкинет вас с других устройств\n"
            "• Используется только для чтения сообщений\n\n"
            "Введите номер телефона в международном формате:\n"
            "Например: +79001234567"
        )
        await state.set_state(AdminStates.waiting_for_phone)
    else:
        try:
            client = get_client()
            if client:
                await client.disconnect()

            data_manager.update_setting("use_account", False)
            data_manager.update_setting("phone", None)
            data_manager.update_setting("session_file", None)

            await callback.answer("❌ Аккаунт отключен")
        except Exception as e:
            await callback.answer(f"❌ Ошибка при отключении: {e}")

        await callback.message.edit_text(
            "⚙️ Настройки:",
            reply_markup=get_settings_menu()
        )


@dp.message(AdminStates.waiting_for_phone, AdminFilter())
async def process_phone(message: types.Message, state: FSMContext):
    phone = message.text.strip()

    if not phone.startswith("+"):
        await message.answer("❌ Номер должен начинаться с '+'")
        return

    try:
        session_file = f"session_{message.from_user.id}"
        data_manager.update_setting("session_file", session_file)

        client = TelegramClient(
            session_file,
            settings.API_ID,
            settings.API_HASH,
            device_model="Telegram Bot",
            system_version="1.0",
            app_version="1.0",
            lang_code="ru",
        )

        await client.connect()
        set_client(client)

        send_code_result = await client.send_code_request(phone)
        await state.update_data(
            phone_code_hash=send_code_result.phone_code_hash,
            phone=phone
        )

        await message.answer(
            "📱 Код подтверждения отправлен в Telegram.\n"
            "Пожалуйста, введите код:"
        )
        await state.set_state(AdminStates.waiting_for_code)

    except Exception as e:
        logger.error(f"Error sending code: {e}")
        await message.answer(f"❌ Ошибка при отправке кода: {e}")
        await state.clear()
        await message.answer(
            "👋 Главное меню:",
            reply_markup=get_admin_menu()
        )


@dp.message(AdminStates.waiting_for_code, AdminFilter())
async def process_code(message: types.Message, state: FSMContext):
    try:
        code = message.text.strip()
        state_data = await state.get_data()
        phone = state_data.get("phone")
        phone_code_hash = state_data.get("phone_code_hash")

        if not phone_code_hash:
            raise Exception("Hash not found. Please restart.")

        client = get_client()
        await client.sign_in(phone, code, phone_code_hash=phone_code_hash)

        data_manager.update_setting("use_account", True)

        await message.answer(
            "✅ Успешный вход в аккаунт!\n"
            "Теперь бот может мониторить источники."
        )
        await state.clear()
        await message.answer(
            "👋 Главное меню:",
            reply_markup=get_admin_menu()
        )

    except Exception as e:
        error_str = str(e)
        if "2FA" in error_str or "password" in error_str.lower():
            await message.answer(
                "🔐 Требуется пароль двухэтапной аутентификации.\n"
                "Пожалуйста, введите пароль:"
            )
            await state.set_state(AdminStates.waiting_for_2fa)
        else:
            logger.error(f"Sign in error: {e}")
            await message.answer(f"❌ Ошибка при входе: {e}")
            await state.clear()
            await message.answer(
                "👋 Главное меню:",
                reply_markup=get_admin_menu()
            )


@dp.message(AdminStates.waiting_for_2fa, AdminFilter())
async def process_2fa(message: types.Message, state: FSMContext):
    try:
        password = message.text.strip()
        client = get_client()
        await client.sign_in(password=password)

        data_manager.update_setting("use_account", True)

        await message.answer(
            "✅ Успешный вход в аккаунт!\n"
            "Теперь бот может мониторить источники."
        )
    except Exception as e:
        logger.error(f"2FA error: {e}")
        await message.answer(f"❌ Ошибка при вводе пароля: {e}")

    await state.clear()
    await message.answer(
        "👋 Главное меню:",
        reply_markup=get_admin_menu()
    )


@dp.callback_query(F.data == "process_history", AdminFilter())
async def process_history_start(callback: types.CallbackQuery, state: FSMContext):
    """Показывает список источников для выбора"""
    client = get_client()
    if not client or not client.is_connected():
        await callback.message.edit_text(
            "❌ Клиент не подключен!",
            reply_markup=get_admin_menu()
        )
        return

    sources = data_manager.get_data()["sources"]
    
    if not sources:
        await callback.answer("❌ Нет источников для обработки", show_alert=True)
        return

    # Формируем список источников с разбивкой по сообщениям
    sources_list = list(sources.items())
    messages_text = []
    current_text = "📋 Выберите источники для обработки истории:\n\n"
    current_text += "Введите номера через пробел или запятую\n"
    current_text += "Например:1 3 5 или 1,3,5\n"
    current_text += "Или введите все для обработки всех источников\n\n"
    
    for i, (source_id, source_data) in enumerate(sources_list, 1):
        source_type = source_data["type"]
        title = source_data["title"]
        username = source_data.get("username")
        processed = source_data.get("processed", False)
        
        if source_type == "chat":
            emoji = "📱"
        elif source_type == "channel":
            emoji = "📺"
        elif source_type == "discussion":
            emoji = "💬"
        else:
            emoji = "❓"
        
        status_emoji = "✅" if processed else "❌"
        
        line = f"{i}. {emoji} {title}"
        if username:
            line += f" (@{username})"
        line += f" {status_emoji}\n"
        
        # Проверяем, не превысит ли добавление строки лимит в 4096 символов
        if len(current_text + line) > 4000:
            messages_text.append(current_text)
            current_text = line
        else:
            current_text += line
    
    # Добавляем последнее сообщение
    if current_text:
        messages_text.append(current_text)
    
    # Отправляем все сообщения
    await callback.message.delete()
    
    for text in messages_text:
        await callback.message.answer(text)
    
    # Сохраняем источники в state для дальнейшей обработки
    await state.update_data(sources_list=sources_list)
    await state.set_state(AdminStates.waiting_for_history_selection)


@dp.message(AdminStates.waiting_for_history_selection, AdminFilter())
async def process_history_selection(message: types.Message, state: FSMContext):
    """Обрабатывает выбор источников"""
    user_input = message.text.strip().lower()
    state_data = await state.get_data()
    sources_list = state_data.get("sources_list", [])
    
    if not sources_list:
        await message.answer("❌ Ошибка: список источников пуст")
        await state.clear()
        return
    
    selected_indices = []
    
    # Если пользователь ввел "все"
    if user_input in ["все", "all", "всі"]:
        selected_indices = list(range(len(sources_list)))
    else:
        # Парсим ввод (через пробел или запятую)
        try:
            # Заменяем запятые на пробелы и разбиваем
            numbers_str = user_input.replace(",", " ").split()
            numbers = [int(num) for num in numbers_str]
            
            # Проверяем валидность номеров
            for num in numbers:
                if 1 <= num <= len(sources_list):
                    selected_indices.append(num - 1)  # Индексы с 0
                else:
                    await message.answer(
                        f"⚠️ Номер {num} вне диапазона (1-{len(sources_list)})"
                    )
                    return
        except ValueError:
            await message.answer(
                "❌ Некорректный ввод!\n"
                "Введите номера через пробел или запятую\n"
                "Например: <code>1 3 5</code> или <code>1,3,5</code>"
            )
            return
    
    if not selected_indices:
        await message.answer("❌ Не выбрано ни одного источника")
        return
    
    # Запускаем обработку выбранных источников
    client = get_client()
    if not client or not client.is_connected():
        await message.answer("❌ Клиент не подключен!")
        await state.clear()
        return
    
    # Сбрасываем флаг processed для выбранных источников
    for idx in selected_indices:
        source_id = sources_list[idx][0]
        data_manager.get_data()["sources"][source_id]["processed"] = False
    data_manager.save_data()
    
    await message.answer(
        f"⏳ Запускаю обработку истории для {len(selected_indices)} источников...\n"
        "Это может занять некоторое время."
    )
    
    from services.history_processor import process_source_history
    import asyncio
    
    # Запускаем обработку в фоне
    for idx in selected_indices:
        source_id, source_data = sources_list[idx]
        asyncio.create_task(
            process_source_history(
                client,
                int(source_id),
                message.from_user.id
            )
        )
        logger.info(f"Started history processing for source {source_id} ({source_data['title']})")
    
    await state.clear()
    await message.answer(
        "✅ Обработка истории запущена в фоне!\n"
        "Вы получите уведомления по завершению каждого источника.",
        reply_markup=get_admin_menu()
    )


@dp.callback_query(F.data == "stats", AdminFilter())
async def show_stats(callback: types.CallbackQuery):
    data = data_manager.get_data()
    sources = data["sources"]
    keywords = data["keywords"]
    settings_data = data["settings"]

    stats_text = (
        "📊 Статистика:\n\n"
        f"👥 Источников: {len(sources)}\n"
        f"🔑 Ключевых слов: {len(keywords)}\n\n"
        f"⚙️ Настройки:\n"
        f"├ Парсинг: {'✅' if settings_data['is_running'] else '❌'}\n"
        f"├ Уведомления: "
        f"{'✅' if settings_data['notifications'] else '❌'}\n"
        f"└ Аккаунт: "
        f"{'✅' if settings_data['use_account'] else '❌'}"
    )

    await callback.message.edit_text(
        stats_text,
        reply_markup=get_admin_menu()
    )


@dp.callback_query(F.data == "start_parsing", AdminFilter())
async def start_parsing(callback: types.CallbackQuery):
    if data_manager.get_setting("is_running"):
        await callback.answer("⚠️ Парсинг уже запущен!")
        return

    data_manager.update_setting("is_running", True)
    await callback.message.edit_text(
        "✅ Парсинг запущен!\n"
        "Бот отслеживает сообщения в добавленных источниках.",
        reply_markup=get_admin_menu()
    )


@dp.callback_query(F.data == "stop_parsing", AdminFilter())
async def stop_parsing(callback: types.CallbackQuery):
    if not data_manager.get_setting("is_running"):
        await callback.answer("⚠️ Парсинг уже остановлен!")
        return

    data_manager.update_setting("is_running", False)
    await callback.message.edit_text(
        "🛑 Парсинг остановлен!\n"
        "Бот больше не отслеживает сообщения.",
        reply_markup=get_admin_menu()
    )
