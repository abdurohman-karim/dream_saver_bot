# handlers/add_income.py
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import date, datetime

from states.incomes import IncomeStates
from keyboards.keyboards import cancel_button, back_button
from rpc import rpc
from utils.ui import parse_amount, format_amount, format_date, clean_text
from ui.menus import get_main_menu

router = Router()

INCOME_CATEGORIES = [
    ("💼 Зарплата", "inc_salary"),
    ("🏦 Перевод", "inc_transfer"),
    ("📈 Бизнес", "inc_business"),
    ("💰 Продажа", "inc_sale"),
    ("🎁 Подарок", "inc_gift"),
]


def income_category_keyboard():
    kb = InlineKeyboardBuilder()
    for text, code in INCOME_CATEGORIES:
        kb.button(text=text, callback_data=code)
    kb.button(text="⬅️ Назад", callback_data="inc_back")
    kb.button(text="❌ Отменить", callback_data="menu_cancel")
    kb.adjust(2)
    return kb.as_markup()


def description_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="⏭ Пропустить", callback_data="inc_desc_skip")
    kb.button(text="❌ Отменить", callback_data="menu_cancel")
    kb.adjust(2)
    return kb.as_markup()


def date_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="📅 Сегодня", callback_data="inc_date_today")
    kb.button(text="🗓 Ввести вручную", callback_data="inc_date_manual")
    kb.button(text="❌ Отменить", callback_data="menu_cancel")
    kb.adjust(1)
    return kb.as_markup()


async def safe_delete(msg: types.Message):
    try:
        await msg.delete()
    except:
        pass


async def update_window(obj, message_id: int, text: str, reply_markup=None):
    if isinstance(obj, types.CallbackQuery):
        bot = obj.bot
        chat_id = obj.message.chat.id
    else:
        bot = obj.bot
        chat_id = obj.chat.id

    await bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text=text,
        reply_markup=reply_markup
    )



@router.callback_query(F.data == "menu_add_income")
async def add_income_start(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(IncomeStates.waiting_for_amount)

    msg = await cb.message.edit_text(
        "💵 <b>Новый доход</b>\n\n"
        "Укажи сумму поступления.\n"
        "Пример: <b>120000</b> или <b>1 500 000</b>",
        reply_markup=back_button()
    )

    await state.update_data(bot_message_id=msg.message_id)
    await cb.answer()


@router.message(IncomeStates.waiting_for_amount)
async def income_amount(message: types.Message, state: FSMContext):
    await safe_delete(message)

    amt = parse_amount(message.text)
    if amt is None:
        return await message.answer("⚠️ Не получилось распознать сумму. Введите число, например: <b>120000</b>.")

    await state.update_data(amount=int(amt))
    await state.set_state(IncomeStates.waiting_for_category)

    data = await state.get_data()
    bot_message_id = data["bot_message_id"]

    await update_window(
        message,
        bot_message_id,
        "🏦 <b>Выберите источник дохода:</b>",
        income_category_keyboard()
    )


@router.callback_query(F.data.in_([code for _, code in INCOME_CATEGORIES]))
async def set_income_category(cb: types.CallbackQuery, state: FSMContext):
    code = cb.data
    category = next((t for t, c in INCOME_CATEGORIES if c == code), None)
    if not category:
        return await cb.answer("Категория не найдена")

    await state.update_data(category=category)
    await state.set_state(IncomeStates.waiting_for_description)

    data = await state.get_data()
    bot_message_id = data["bot_message_id"]

    await update_window(
        cb,
        bot_message_id,
        "📝 <b>Описание (необязательно):</b>",
        description_keyboard()
    )
    await cb.answer()


@router.callback_query(F.data == "inc_desc_skip")
async def skip_income_description(cb: types.CallbackQuery, state: FSMContext):
    await state.update_data(description=None)
    await state.set_state(IncomeStates.waiting_for_date)

    data = await state.get_data()
    bot_message_id = data["bot_message_id"]

    await update_window(
        cb,
        bot_message_id,
        "📅 <b>Дата дохода:</b>\n\nВыберите вариант:",
        date_keyboard()
    )
    await cb.answer()


@router.message(IncomeStates.waiting_for_description)
async def income_description(message: types.Message, state: FSMContext):
    await safe_delete(message)

    await state.update_data(description=message.text.strip())
    await state.set_state(IncomeStates.waiting_for_date)

    data = await state.get_data()
    bot_message_id = data["bot_message_id"]

    await update_window(
        message,
        bot_message_id,
        "📅 <b>Дата дохода:</b>\n\nВыберите один вариант:",
        date_keyboard()
    )


@router.callback_query(F.data == "inc_date_today")
async def choose_today_income(cb: types.CallbackQuery, state: FSMContext):
    await prepare_income_confirmation(cb, state, date.today().isoformat())


@router.callback_query(F.data == "inc_date_manual")
async def manual_date_income(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(IncomeStates.waiting_for_date)

    data = await state.get_data()
    bot_message_id = data["bot_message_id"]

    await update_window(
        cb,
        bot_message_id,
        "📆 <b>Введите дату (YYYY-MM-DD):</b>",
        cancel_button()
    )
    await cb.answer()


@router.message(IncomeStates.waiting_for_date)
async def manual_date_income_enter(message: types.Message, state: FSMContext):
    date_value = message.text.strip()
    try:
        datetime.strptime(date_value, "%Y-%m-%d")
    except ValueError:
        return await message.answer("⚠ Неверный формат даты. Пример: <b>2026-02-05</b>")
    await prepare_income_confirmation(message, state, date_value)



def confirm_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Сохранить", callback_data="income_confirm")
    kb.button(text="❌ Отменить", callback_data="menu_cancel")
    kb.adjust(1)
    return kb.as_markup()


async def prepare_income_confirmation(obj, state: FSMContext, date_value: str):
    data = await state.get_data()
    await state.update_data(date=date_value)
    await state.set_state(IncomeStates.waiting_for_confirm)

    amount_text = format_amount(data["amount"])
    category = data["category"]
    description = clean_text(data.get("description") or "—", 120)
    date_text = format_date(date_value)

    text = (
        "🧾 <b>Проверьте доход</b>\n\n"
        f"💵 Сумма: <b>{amount_text}</b>\n"
        f"🏦 Источник: <b>{category}</b>\n"
        f"📝 Описание: <b>{description}</b>\n"
        f"📅 Дата: <b>{date_text}</b>\n\n"
        "Сохранить операцию?"
    )

    bot_message_id = data["bot_message_id"]
    chat_id = obj.message.chat.id if isinstance(obj, types.CallbackQuery) else obj.chat.id
    await obj.bot.edit_message_text(
        chat_id=chat_id,
        message_id=bot_message_id,
        text=text,
        reply_markup=confirm_keyboard()
    )


@router.callback_query(IncomeStates.waiting_for_confirm, F.data == "income_confirm")
async def finish_income(cb: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    date_value = data.get("date")

    payload = {
        "tg_user_id": cb.from_user.id,
        "items": [{
            "amount": abs(data["amount"]),
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
            "⚠️ Не удалось сохранить доход. Попробуй позже.",
            reply_markup=await get_main_menu(cb.from_user.id)
        )

    bot_message_id = data["bot_message_id"]
    await state.clear()

    await cb.bot.edit_message_text(
        chat_id=cb.message.chat.id,
        message_id=bot_message_id,
        text=(
            "✅ <b>Доход записан</b>\n\n"
            f"💵 Сумма: <b>{format_amount(data['amount'])}</b>\n"
            f"🏦 Источник: <b>{data['category']}</b>\n"
            f"📅 Дата: <b>{format_date(date_value)}</b>\n"
            "Отлично. Это укрепляет твою финансовую дисциплину."
        ),
        reply_markup=await get_main_menu(cb.from_user.id)
    )
    await cb.answer()


@router.callback_query(F.data == "inc_back")
async def income_back_to_amount(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(IncomeStates.waiting_for_amount)

    data = await state.get_data()
    bot_message_id = data.get("bot_message_id")

    if bot_message_id:
        await update_window(
            cb,
            bot_message_id,
            "💵 <b>Новый доход</b>\n\n"
            "Укажи сумму поступления.\n"
            "Пример: <b>120000</b> или <b>1 500 000</b>",
            back_button()
        )
    await cb.answer()
