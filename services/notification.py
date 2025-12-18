from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import Optional


def format_notification(
    keyword: str,
    sender_id: int,
    sender_name: str,
    sender_username: Optional[str],
    source_type: str,
    source_title: str,
    source_username: Optional[str],
    message_text: str,
    message_link: Optional[str] = None,
    parent_channel: Optional[str] = None
) -> tuple[str, Optional[InlineKeyboardMarkup]]:

    text = "🔔 <b>Найдено ключевое слово!</b>\n\n"
    text += f"🔑 <b>Ключевое слово:</b> {keyword}\n\n"

    text += "👤 <b>Отправитель:</b>\n"
    text += f"├ Имя: {sender_name}\n"
    if sender_username:
        text += f"├ Username: @{sender_username}\n"
    text += f"└ ID: <code>{sender_id}</code>\n\n"

    text += "💬 <b>Источник:</b>\n"

    if source_type == "chat":
        text += "├ Тип: Группа\n"
    elif source_type == "channel":
        text += "├ Тип: Канал\n"
    elif source_type == "discussion":
        text += "├ Тип: Комментарий в канале\n"
        if parent_channel:
            text += f"├ Канал: {parent_channel}\n"

    text += f"├ Название: {source_title}\n"
    if source_username:
        text += f"└ Username: @{source_username}\n"
    else:
        text += "└ Username: Нет\n"

    text += "\n📝 <b>Сообщение:</b>\n"
    preview = message_text[:200]
    if len(message_text) > 200:
        preview += "..."
    text += f"<i>{preview}</i>"

    # Создаем кнопки
    keyboard = None
    buttons = []
    
    # Кнопка для перехода к сообщению (если есть ссылка)
    if message_link:
        buttons.append([
            InlineKeyboardButton(
                text="🔗 Перейти к сообщению",
                url=message_link
            )
        ])
    
    # Кнопка для перехода в чат с пользователем
    if sender_username:
        # Если есть username - используем его
        buttons.append([
            InlineKeyboardButton(
                text="💬 Написать пользователю",
                url=f"https://t.me/{sender_username}"
            )
        ])
    else:
        # Если нет username - используем tg://user?id=
        buttons.append([
            InlineKeyboardButton(
                text="💬 Написать пользователю",
                url=f"tg://user?id={sender_id}"
            )
        ])
    
    if buttons:
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    return text, keyboard
