from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder  # <-- добавили

from datetime import date

from states.transactions import TransactionStates
from keyboards.keyboards import cancel_button, main_menu, back_button
from keyboards.expense_categories import expense_category_keyboard, EXPENSE_CATEGORIES
from rpc import rpc, RPCError, RPCTransportError

router = Router()


@router.callback_query(F.data == "menu_add_transaction")
async def add_start(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(TransactionStates.waiting_for_amount)

    await cb.message.edit_text(
        "💸 <b>Добавление расхода</b>\n\n"
        "Укажи сумму, которую ты потратил.\n"
        "Я сохраню её в твою статистику и помогу точнее отслеживать бюджет 😉\n\n"
        "Например: <b>12000</b> или <b>450 000</b>",
        reply_markup=back_button()
    )
    await cb.answer()

@router.message(TransactionStates.waiting_for_amount)
async def set_amount(message: types.Message, state: FSMContext):
    amt = message.text.replace(" ", "")
    if not amt.isdigit():
        return await message.answer("⚠ Введите сумму числом.")

    await state.update_data(amount=int(amt))
    await state.set_state(TransactionStates.waiting_for_category)

    await message.answer(
        "🏷 <b>Выберите категорию:</b>",
        reply_markup=expense_category_keyboard()
    )


# 🎯 Категория
@router.callback_query(F.data.startswith("cat_"))
async def set_category(cb: types.CallbackQuery, state: FSMContext):
    code = cb.data

    text = next((t for t, c in EXPENSE_CATEGORIES if c == code), None)
    if not text:
        return await cb.answer("Ошибка категории")

    await state.update_data(category=text)
    await state.set_state(TransactionStates.waiting_for_description)

    await cb.message.edit_text(
        "📝 <b>Введите описание (необязательно):</b>",
        reply_markup=back_button()
    )
    await cb.answer()


# ✏️ Описание
@router.message(TransactionStates.waiting_for_description)
async def set_desc(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text.strip())
    await state.set_state(TransactionStates.waiting_for_date)

    await message.answer(
        "📅 <b>Дата траты:</b>\n\n"
        "Нажмите, чтобы выбрать:",
        reply_markup=date_keyboard()
    )


# 📅 Клавиатура с выбором даты
def date_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="📅 Сегодня", callback_data="date_today")
    kb.button(text="🗓 Ввести вручную", callback_data="date_manual")
    kb.button(text="⬅ Назад", callback_data="add_expense_back")
    kb.button(text="❌ Отменить", callback_data="menu_cancel")
    kb.adjust(1)
    return kb.as_markup()


@router.callback_query(F.data == "date_today")
async def choose_today(cb: types.CallbackQuery, state: FSMContext):
    await save_expense(cb, state, date.today().isoformat())


@router.callback_query(F.data == "date_manual")
async def date_manual(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(TransactionStates.waiting_for_date)

    await cb.message.edit_text(
        "📆 <b>Введите дату (YYYY-MM-DD):</b>",
        reply_markup=cancel_button()
    )
    await cb.answer()


@router.message(TransactionStates.waiting_for_date)
async def save_manual(message: types.Message, state: FSMContext):
    date_value = message.text.strip()
    await save_expense(message, state, date_value)


# 💾 Сохранение транзакции
async def save_expense(msg_or_cb, state: FSMContext, date_value: str):
    data = await state.get_data()

    payload = {
        "tg_user_id": msg_or_cb.from_user.id,
        "items": [
            {
                "amount": -abs(data["amount"]),
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
        "✅ <b>Расход добавлен!</b>\n\n"
        f"💸 Сумма: <b>{data['amount']:,} сум</b>\n"
        f"🏷 Категория: <b>{data['category']}</b>\n"
        f"📅 Дата: <b>{date_value}</b>",
        reply_markup=main_menu()
    )
