from aiogram import types, F
from aiogram.fsm.context import FSMContext
from core.bot import dp
from core.database import data_manager
from keyboards.inline import (
    get_keywords_menu,
    get_back_button,
    get_admin_menu
)
from utils.states import AdminStates
from filters.admin import AdminFilter


@dp.callback_query(F.data == "manage_keywords", AdminFilter())
async def manage_keywords(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🔑 Управление ключевыми словами:",
        reply_markup=get_keywords_menu(),
    )


@dp.callback_query(F.data == "add_keyword", AdminFilter())
async def add_keyword_start(
    callback: types.CallbackQuery,
    state: FSMContext
):
    await callback.message.edit_text(
        "📝 Введите ключевое слово для добавления:"
    )
    await state.set_state(AdminStates.waiting_for_keyword)


@dp.message(AdminStates.waiting_for_keyword, AdminFilter())
async def process_add_keyword(
    message: types.Message,
    state: FSMContext
):
    keyword = message.text.strip()

    if not keyword:
        await message.answer("❌ Ключевое слово не может быть пустым!")
        return

    if data_manager.add_keyword(keyword):
        await message.answer(f"✅ Ключевое слово '{keyword}' добавлено!")
    else:
        await message.answer(
            f"⚠️ Ключевое слово '{keyword}' уже существует!"
        )

    await state.clear()
    await message.answer(
        "👋 Главное меню:",
        reply_markup=get_admin_menu()
    )


@dp.callback_query(F.data == "list_keywords", AdminFilter())
async def list_keywords(callback: types.CallbackQuery):
    keywords = data_manager.get_keywords()

    if not keywords:
        await callback.message.edit_text(
            "📝 Список ключевых слов пуст",
            reply_markup=get_back_button("manage_keywords"),
        )
        return

    text = "📝 Ключевые слова:\n\n"
    for i, keyword in enumerate(keywords, 1):
        text += f"{i}. {keyword}\n"

    await callback.message.edit_text(
        text,
        reply_markup=get_back_button("manage_keywords")
    )


@dp.callback_query(F.data == "delete_keyword", AdminFilter())
async def delete_keyword_start(
    callback: types.CallbackQuery,
    state: FSMContext
):
    keywords = data_manager.get_keywords()

    if not keywords:
        await callback.message.edit_text(
            "❌ Список ключевых слов пуст",
            reply_markup=get_back_button("manage_keywords"),
        )
        return

    text = "❌ Введите номер ключевого слова для удаления:\n\n"
    for i, keyword in enumerate(keywords, 1):
        text += f"{i}. {keyword}\n"

    await callback.message.edit_text(text)
    await state.set_state(AdminStates.waiting_for_keyword_delete)


@dp.message(AdminStates.waiting_for_keyword_delete, AdminFilter())
async def process_delete_keyword(
    message: types.Message,
    state: FSMContext
):
    try:
        index = int(message.text) - 1
        keyword = data_manager.remove_keyword(index)

        if keyword:
            await message.answer(
                f"✅ Ключевое слово '{keyword}' удалено!"
            )
        else:
            await message.answer("❌ Неверный номер ключевого слова!")
    except ValueError:
        await message.answer("❌ Пожалуйста, введите корректный номер")

    await state.clear()
    await message.answer(
        "👋 Главное меню:",
        reply_markup=get_admin_menu()
    )