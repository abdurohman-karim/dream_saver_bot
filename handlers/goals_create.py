# handlers/goals_create.py
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext

from states.goals import GoalStates
from rpc import rpc, RPCError, RPCTransportError
from keyboards.keyboards import cancel_button, main_menu
from keyboards.goal_icons import icons_keyboard

router = Router()


@router.callback_query(F.data == "menu_newgoal")
async def new_goal_start(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(GoalStates.waiting_for_title)

    sent = await cb.message.edit_text(
        "🎯 <b>Создание новой цели</b>\n\n"
        "Введите название цели:\n"
        "<i>Например: «iPhone 17 Pro Max»</i>",
        reply_markup=cancel_button()
    )

    await state.update_data(bot_message_id=sent.message_id)
    await cb.answer()


@router.message(GoalStates.waiting_for_title)
async def set_title(message: types.Message, state: FSMContext):
    title = (message.text or "").strip()

    if len(title) < 2:
        return await message.answer("⚠️ Название слишком короткое")

    await state.update_data(title=title)
    data = await state.get_data()

    sent = await message.bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=data["bot_message_id"],
        text=(
            "💰 <b>Введите сумму цели</b> (UZS):\n"
            "<i>Например: 3 000 000</i>"
        ),
        reply_markup=cancel_button()
    )

    await state.update_data(bot_message_id=sent.message_id)
    await state.set_state(GoalStates.waiting_for_amount)


@router.message(GoalStates.waiting_for_amount)
async def set_amount(message: types.Message, state: FSMContext):
    raw = (message.text or "").replace(" ", "")

    if not raw.isdigit():
        return await message.answer("⚠️ Введите сумму числом")

    amount = int(raw)
    await state.update_data(amount_total=amount)

    data = await state.get_data()
    bot_msg_id = data["bot_message_id"]
    amount_fmt = f"{amount:,}".replace(",", " ")

    sent = await message.bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=bot_msg_id,
        text=(
            f"🎨 <b>Выбери иконку для цели</b>\n\n"
            f"💰 Сумма: <b>{amount_fmt} сум</b>\n\n"
            "Это поможет визуально отличать цели."
        ),
        reply_markup=icons_keyboard()
    )

    await state.update_data(bot_message_id=sent.message_id)
    await state.set_state(GoalStates.waiting_for_icon)


@router.callback_query(F.data.startswith("goal_icon_"))
async def choose_icon(cb: types.CallbackQuery, state: FSMContext):
    icon = cb.data.replace("goal_icon_", "")
    await state.update_data(icon=icon)

    data = await state.get_data()
    bot_msg_id = data["bot_message_id"]
    amount = data["amount_total"]
    amount_fmt = f"{amount:,}".replace(",", " ")

    sent = await cb.bot.edit_message_text(
        chat_id=cb.message.chat.id,
        message_id=bot_msg_id,
        text=(
            f"{icon} <b>Почти готово!</b>\n\n"
            f"💰 Сумма: <b>{amount_fmt} сум</b>\n\n"
            "📅 Выбери дедлайн для цели:"
        ),
        reply_markup=deadline_keyboard()
    )

    await state.update_data(bot_message_id=sent.message_id)
    await state.set_state(GoalStates.waiting_for_deadline)
    await cb.answer()


# временно: простая клавиатура дедлайна внутри файла
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import date, timedelta

def deadline_keyboard():
    kb = InlineKeyboardBuilder()
    today = date.today()
    kb.button(text="Через 3 месяца", callback_data=f"deadline_{(today + timedelta(days=90)).isoformat()}")
    kb.button(text="Через 6 месяцев", callback_data=f"deadline_{(today + timedelta(days=180)).isoformat()}")
    kb.button(text="Через год", callback_data=f"deadline_{(today.replace(year=today.year + 1)).isoformat()}")
    kb.button(text="Без дедлайна", callback_data="deadline_none")
    kb.button(text="❌ Отменить", callback_data="menu_cancel")
    kb.adjust(1)
    return kb.as_markup()


@router.callback_query(F.data.startswith("deadline_"))
async def choose_deadline(cb: types.CallbackQuery, state: FSMContext):
    raw = cb.data.replace("deadline_", "")
    deadline = None if raw == "none" else raw

    data = await state.get_data()

    title = data["title"]
    amount = data["amount_total"]
    icon = data.get("icon")
    amount_fmt = f"{amount:,}".replace(",", " ")

    goal_payload = {
        "tg_user_id": cb.from_user.id,
        "title": title,
        "amount_total": amount,
        "deadline": deadline,
        "icon": icon,
    }

    try:
        await rpc("goal.create", goal_payload)
    except RPCTransportError:
        await cb.message.edit_text(
            "⚠️ Сервер недоступен, попробуйте позже.",
            reply_markup=main_menu()
        )
        await state.clear()
        return
    except RPCError as e:
        await cb.message.edit_text(
            f"⚠️ Ошибка:\n{e}",
            reply_markup=main_menu()
        )
        await state.clear()
        return

    await state.clear()

    await cb.message.edit_text(
        f"🎉 <b>Цель создана!</b>\n\n"
        f"🏷 Название: <b>{title}</b>\n"
        f"💰 Сумма: <b>{amount_fmt} сум</b>\n"
        f"📅 Дедлайн: <b>{deadline or 'Без дедлайна'}</b>",
        reply_markup=main_menu()
    )
    await cb.answer()
