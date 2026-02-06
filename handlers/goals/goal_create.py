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
from i18n import t

router = Router()


async def safe_delete(message: types.Message):
    try:
        await message.delete()
    except:
        pass


async def render_create_window(cb_or_msg, state: FSMContext, lang: str | None = None):
    data = await state.get_data()

    title = data.get("title", "—")
    amount = data.get("amount_total", "—")
    deadline = data.get("deadline", "—")

    if isinstance(amount, int):
        amount_fmt = format_amount(amount)
    else:
        amount_fmt = amount

    text = (
        f"{t('goals.create.window.title', lang)}\n\n"
        f"{t('goals.create.window.label_title', lang)}: <b>{title}</b>\n"
        f"{t('goals.create.window.label_amount', lang)}: <b>{amount_fmt}</b>\n"
        f"{t('goals.create.window.label_deadline', lang)}: <b>{format_date(deadline) if deadline else '—'}</b>"
    )

    bot_msg_id = data["bot_message_id"]

    await cb_or_msg.bot.edit_message_text(
        chat_id=cb_or_msg.chat.id if isinstance(cb_or_msg, types.Message) else cb_or_msg.message.chat.id,
        message_id=bot_msg_id,
        text=text,
        reply_markup=cancel_button(lang)
    )


async def finish_goal_create(cb_or_msg, state: FSMContext, lang: str | None = None):
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
                t("goals.create.error", lang),
                reply_markup=await get_main_menu(cb_or_msg.from_user.id, lang)
            )
        else:
            await cb_or_msg.answer(
                t("goals.create.error", lang),
                reply_markup=await get_main_menu(cb_or_msg.from_user.id, lang)
            )
        await state.clear()
        return

    await state.clear()

    amount_fmt = format_amount(data["amount_total"])

    text = t(
        "goals.create.success",
        lang,
        title=data["title"],
        amount=amount_fmt,
        deadline=format_date(data.get("deadline"))
    )

    if isinstance(cb_or_msg, types.CallbackQuery):
        await cb_or_msg.message.answer(text, reply_markup=await get_main_menu(cb_or_msg.from_user.id, lang))
    else:
        await cb_or_msg.answer(text, reply_markup=await get_main_menu(cb_or_msg.from_user.id, lang))


@router.callback_query(F.data == "menu_newgoal")
async def new_goal_start(cb: types.CallbackQuery, state: FSMContext, lang: str | None = None):
    await state.set_state(GoalStates.waiting_for_title)

    sent = await cb.message.edit_text(
        f"{t('goals.create.window.title', lang)}\n\n{t('goals.create.ask_title', lang)}",
        reply_markup=cancel_button(lang)
    )

    await state.update_data(bot_message_id=sent.message_id)
    await cb.answer()


@router.message(GoalStates.waiting_for_title)
async def set_title(message: types.Message, state: FSMContext, lang: str | None = None):
    title = message.text.strip()
    if len(title) < 2:
        await safe_delete(message)
        return await message.answer(t("goals.create.title_short", lang))

    await state.update_data(title=title)
    await safe_delete(message)

    await state.set_state(GoalStates.waiting_for_amount)

    await render_create_window(message, state, lang)
    await message.answer(t("goals.create.ask_amount", lang))


@router.message(GoalStates.waiting_for_amount)
async def set_amount(message: types.Message, state: FSMContext, lang: str | None = None):
    amount = parse_amount(message.text)
    if amount is None:
        await safe_delete(message)
        return await message.answer(t("goals.create.amount_invalid", lang))
    await state.update_data(amount_total=int(amount))
    await safe_delete(message)

    await state.set_state(GoalStates.waiting_for_deadline)

    await render_create_window(message, state, lang)
    await message.answer(
        t("goals.create.ask_deadline", lang),
        reply_markup=deadline_keyboard(lang)
    )


@router.callback_query(
    StateFilter(GoalStates.waiting_for_deadline),
    F.data.regexp(r"^deadline_\d{4}-\d{2}-\d{2}$")
)
async def choose_deadline(cb: types.CallbackQuery, state: FSMContext, lang: str | None = None):
    raw = cb.data.replace("deadline_", "")
    await state.update_data(deadline=raw)

    await cb.answer()
    return await finish_goal_create(cb, state, lang)


@router.callback_query(
    StateFilter(GoalStates.waiting_for_deadline),
    F.data == "deadline_none"
)
async def no_deadline(cb: types.CallbackQuery, state: FSMContext, lang: str | None = None):
    await state.update_data(deadline=None)
    await cb.answer()
    return await finish_goal_create(cb, state, lang)


@router.callback_query(
    StateFilter(GoalStates.waiting_for_deadline),
    F.data == "deadline_manual"
)
async def manual_deadline_start(cb: types.CallbackQuery, state: FSMContext, lang: str | None = None):
    await cb.answer()
    await state.set_state(GoalStates.waiting_for_manual_deadline)

    await cb.message.edit_text(
        t("goals.create.manual_deadline_prompt", lang),
        reply_markup=cancel_button(lang)
    )


@router.message(StateFilter(GoalStates.waiting_for_manual_deadline))
async def manual_deadline_input(message: types.Message, state: FSMContext, lang: str | None = None):
    raw = message.text.strip()

    try:
        deadline = datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        await safe_delete(message)
        return await message.answer(t("goals.create.manual_deadline_invalid", lang))

    await safe_delete(message)
    await state.update_data(deadline=str(deadline))

    return await finish_goal_create(message, state, lang)
