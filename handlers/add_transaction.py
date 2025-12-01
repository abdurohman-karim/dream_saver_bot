from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import date

from states.transactions import TransactionStates
from keyboards.keyboards import cancel_button, main_menu, back_button
from keyboards.expense_categories import expense_category_keyboard, EXPENSE_CATEGORIES
from rpc import rpc, RPCError, RPCTransportError

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
        "💸 <b>Добавление расхода</b>\n\n"
        "Укажи сумму, которую ты потратил.\n"
        "Я сохраню её в твою статистику и помогу точнее отслеживать бюджет 😉\n\n"
        "Например: <b>12000</b> или <b>450 000</b>",
        reply_markup=back_button()
    )

    await state.update_data(bot_message_id=msg.message_id)
    await cb.answer()


@router.message(TransactionStates.waiting_for_amount)
async def set_amount(message: types.Message, state: FSMContext):
    await safe_delete(message)

    raw = message.text.replace(" ", "")
    if not raw.isdigit():
        return await message.answer("⚠ Введите сумму числом.")

    await state.update_data(amount=int(raw))
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
        return await cb.answer("Ошибка категории")

    await state.update_data(category=category)
    await state.set_state(TransactionStates.waiting_for_description)

    data = await state.get_data()
    bot_msg_id = data["bot_message_id"]

    await cb.message.bot.edit_message_text(
        chat_id=cb.message.chat.id,
        message_id=bot_msg_id,
        text="📝 <b>Введите описание (необязательно):</b>",
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
    await finish_expense(cb, state, date.today().isoformat())


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
    await finish_expense(message, state, date_value)


async def finish_expense(obj, state, date_value):
    data = await state.get_data()

    payload = {
        "tg_user_id": obj.from_user.id,
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
    except Exception as e:
        if isinstance(obj, types.CallbackQuery):
            return await obj.message.edit_text(f"❌ Ошибка сохранения:\n{e}", reply_markup=main_menu())
        else:
            return await obj.answer(f"❌ Ошибка сохранения:\n{e}", reply_markup=main_menu())

    bot_msg_id = data["bot_message_id"]
    await state.clear()

    if isinstance(obj, types.CallbackQuery):
        chat_id = obj.message.chat.id
        bot = obj.bot
    else:
        chat_id = obj.chat.id
        bot = obj.bot

    await bot.edit_message_text(
        chat_id=chat_id,
        message_id=bot_msg_id,
        text=(
            "✅ <b>Расход добавлен!</b>\n\n"
            f"💸 Сумма: <b>{data['amount']:,} сум</b>\n"
            f"🏷 Категория: <b>{data['category']}</b>\n"
            f"📅 Дата: <b>{date_value}</b>"
        ),
        reply_markup=main_menu()
    )

