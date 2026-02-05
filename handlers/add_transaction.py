from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import date, datetime

from states.transactions import TransactionStates
from keyboards.keyboards import cancel_button, back_button
from keyboards.expense_categories import expense_category_keyboard, EXPENSE_CATEGORIES
from rpc import rpc
from ui.menus import get_main_menu
from utils.ui import parse_amount, format_amount, format_date, clean_text

router = Router()


async def safe_delete(msg: types.Message):
    try:
        await msg.delete()
    except:
        pass


@router.callback_query(F.data == "menu_add_transaction")
async def add_start(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(TransactionStates.waiting_for_amount)

    msg = await cb.message.edit_text(
        "💸 <b>Новый расход</b>\n\n"
        "Укажи сумму траты.\n"
        "Пример: <b>12000</b> или <b>450 000</b>",
        reply_markup=back_button()
    )

    await state.update_data(bot_message_id=msg.message_id)
    await cb.answer()


@router.message(TransactionStates.waiting_for_amount)
async def set_amount(message: types.Message, state: FSMContext):
    await safe_delete(message)

    amount = parse_amount(message.text)
    if amount is None:
        return await message.answer("⚠️ Не получилось распознать сумму. Введите число, например: <b>12000</b>.")

    await state.update_data(amount=int(amount))
    await state.set_state(TransactionStates.waiting_for_category)

    data = await state.get_data()
    bot_msg_id = data["bot_message_id"]

    # редактируем основное окно
    await message.bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=bot_msg_id,
        text="🏷 <b>Выберите категорию:</b>",
        reply_markup=expense_category_keyboard()
    )


@router.callback_query(F.data.startswith("cat_"))
async def set_category(cb: types.CallbackQuery, state: FSMContext):
    code = cb.data
    category = next((t for t, c in EXPENSE_CATEGORIES if c == code), None)

    if not category:
        return await cb.answer("Категория не найдена")

    await state.update_data(category=category)
    await state.set_state(TransactionStates.waiting_for_description)

    data = await state.get_data()
    bot_msg_id = data["bot_message_id"]

    await cb.message.bot.edit_message_text(
        chat_id=cb.message.chat.id,
        message_id=bot_msg_id,
        text="📝 <b>Описание (необязательно):</b>",
        reply_markup=description_keyboard()
    )
    await cb.answer()


def description_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="⏭ Пропустить", callback_data="desc_skip")
    kb.button(text="❌ Отменить", callback_data="menu_cancel")
    kb.adjust(1)
    return kb.as_markup()


@router.callback_query(F.data == "desc_skip")
async def skip_description(cb: types.CallbackQuery, state: FSMContext):
    await state.update_data(description=None)
    await state.set_state(TransactionStates.waiting_for_date)

    data = await state.get_data()
    bot_msg_id = data["bot_message_id"]

    await cb.message.bot.edit_message_text(
        chat_id=cb.message.chat.id,
        message_id=bot_msg_id,
        text="📅 <b>Дата траты:</b>\n\nВыберите вариант:",
        reply_markup=date_keyboard()
    )
    await cb.answer()


@router.message(TransactionStates.waiting_for_description)
async def set_desc(message: types.Message, state: FSMContext):
    await safe_delete(message)

    await state.update_data(description=message.text.strip())
    await state.set_state(TransactionStates.waiting_for_date)

    data = await state.get_data()
    bot_msg_id = data["bot_message_id"]

    await message.bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=bot_msg_id,
        text="📅 <b>Дата траты:</b>\n\nВыберите вариант:",
        reply_markup=date_keyboard()
    )

def date_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="📅 Сегодня", callback_data="date_today")
    kb.button(text="🗓 Ввести вручную", callback_data="date_manual")
    kb.button(text="❌ Отменить", callback_data="menu_cancel")
    kb.adjust(1)
    return kb.as_markup()


@router.callback_query(F.data == "date_today")
async def choose_today(cb: types.CallbackQuery, state: FSMContext):
    await prepare_confirmation(cb, state, date.today().isoformat())


@router.callback_query(F.data == "date_manual")
async def date_manual(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(TransactionStates.waiting_for_date_manual)

    data = await state.get_data()
    bot_msg_id = data["bot_message_id"]

    await cb.message.bot.edit_message_text(
        chat_id=cb.message.chat.id,
        message_id=bot_msg_id,
        text="📆 <b>Введите дату (YYYY-MM-DD):</b>",
        reply_markup=cancel_button()
    )
    await cb.answer()


@router.message(TransactionStates.waiting_for_date_manual)
async def save_manual(message: types.Message, state: FSMContext):
    await safe_delete(message)
    date_value = message.text.strip()
    try:
        datetime.strptime(date_value, "%Y-%m-%d")
    except ValueError:
        return await message.answer("⚠ Неверный формат даты. Пример: <b>2026-02-05</b>")
    await prepare_confirmation(message, state, date_value)


def confirm_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Сохранить", callback_data="expense_confirm")
    kb.button(text="❌ Отменить", callback_data="menu_cancel")
    kb.adjust(1)
    return kb.as_markup()


async def prepare_confirmation(obj, state: FSMContext, date_value: str):
    data = await state.get_data()
    await state.update_data(date=date_value)
    await state.set_state(TransactionStates.waiting_for_confirm)

    amount_text = format_amount(data["amount"])
    category = data["category"]
    description = clean_text(data.get("description") or "—", 120)
    date_text = format_date(date_value)

    text = (
        "🧾 <b>Проверьте расход</b>\n\n"
        f"💸 Сумма: <b>{amount_text}</b>\n"
        f"🏷 Категория: <b>{category}</b>\n"
        f"📝 Описание: <b>{description}</b>\n"
        f"📅 Дата: <b>{date_text}</b>\n\n"
        "Сохранить операцию?"
    )

    bot_msg_id = data["bot_message_id"]
    chat_id = obj.message.chat.id if isinstance(obj, types.CallbackQuery) else obj.chat.id
    await obj.bot.edit_message_text(
        chat_id=chat_id,
        message_id=bot_msg_id,
        text=text,
        reply_markup=confirm_keyboard()
    )


@router.callback_query(TransactionStates.waiting_for_confirm, F.data == "expense_confirm")
async def finish_expense(cb: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    date_value = data.get("date")

    payload = {
        "tg_user_id": cb.from_user.id,
        "items": [{
            "amount": -abs(data["amount"]),
            "category": data["category"],
            "description": data.get("description"),
            "datetime": date_value,
        }],
        "source": "manual",
    }

    try:
        await rpc("transaction.import", payload)
    except Exception:
        await state.clear()
        return await cb.message.edit_text(
            "⚠️ Не удалось сохранить расход. Попробуй позже.",
            reply_markup=await get_main_menu(cb.from_user.id)
        )

    bot_msg_id = data["bot_message_id"]
    await state.clear()
    await cb.bot.edit_message_text(
        chat_id=cb.message.chat.id,
        message_id=bot_msg_id,
        text=(
            "✅ <b>Расход записан</b>\n\n"
            f"💸 Сумма: <b>{format_amount(data['amount'])}</b>\n"
            f"🏷 Категория: <b>{data['category']}</b>\n"
            f"📅 Дата: <b>{format_date(date_value)}</b>\n"
            "Хорошая работа. Так проще держать бюджет под контролем."
        ),
        reply_markup=await get_main_menu(cb.from_user.id)
    )
    await cb.answer()


@router.callback_query(F.data == "add_expense_back")
async def back_to_amount(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(TransactionStates.waiting_for_amount)

    data = await state.get_data()
    bot_msg_id = data.get("bot_message_id")

    if bot_msg_id:
        await cb.message.bot.edit_message_text(
            chat_id=cb.message.chat.id,
            message_id=bot_msg_id,
            text=(
                "💸 <b>Новый расход</b>\n\n"
                "Укажи сумму траты.\n"
                "Пример: <b>12000</b> или <b>450 000</b>"
            ),
            reply_markup=back_button()
        )
    await cb.answer()
