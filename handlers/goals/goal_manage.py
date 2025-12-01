# handlers/goal_manage.py

from aiogram import Router, types, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext

from rpc import rpc
from keyboards.goals_manage import goals_list_keyboard, goal_manage_keyboard
from states.goals import DepositGoal

router = Router()


@router.callback_query(F.data == "menu_goals")
async def menu_goals(cb: types.CallbackQuery):
    user_id = cb.from_user.id

    result = await rpc("goal.list", {"tg_user_id": user_id})

    if "error" in result:
        await cb.message.edit_text(
            f"⚠️ Ошибка сервера при загрузке целей.",
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
            "У тебя ещё нет целей.\n\nНажми «Создать цель» в главном меню 🎯",
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
async def goal_manage(cb: types.CallbackQuery):
    goal_id = int(cb.data.split("_")[-1])
    user_id = cb.from_user.id

    result = await rpc("goal.get", {"tg_user_id": user_id, "goal_id": goal_id})
    res = result.get("result") or result
    goal = res

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
        f"💰 {saved:,} / {total:,}\n"
        f"📈 Прогресс: {percent}%\n"
        f"{bar}\n\n"
        f"⭐ Основная: {'Да' if is_primary else 'Нет'}\n"
        f"🔢 Приоритет: {pr}\n"
        f"📅 Дедлайн: {deadline}\n"
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

    await cb.answer("⭐ Теперь это основная цель")
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


@router.callback_query(F.data.startswith("goal_deposit_"))
async def deposit_start(cb: types.CallbackQuery, state: FSMContext):
    goal_id = int(cb.data.split("_")[-1])

    await state.update_data(goal_id=goal_id)

    await cb.message.edit_text(
        "💸 <b>Введите сумму пополнения</b>\n\n"
        "Можно отправить просто число, например: <b>150000</b>.\n"
        "Для отмены нажмите «Назад»."
    )

    await state.set_state(DepositGoal.waiting_for_amount)
    await cb.answer()

@router.callback_query(F.data.startswith("goal_close_completed_"))
async def close_goal(cb: types.CallbackQuery):
    goal_id = int(cb.data.split("_")[-1])

    result = await rpc("goal.close", {
        "tg_user_id": cb.from_user.id,
        "goal_id": goal_id
    })

    await cb.answer("🛑 Цель закрыта")

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

    result = await rpc("goal.deposit", {
        "tg_user_id": message.from_user.id,
        "goal_id": goal_id,
        "amount": amount,
        "method": "manual"
    })

    goal = result.get("result") or result

    await state.clear()

    try:
        await message.delete()
    except:
        pass

    pretty = f"{amount:,.0f}".replace(",", " ")

    await message.answer(
        f"💰 <b>Успешно пополнено!</b>\n"
        f"Ты добавил <b>{pretty} сум</b> в цель <b>{goal['title']}</b> 🎯",
    )

    await render_goal(message, goal_id, rpc_result=result)



async def render_goal(event: types.Message | types.CallbackQuery, goal_id: int, rpc_result=None):
    user_id = event.from_user.id

    if rpc_result:
        goal = rpc_result.get("result") or rpc_result
    else:
        result = await rpc("goal.get", {"tg_user_id": user_id, "goal_id": goal_id})
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
        f"💰 {saved:,} / {total:,}\n"
        f"📈 Прогресс: {percent}%\n"
        f"{bar}\n\n"
        f"⭐ Основная: {'Да' if is_primary else 'Нет'}\n"
        f"🔢 Приоритет: {pr}\n"
        f"📅 Дедлайн: {deadline}\n"
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


