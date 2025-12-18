from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from core.database import data_manager


def get_admin_menu() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👥 Управление источниками",
                    callback_data="manage_sources"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔑 Ключевые слова",
                    callback_data="manage_keywords"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📊 Статистика",
                    callback_data="stats"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="▶️ Запустить парсинг",
                    callback_data="start_parsing"
                ),
                InlineKeyboardButton(
                    text="⏹ Остановить парсинг",
                    callback_data="stop_parsing"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⚙️ Настройки",
                    callback_data="settings"
                )
            ],
        ]
    )
    return keyboard


def get_sources_menu() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Добавить источник",
                    callback_data="add_source"
                ),
                InlineKeyboardButton(
                    text="❌ Удалить источник",
                    callback_data="delete_source"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📋 Список источников",
                    callback_data="list_sources"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Назад",
                    callback_data="back_to_main"
                )
            ],
        ]
    )
    return keyboard


def get_keywords_menu() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Добавить слово",
                    callback_data="add_keyword"
                ),
                InlineKeyboardButton(
                    text="❌ Удалить слово",
                    callback_data="delete_keyword"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📋 Список слов",
                    callback_data="list_keywords"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Назад",
                    callback_data="back_to_main"
                )
            ],
        ]
    )
    return keyboard


def get_settings_menu() -> InlineKeyboardMarkup:
    data = data_manager.get_data()
    use_account = data["settings"]["use_account"]

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=(
                        f"{'✅' if use_account else '❌'} "
                        "Аккаунт Telegram"
                    ),
                    callback_data="toggle_account"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔔 Уведомления",
                    callback_data="toggle_notifications"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📜 Обработать историю",
                    callback_data="process_history"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📤 Экспорт данных",
                    callback_data="export_data"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Назад",
                    callback_data="back_to_main"
                )
            ],
        ]
    )
    return keyboard


def get_back_button(
    callback_data: str = "back_to_main"
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔙 Назад",
                    callback_data=callback_data
                )
            ]
        ]
    )


def get_refresh_button(callback_data: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔄 Обновить",
                    callback_data=callback_data
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Назад",
                    callback_data="back_to_main"
                )
            ],
        ]
    )
