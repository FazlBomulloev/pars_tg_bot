from aiogram import types, F
from aiogram.filters import Command
from core.bot import bot, dp
from core.database import data_manager
from keyboards.inline import get_admin_menu
from filters.admin import AdminFilter
from config import settings


@dp.message(Command("start"), AdminFilter())
async def cmd_start(message: types.Message):
    await message.answer(
        f"👋 Привет, {message.from_user.first_name}!\n\n"
        "📱 Добро пожаловать в панель управления парсер-ботом!\n"
        "Выберите нужный раздел:",
        reply_markup=get_admin_menu(),
    )

    commands = [
        types.BotCommand(command="menu", description="Главное меню")
    ]
    await bot.set_my_commands(
        commands,
        scope=types.BotCommandScopeChat(chat_id=message.from_user.id)
    )


@dp.message(Command("menu"), AdminFilter())
async def cmd_menu(message: types.Message):
    await message.answer(
        "👋 Главное меню:",
        reply_markup=get_admin_menu()
    )


@dp.message(Command("add_admin"), AdminFilter())
async def add_admin(message: types.Message):
    if message.from_user.id == settings.ADMIN_ID:
        try:
            new_admin_id = int(message.text.split()[1])
            if data_manager.add_admin(new_admin_id):
                await message.answer(
                    f"✅ Пользователь {new_admin_id} добавлен "
                    "как администратор!"
                )
            else:
                await message.answer(
                    "❌ Этот пользователь уже является "
                    "администратором!"
                )
        except (IndexError, ValueError):
            await message.answer(
                "❌ Используйте формат: /add_admin ID_пользователя"
            )
    else:
        await message.answer(
            "⛔️ У вас нет прав для добавления администраторов."
        )


@dp.message(Command("remove_admin"), AdminFilter())
async def remove_admin(message: types.Message):
    if message.from_user.id == settings.ADMIN_ID:
        try:
            admin_id = int(message.text.split()[1])
            if data_manager.remove_admin(admin_id):
                await message.answer(
                    f"✅ Администратор {admin_id} удален!"
                )
            else:
                await message.answer(
                    "❌ Этот пользователь не является "
                    "администратором или это главный админ!"
                )
        except (IndexError, ValueError):
            await message.answer(
                "❌ Используйте формат: /remove_admin ID_пользователя"
            )
    else:
        await message.answer(
            "⛔️ У вас нет прав для удаления администраторов."
        )


@dp.message(Command("list_admins"), AdminFilter())
async def list_admins(message: types.Message):
    data = data_manager.get_data()
    admin_list = "👥 Список администраторов:\n\n"
    for admin_id in data["settings"]["admins"]:
        admin_list += f"• {admin_id}\n"
    await message.answer(admin_list)


@dp.callback_query(F.data == "back_to_main", AdminFilter())
async def back_to_main(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "👋 Главное меню:\nВыберите нужный раздел:",
        reply_markup=get_admin_menu(),
    )