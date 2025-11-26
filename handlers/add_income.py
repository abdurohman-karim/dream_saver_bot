from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import date

from states.incomes import IncomeStates
from rpc import rpc, RPCError, RPCTransportError
from keyboards.keyboards import cancel_button, main_menu

router = Router()


# --------------- КАТЕГОРИИ ДОХОДОВ ------------------
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
    kb.button(text="⬅ Назад", callback_data="add_income_back")
    kb.button(text="❌ Отменить", callback_data="menu_cancel")
    kb.adjust(2)
    return kb.as_markup()


# --------------- ВЫБОР ДАТЫ ------------------
def date_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="📅 Сегодня", callback_data="date_today_income")
    kb.button(text="🗓 Ввести вручную", callback_data="date_manual_income")
    kb.button(text="⬅ Назад", callback_data="add_income_back_desc")
    kb.button(text="❌ Отменить", callback_data="menu_cancel")
    kb.adjust(1)
    return kb.as_markup()


# --------------- 1. НАЖАЛИ «Добавить доход» ------------------
@router.callback_query(F.data == "menu_add_income")
async def add_income_start(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(IncomeStates.waiting_for_amount)

    await cb.message.edit_text(
        "💵 <b>Добавление дохода</b>\n\n"
        "Введите сумму:",
        reply_markup=cancel_button()
    )
    await cb.answer()


# --------------- 2. ВВОД СУММЫ ------------------
@router.message(IncomeStates.waiting_for_amount)
async def income_amount(message: types.Message, state: FSMContext):
    amt = message.text.replace(" ", "")
    if not amt.isdigit():
        return await message.answer("⚠ Введите сумму числом.")

    await state.update_data(amount=int(amt))
    await state.set_state(IncomeStates.waiting_for_category)

    await message.answer(
        "🏦 <b>Выберите источник дохода:</b>",
        reply_markup=income_category_keyboard()
    )


# --------------- 3. ВЫБОР КАТЕГОРИИ ------------------
@router.callback_query(F.data.startswith("inc_"))
async def set_income_category(cb: types.CallbackQuery, state: FSMContext):
    code = cb.data

    text = next((t for t, c in INCOME_CATEGORIES if c == code), None)
    if not text:
        return await cb.answer("Ошибка категории")

    await state.update_data(category=text)
    await state.set_state(IncomeStates.waiting_for_description)

    await cb.message.edit_text(
        "📝 <b>Введите описание (необязательно):</b>",
        reply_markup=cancel_button()
    )
    await cb.answer()


# --------------- 4. ВВОД ОПИСАНИЯ ------------------
@router.message(IncomeStates.waiting_for_description)
async def income_description(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text.strip())
    await state.set_state(IncomeStates.waiting_for_date)

    await message.answer(
        "📅 <b>Дата дохода:</b>\n\n"
        "Выберите один вариант:",
        reply_markup=date_keyboard()
    )


# --------------- 5. СЕГОДНЯ ------------------
@router.callback_query(F.data == "date_today_income")
async def choose_today_income(cb: types.CallbackQuery, state: FSMContext):
    await save_income(cb, state, date.today().isoformat())


# --------------- 6. РУЧНОЙ ВВОД ДАТЫ ------------------
@router.callback_query(F.data == "date_manual_income")
async def manual_date_income(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(IncomeStates.waiting_for_date)

    await cb.message.edit_text(
        "📆 <b>Введите дату (YYYY-MM-DD):</b>",
        reply_markup=cancel_button()
    )
    await cb.answer()


@router.message(IncomeStates.waiting_for_date)
async def manual_date_income_enter(message: types.Message, state: FSMContext):
    await save_income(message, state, message.text.strip())


# --------------- 7. СОХРАНЕНИЕ ------------------
async def save_income(msg_or_cb, state: FSMContext, date_value: str):
    data = await state.get_data()

    payload = {
        "tg_user_id": msg_or_cb.from_user.id,
        "items": [
            {
                "amount": abs(data["amount"]),  # доход = положительное число
                "category": data["category"],
                "description": data.get("description"),
                "datetime": date_value,
            }
        ],
        "source": "manual",
    }

    try:
        await rpc("transaction.import", payload)
    except (RPCError, RPCTransportError) as e:
        await msg_or_cb.message.edit_text(
            f"⚠ Ошибка при сохранении:\n{e}",
            reply_markup=main_menu()
        )
        await state.clear()
        return

    await state.clear()

    await msg_or_cb.message.edit_text(
        "✅ <b>Доход сохранён!</b>\n\n"
        f"💵 Сумма: <b>{data['amount']:,} сум</b>\n"
        f"🏦 Источник: <b>{data['category']}</b>\n"
        f"📅 Дата: <b>{date_value}</b>",
        reply_markup=main_menu()
    )
