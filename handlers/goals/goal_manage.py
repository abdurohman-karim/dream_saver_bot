# handlers/goal_manage.py

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from rpc import rpc, RPCError, RPCTransportError
from keyboards.goals_manage import goals_list_keyboard, goal_manage_keyboard
from states.goals import DepositGoal
from ui.menus import get_main_menu
from utils.ui import format_amount, format_date
from ui.formatting import SEPARATOR

router = Router()


def deposit_input_keyboard(goal_id: int):
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Назад", callback_data=f"goal_manage_{goal_id}")
    kb.button(text="❌ Отменить", callback_data="menu_cancel")
    kb.adjust(1)
    return kb.as_markup()


def deposit_confirm_keyboard(goal_id: int):
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Сохранить", callback_data=f"goal_deposit_confirm_{goal_id}")
    kb.button(text="⬅️ Назад", callback_data=f"goal_manage_{goal_id}")
    kb.adjust(1)
    return kb.as_markup()


def close_confirm_keyboard(goal_id: int):
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Закрыть цель", callback_data=f"goal_close_confirm_{goal_id}")
    kb.button(text="⬅️ Назад", callback_data=f"goal_manage_{goal_id}")
    kb.adjust(1)
    return kb.as_markup()


@router.callback_query(F.data == "menu_goals")
async def menu_goals(cb: types.CallbackQuery):
    user_id = cb.from_user.id
    try:
        result = await rpc("goal.list", {"tg_user_id": user_id})
    except (RPCError, RPCTransportError):
        await cb.message.edit_text(
            "⚠️ Не удалось загрузить цели. Попробуй позже.",
            reply_markup=goals_list_keyboard([])
        )
        return await cb.answer()

    res = result.get("result") or result
    goals = res.get("goals", [])

    if not goals:
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        kb = InlineKeyboardBuilder()
        kb.button(text="➕ Создать цель", callback_data="menu_newgoal")
        kb.button(text="⬅️ Назад", callback_data="menu_back")
        kb.adjust(1)

        await cb.message.edit_text(
            "Пока нет целей.\n\nСоздай первую — и начнем отслеживать прогресс.",
            reply_markup=kb.as_markup()
        )
        return await cb.answer()

    await cb.message.edit_text(
        "🎯 <b>Твои цели:</b>",
        reply_markup=goals_list_keyboard(goals)
    )
    await cb.answer()
    return None


@router.callback_query(F.data.startswith("goal_manage_"))
async def goal_manage(cb: types.CallbackQuery, state: FSMContext):
    goal_id = int(cb.data.split("_")[-1])
    user_id = cb.from_user.id
    await state.clear()

    try:
        result = await rpc("goal.get", {"tg_user_id": user_id, "goal_id": goal_id})
    except (RPCError, RPCTransportError):
        await cb.message.edit_text(
            "⚠️ Не удалось загрузить цель. Попробуй позже.",
            reply_markup=await get_main_menu(cb.from_user.id)
        )
        return await cb.answer()

    goal = result.get("result") or result

    icon = goal.get("icon", "🎯")
    title = goal["title"]
    total = goal["amount_total"]
    saved = goal["amount_saved"]
    percent = int(saved / total * 100) if total else 0

    bar = "█" * (percent // 10) + "░" * (10 - percent // 10)

    is_primary = goal.get("is_primary", False)
    pr = goal.get("priority", 1)
    status = goal.get("status", "active")
    deadline = goal.get("deadline") or "Без дедлайна"

    text = (
        f"{icon} <b>{title}</b>\n\n"
        f"💰 {format_amount(saved)} / {format_amount(total)}\n"
        f"📈 Прогресс: <b>{percent}%</b>\n"
        f"{bar}\n"
        f"{SEPARATOR}\n"
        f"⭐ Основная: {'Да' if is_primary else 'Нет'}\n"
        f"🔢 Приоритет: {pr}\n"
        f"📅 Дедлайн: {format_date(deadline)}\n"
    )

    await cb.message.edit_text(
        text,
        reply_markup=goal_manage_keyboard(goal_id, is_primary, status)
    )
    await cb.answer()


@router.callback_query(F.data.startswith("goal_set_primary_"))
async def set_primary(cb: types.CallbackQuery):
    goal_id = int(cb.data.split("_")[-1])

    await rpc("goal.setPrimary", {
        "tg_user_id": cb.from_user.id,
        "goal_id": goal_id
    })

    await cb.answer("⭐ Основная цель обновлена")
    await menu_goals(cb)


@router.callback_query(F.data.startswith("goal_priority_up_"))
async def priority_up(cb: types.CallbackQuery):
    goal_id = int(cb.data.split("_")[-1])
    await rpc("goal.priority.up", {"tg_user_id": cb.from_user.id, "goal_id": goal_id})

    await render_goal(cb, goal_id)


@router.callback_query(F.data.startswith("goal_priority_down_"))
async def priority_down(cb: types.CallbackQuery):
    goal_id = int(cb.data.split("_")[-1])
    await rpc("goal.priority.down", {"tg_user_id": cb.from_user.id, "goal_id": goal_id})

    await render_goal(cb, goal_id)


@router.callback_query(F.data.regexp(r"^goal_deposit_\d+$"))
async def deposit_start(cb: types.CallbackQuery, state: FSMContext):
    goal_id = int(cb.data.split("_")[-1])

    await state.update_data(goal_id=goal_id, bot_message_id=cb.message.message_id)

    await cb.message.edit_text(
        "💸 <b>Пополнение цели</b>\n\n"
        "Введи сумму. Пример: <b>150000</b>.",
        reply_markup=deposit_input_keyboard(goal_id)
    )

    await state.set_state(DepositGoal.waiting_for_amount)
    await cb.answer()

@router.callback_query(F.data.startswith("goal_close_completed_"))
async def close_goal(cb: types.CallbackQuery):
    goal_id = int(cb.data.split("_")[-1])
    await cb.message.edit_text(
        "🛑 <b>Закрыть цель?</b>\n\n"
        "Цель будет помечена как завершённая. Можно восстановить позже.",
        reply_markup=close_confirm_keyboard(goal_id)
    )
    await cb.answer()


@router.callback_query(F.data.startswith("goal_close_confirm_"))
async def close_goal_confirm(cb: types.CallbackQuery):
    goal_id = int(cb.data.split("_")[-1])
    try:
        result = await rpc("goal.close", {
            "tg_user_id": cb.from_user.id,
            "goal_id": goal_id
        })
    except (RPCError, RPCTransportError):
        await cb.message.edit_text(
            "⚠️ Не удалось закрыть цель. Попробуй позже.",
            reply_markup=await get_main_menu(cb.from_user.id)
        )
        return await cb.answer()

    await cb.answer("Цель закрыта")
    await render_goal(cb, goal_id, rpc_result=result)


@router.callback_query(F.data.startswith("goal_reopen_"))
async def reopen_goal(cb: types.CallbackQuery):
    goal_id = int(cb.data.split("_")[-1])

    result = await rpc("goal.reopen", {
        "tg_user_id": cb.from_user.id,
        "goal_id": goal_id
    })

    await cb.answer("♻️ Цель снова активна")

    await render_goal(cb, goal_id, rpc_result=result)


@router.message(DepositGoal.waiting_for_amount)
async def deposit_amount_handler(message: types.Message, state: FSMContext):
    text = message.text.replace(" ", "").replace(",", ".")

    try:
        amount = float(text)
        if amount <= 0:
            raise ValueError
    except:
        return await message.answer("⚠️ Введи корректную сумму, например: <b>100000</b>")

    data = await state.get_data()
    goal_id = data["goal_id"]

    try:
        await message.delete()
    except:
        pass

    await state.update_data(amount=amount)
    await state.set_state(DepositGoal.waiting_for_confirm)

    bot_msg_id = data.get("bot_message_id")
    if bot_msg_id:
        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=bot_msg_id,
            text=(
                "🧾 <b>Проверьте пополнение</b>\n\n"
                f"💰 Сумма: <b>{format_amount(amount)}</b>\n"
                "Сохранить пополнение?"
            ),
            reply_markup=deposit_confirm_keyboard(goal_id)
        )

    return None


@router.callback_query(DepositGoal.waiting_for_confirm, F.data.regexp(r"^goal_deposit_confirm_\d+$"))
async def deposit_confirm(cb: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    goal_id = data["goal_id"]
    amount = data["amount"]

    try:
        result = await rpc("goal.deposit", {
            "tg_user_id": cb.from_user.id,
            "goal_id": goal_id,
            "amount": amount,
            "method": "manual"
        })
    except (RPCError, RPCTransportError):
        await state.clear()
        await cb.message.edit_text(
            "⚠️ Не удалось сохранить пополнение. Попробуй позже.",
            reply_markup=await get_main_menu(cb.from_user.id)
        )
        return await cb.answer()

    await state.clear()
    await cb.answer("Пополнение сохранено")
    await render_goal(cb, goal_id, rpc_result=result)



async def render_goal(event: types.Message | types.CallbackQuery, goal_id: int, rpc_result=None):
    user_id = event.from_user.id

    if rpc_result:
        goal = rpc_result.get("result") or rpc_result
    else:
        try:
            result = await rpc("goal.get", {"tg_user_id": user_id, "goal_id": goal_id})
            goal = result.get("result") or result
        except (RPCError, RPCTransportError):
            if isinstance(event, types.CallbackQuery):
                await event.message.edit_text(
                    "⚠️ Не удалось загрузить цель. Попробуй позже.",
                    reply_markup=await get_main_menu(event.from_user.id)
                )
                return await event.answer()
            await event.answer("⚠️ Не удалось загрузить цель. Попробуй позже.")
            return None

    icon = goal.get("icon", "🎯")
    title = goal["title"]
    total = goal["amount_total"]
    saved = goal["amount_saved"]
    percent = int(saved / total * 100) if total else 0
    bar = "█" * (percent // 10) + "░" * (10 - percent // 10)

    is_primary = goal.get("is_primary", False)
    pr = goal.get("priority", 1)
    status = goal.get("status", "active")
    deadline = goal.get("deadline") or "Без дедлайна"

    text = (
        f"{icon} <b>{title}</b>\n\n"
        f"💰 {format_amount(saved)} / {format_amount(total)}\n"
        f"📈 Прогресс: <b>{percent}%</b>\n"
        f"{bar}\n"
        f"{SEPARATOR}\n"
        f"⭐ Основная: {'Да' if is_primary else 'Нет'}\n"
        f"🔢 Приоритет: {pr}\n"
        f"📅 Дедлайн: {format_date(deadline)}\n"
    )

    markup = goal_manage_keyboard(goal_id, is_primary, status)

    # Если это callback
    if isinstance(event, types.CallbackQuery):
        try:
            await event.message.edit_text(text, reply_markup=markup)
        except:
            pass
        return await event.answer()

    # Если это обычное сообщение (после ввода суммы)
    if isinstance(event, types.Message):
        return await event.answer(text, reply_markup=markup)
