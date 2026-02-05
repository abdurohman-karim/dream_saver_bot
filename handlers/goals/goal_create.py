# handlers/goal_create.py
from aiogram import Router, types, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from datetime import datetime

from states.goals import GoalStates
from keyboards.keyboards import cancel_button
from keyboards.deadline import deadline_keyboard
from rpc import rpc, RPCError, RPCTransportError
from utils.ui import parse_amount, format_amount, format_date
from ui.menus import get_main_menu

router = Router()

async def safe_delete(message: types.Message):
    try:
        await message.delete()
    except:
        pass


async def render_create_window(cb_or_msg, state: FSMContext):
    data = await state.get_data()

    title = data.get("title", "—")
    amount = data.get("amount_total", "—")
    deadline = data.get("deadline", "—")

    if isinstance(amount, int):
        amount_fmt = format_amount(amount)
    else:
        amount_fmt = amount

    text = (
        "🎯 <b>Создание новой цели</b>\n\n"
        f"🏷 Название: <b>{title}</b>\n"
        f"💰 Сумма: <b>{amount_fmt}</b>\n"
        f"📅 Дедлайн: <b>{format_date(deadline) if deadline else '—'}</b>"
    )

    bot_msg_id = data["bot_message_id"]

    await cb_or_msg.bot.edit_message_text(
        chat_id=cb_or_msg.chat.id if isinstance(cb_or_msg, types.Message) else cb_or_msg.message.chat.id,
        message_id=bot_msg_id,
        text=text,
        reply_markup=cancel_button()
    )


async def finish_goal_create(cb_or_msg, state: FSMContext):
    data = await state.get_data()

    payload = {
        "tg_user_id": cb_or_msg.from_user.id,
        "title": data["title"],
        "amount_total": data["amount_total"],
        "deadline": data["deadline"] if data["deadline"] != "—" else None
    }

    try:
        await rpc("goal.create", payload)
    except (RPCTransportError, RPCError):
        if isinstance(cb_or_msg, types.CallbackQuery):
            await cb_or_msg.message.answer(
                "⚠️ Не удалось создать цель. Попробуй позже.",
                reply_markup=await get_main_menu(cb_or_msg.from_user.id)
            )
        else:
            await cb_or_msg.answer(
                "⚠️ Не удалось создать цель. Попробуй позже.",
                reply_markup=await get_main_menu(cb_or_msg.from_user.id)
            )
        await state.clear()
        return

    await state.clear()

    amount_fmt = format_amount(data["amount_total"])

    text = (
        f"🎯 <b>Цель создана</b>\n\n"
        f"🏷 Название: <b>{data['title']}</b>\n"
        f"💰 Сумма: <b>{amount_fmt}</b>\n"
        f"📅 Дедлайн: <b>{format_date(data.get('deadline'))}</b>\n"
        "Хорошее решение. Будем двигаться к цели спокойно и системно."
    )

    # ←←← главный фикс
    if isinstance(cb_or_msg, types.CallbackQuery):
        await cb_or_msg.message.answer(text, reply_markup=await get_main_menu(cb_or_msg.from_user.id))
    else:
        await cb_or_msg.answer(text, reply_markup=await get_main_menu(cb_or_msg.from_user.id))


@router.callback_query(F.data == "menu_newgoal")
async def new_goal_start(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(GoalStates.waiting_for_title)

    sent = await cb.message.edit_text(
        "🎯 <b>Создание новой цели</b>\n\n"
        "Как назовем цель?",
        reply_markup=cancel_button()
    )

    await state.update_data(bot_message_id=sent.message_id)
    await cb.answer()


@router.message(GoalStates.waiting_for_title)
async def set_title(message: types.Message, state: FSMContext):

    title = message.text.strip()
    if len(title) < 2:
        await safe_delete(message)
        return await message.answer("⚠️ Название слишком короткое. Сделаем его чуть подробнее?")

    await state.update_data(title=title)
    await safe_delete(message)

    await state.set_state(GoalStates.waiting_for_amount)

    await render_create_window(message, state)
    await message.answer("💰 Введите сумму цели (UZS):")


@router.message(GoalStates.waiting_for_amount)
async def set_amount(message: types.Message, state: FSMContext):
    amount = parse_amount(message.text)
    if amount is None:
        await safe_delete(message)
        return await message.answer("⚠️ Введите сумму числом, например: <b>500000</b>")
    await state.update_data(amount_total=int(amount))
    await safe_delete(message)

    await state.set_state(GoalStates.waiting_for_deadline)

    await render_create_window(message, state)
    await message.answer(
        "📅 Выберите дедлайн:",
        reply_markup=deadline_keyboard()
    )


@router.callback_query(
    StateFilter(GoalStates.waiting_for_deadline),
    F.data.regexp(r"^deadline_\d{4}-\d{2}-\d{2}$")
)
async def choose_deadline(cb: types.CallbackQuery, state: FSMContext):
    raw = cb.data.replace("deadline_", "")
    await state.update_data(deadline=raw)

    await cb.answer()
    return await finish_goal_create(cb, state)



@router.callback_query(
    StateFilter(GoalStates.waiting_for_deadline),
    F.data == "deadline_none"
)
async def no_deadline(cb: types.CallbackQuery, state: FSMContext):
    await state.update_data(deadline=None)
    await cb.answer()
    return await finish_goal_create(cb, state)


@router.callback_query(
    StateFilter(GoalStates.waiting_for_deadline),
    F.data == "deadline_manual"
)
async def manual_deadline_start(cb: types.CallbackQuery, state: FSMContext):
    await cb.answer()
    await state.set_state(GoalStates.waiting_for_manual_deadline)

    await cb.message.edit_text(
        "🗓 Введите дату в формате <b>ГГГГ-ММ-ДД</b>",
        reply_markup=cancel_button()
    )

@router.message(StateFilter(GoalStates.waiting_for_manual_deadline))
async def manual_deadline_input(message: types.Message, state: FSMContext):
    raw = message.text.strip()

    try:
        deadline = datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        await safe_delete(message)
        return await message.answer("⚠️ Неверный формат даты! Введите ГГГГ-ММ-ДД")

    await safe_delete(message)
    await state.update_data(deadline=str(deadline))

    return await finish_goal_create(message, state)
