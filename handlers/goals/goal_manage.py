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
from i18n import t

router = Router()


def deposit_input_keyboard(goal_id: int, lang: str | None = None):
    kb = InlineKeyboardBuilder()
    kb.button(text=t("common.back", lang), callback_data=f"goal_manage_{goal_id}")
    kb.button(text=t("common.cancel", lang), callback_data="menu_cancel")
    kb.adjust(1)
    return kb.as_markup()


def deposit_confirm_keyboard(goal_id: int, lang: str | None = None):
    kb = InlineKeyboardBuilder()
    kb.button(text=t("common.save", lang), callback_data=f"goal_deposit_confirm_{goal_id}")
    kb.button(text=t("common.back", lang), callback_data=f"goal_manage_{goal_id}")
    kb.adjust(1)
    return kb.as_markup()


def close_confirm_keyboard(goal_id: int, lang: str | None = None):
    kb = InlineKeyboardBuilder()
    kb.button(text=t("goals.button.close", lang), callback_data=f"goal_close_confirm_{goal_id}")
    kb.button(text=t("common.back", lang), callback_data=f"goal_manage_{goal_id}")
    kb.adjust(1)
    return kb.as_markup()


@router.callback_query(F.data == "menu_goals")
async def menu_goals(cb: types.CallbackQuery, lang: str | None = None):
    user_id = cb.from_user.id
    try:
        result = await rpc("goal.list", {"tg_user_id": user_id})
    except (RPCError, RPCTransportError):
        await cb.message.edit_text(
            t("goals.manage.list_error", lang),
            reply_markup=goals_list_keyboard([], lang)
        )
        return await cb.answer()

    res = result.get("result") or result
    goals = res.get("goals", [])

    if not goals:
        kb = InlineKeyboardBuilder()
        kb.button(text=t("goals.menu.create_button", lang), callback_data="menu_newgoal")
        kb.button(text=t("common.back", lang), callback_data="menu_back")
        kb.adjust(1)

        await cb.message.edit_text(
            t("goals.menu.empty", lang),
            reply_markup=kb.as_markup()
        )
        return await cb.answer()

    await cb.message.edit_text(
        t("goals.menu.title", lang),
        reply_markup=goals_list_keyboard(goals, lang)
    )
    await cb.answer()
    return None


@router.callback_query(F.data.startswith("goal_manage_"))
async def goal_manage(cb: types.CallbackQuery, state: FSMContext, lang: str | None = None):
    goal_id = int(cb.data.split("_")[-1])
    user_id = cb.from_user.id
    await state.clear()

    try:
        result = await rpc("goal.get", {"tg_user_id": user_id, "goal_id": goal_id})
    except (RPCError, RPCTransportError):
        await cb.message.edit_text(
            t("goals.manage.load_error", lang),
            reply_markup=await get_main_menu(cb.from_user.id, lang)
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
    deadline = goal.get("deadline") or "—"

    text = (
        f"{icon} <b>{title}</b>\n\n"
        f"💰 {format_amount(saved)} / {format_amount(total)}\n"
        f"📈 {t('label.progress', lang)}: <b>{percent}%</b>\n"
        f"{bar}\n"
        f"{SEPARATOR}\n"
        f"{t('goals.detail.primary', lang)}: {t('common.yes', lang) if is_primary else t('common.no', lang)}\n"
        f"{t('goals.detail.priority', lang)}: {pr}\n"
        f"{t('goals.detail.deadline', lang)}: {format_date(deadline)}\n"
    )

    await cb.message.edit_text(
        text,
        reply_markup=goal_manage_keyboard(goal_id, is_primary, status, lang)
    )
    await cb.answer()


@router.callback_query(F.data.startswith("goal_set_primary_"))
async def set_primary(cb: types.CallbackQuery, lang: str | None = None):
    goal_id = int(cb.data.split("_")[-1])

    await rpc("goal.setPrimary", {
        "tg_user_id": cb.from_user.id,
        "goal_id": goal_id
    })

    await cb.answer(t("goals.manage.primary_updated", lang))
    await menu_goals(cb, lang=lang)


@router.callback_query(F.data.startswith("goal_priority_up_"))
async def priority_up(cb: types.CallbackQuery, lang: str | None = None):
    goal_id = int(cb.data.split("_")[-1])
    await rpc("goal.priority.up", {"tg_user_id": cb.from_user.id, "goal_id": goal_id})

    await render_goal(cb, goal_id, lang=lang)


@router.callback_query(F.data.startswith("goal_priority_down_"))
async def priority_down(cb: types.CallbackQuery, lang: str | None = None):
    goal_id = int(cb.data.split("_")[-1])
    await rpc("goal.priority.down", {"tg_user_id": cb.from_user.id, "goal_id": goal_id})

    await render_goal(cb, goal_id, lang=lang)


@router.callback_query(F.data.regexp(r"^goal_deposit_\d+$"))
async def deposit_start(cb: types.CallbackQuery, state: FSMContext, lang: str | None = None):
    goal_id = int(cb.data.split("_")[-1])

    await state.update_data(goal_id=goal_id, bot_message_id=cb.message.message_id)

    await cb.message.edit_text(
        t("goals.manage.deposit_prompt", lang),
        reply_markup=deposit_input_keyboard(goal_id, lang)
    )

    await state.set_state(DepositGoal.waiting_for_amount)
    await cb.answer()


@router.callback_query(F.data.startswith("goal_close_completed_"))
async def close_goal(cb: types.CallbackQuery, lang: str | None = None):
    goal_id = int(cb.data.split("_")[-1])
    await cb.message.edit_text(
        t("goals.manage.close_prompt", lang),
        reply_markup=close_confirm_keyboard(goal_id, lang)
    )
    await cb.answer()


@router.callback_query(F.data.startswith("goal_close_confirm_"))
async def close_goal_confirm(cb: types.CallbackQuery, lang: str | None = None):
    goal_id = int(cb.data.split("_")[-1])
    try:
        result = await rpc("goal.close", {
            "tg_user_id": cb.from_user.id,
            "goal_id": goal_id
        })
    except (RPCError, RPCTransportError):
        await cb.message.edit_text(
            t("goals.manage.close_error", lang),
            reply_markup=await get_main_menu(cb.from_user.id, lang)
        )
        return await cb.answer()

    await cb.answer(t("goals.manage.closed", lang))
    await render_goal(cb, goal_id, rpc_result=result, lang=lang)


@router.callback_query(F.data.startswith("goal_reopen_"))
async def reopen_goal(cb: types.CallbackQuery, lang: str | None = None):
    goal_id = int(cb.data.split("_")[-1])

    result = await rpc("goal.reopen", {
        "tg_user_id": cb.from_user.id,
        "goal_id": goal_id
    })

    await cb.answer(t("goals.manage.reopened", lang))

    await render_goal(cb, goal_id, rpc_result=result, lang=lang)


@router.message(DepositGoal.waiting_for_amount)
async def deposit_amount_handler(message: types.Message, state: FSMContext, lang: str | None = None):
    text = message.text.replace(" ", "").replace(",", ".")

    try:
        amount = float(text)
        if amount <= 0:
            raise ValueError
    except:
        return await message.answer(t("goals.create.amount_invalid", lang))

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
                f"{t('goals.manage.deposit_confirm_title', lang)}\n\n"
                f"💰 {t('label.amount', lang)}: <b>{format_amount(amount)}</b>\n"
                f"{t('goals.manage.deposit_confirm_question', lang)}"
            ),
            reply_markup=deposit_confirm_keyboard(goal_id, lang)
        )

    return None


@router.callback_query(DepositGoal.waiting_for_confirm, F.data.regexp(r"^goal_deposit_confirm_\d+$"))
async def deposit_confirm(cb: types.CallbackQuery, state: FSMContext, lang: str | None = None):
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
            t("goals.manage.deposit_error", lang),
            reply_markup=await get_main_menu(cb.from_user.id, lang)
        )
        return await cb.answer()

    await state.clear()
    await cb.answer(t("goals.manage.deposit_saved", lang))
    await render_goal(cb, goal_id, rpc_result=result, lang=lang)


async def render_goal(event: types.Message | types.CallbackQuery, goal_id: int, rpc_result=None, lang: str | None = None):
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
                    t("goals.manage.load_error", lang),
                    reply_markup=await get_main_menu(event.from_user.id, lang)
                )
                return await event.answer()
            await event.answer(t("goals.manage.load_error", lang))
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
    deadline = goal.get("deadline") or "—"

    text = (
        f"{icon} <b>{title}</b>\n\n"
        f"💰 {format_amount(saved)} / {format_amount(total)}\n"
        f"📈 {t('label.progress', lang)}: <b>{percent}%</b>\n"
        f"{bar}\n"
        f"{SEPARATOR}\n"
        f"{t('goals.detail.primary', lang)}: {t('common.yes', lang) if is_primary else t('common.no', lang)}\n"
        f"{t('goals.detail.priority', lang)}: {pr}\n"
        f"{t('goals.detail.deadline', lang)}: {format_date(deadline)}\n"
    )

    markup = goal_manage_keyboard(goal_id, is_primary, status, lang)

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
