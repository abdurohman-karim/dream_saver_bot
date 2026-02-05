# handlers/onboarding.py
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import date

from states.onboarding import OnboardingStates
from ui.menus import get_main_menu
from ui.formatting import header, money_line, SEPARATOR
from rpc import rpc, RPCError, RPCTransportError
from handlers.goals.goal_create import new_goal_start
from handlers.add_income import add_income_start
from handlers.add_transaction import add_start

router = Router()


def onboarding_start_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="Начать", callback_data="onb_start")
    kb.button(text="Пропустить", callback_data="onb_skip")
    kb.adjust(2)
    return kb.as_markup()


def onboarding_focus_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="🎯 Копить на цель", callback_data="onb_focus_save")
    kb.button(text="📌 Контроль расходов", callback_data="onb_focus_track")
    kb.button(text="Пропустить", callback_data="onb_skip")
    kb.adjust(1)
    return kb.as_markup()


def onboarding_goal_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="🎯 Создать цель", callback_data="onb_goal_create")
    kb.button(text="Пропустить", callback_data="onb_goal_skip")
    kb.adjust(1)
    return kb.as_markup()


def onboarding_income_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="💰 Добавить доход", callback_data="onb_income_add")
    kb.button(text="💸 Добавить расход", callback_data="onb_expense_add")
    kb.button(text="Позже", callback_data="onb_finish")
    kb.adjust(1)
    return kb.as_markup()


async def start_onboarding(message: types.Message, state: FSMContext | None = None):
    if state:
        await state.set_state(OnboardingStates.welcome)
    await message.answer(
        header("Добро пожаловать в Finora", "info")
        + "\n\n"
        + "Я помогу вести финансы спокойно и системно.\n"
        + "Небольшая настройка займет меньше минуты.",
        reply_markup=onboarding_start_keyboard()
    )


@router.callback_query(F.data == "onb_start")
async def onboarding_begin(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(OnboardingStates.focus)
    await cb.message.edit_text(
        header("С чего начнем?", "info")
        + "\n\n"
        + "Выбери главный фокус на сегодня.",
        reply_markup=onboarding_focus_keyboard()
    )
    await cb.answer()


@router.callback_query(F.data == "onb_skip")
async def onboarding_skip(cb: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.edit_text(
        header("Главное меню", "info")
        + "\n\n"
        + "Дальше можно двигаться в своем темпе.",
        reply_markup=await get_main_menu(cb.from_user.id)
    )
    await cb.answer()


@router.callback_query(F.data.in_(["onb_focus_save", "onb_focus_track"]))
async def onboarding_focus(cb: types.CallbackQuery, state: FSMContext):
    focus = "save" if cb.data == "onb_focus_save" else "track"
    await state.update_data(focus=focus)
    await state.set_state(OnboardingStates.offer_goal)

    title = "Давай зафиксируем первую цель" if focus == "save" else "Можно создать цель и для контроля"
    text = (
        header(title, "goal")
        + "\n\n"
        + "Цель помогает держать фокус и видеть прогресс."
    )

    await cb.message.edit_text(text, reply_markup=onboarding_goal_keyboard())
    await cb.answer()


@router.callback_query(F.data == "onb_goal_create")
async def onboarding_goal_create(cb: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.answer()
    return await new_goal_start(cb, state)


@router.callback_query(F.data == "onb_goal_skip")
async def onboarding_goal_skip(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(OnboardingStates.offer_income)
    await cb.message.edit_text(
        header("Добавим первую операцию", "info")
        + "\n\n"
        + "Это поможет сразу увидеть реальную картину.",
        reply_markup=onboarding_income_keyboard()
    )
    await cb.answer()


@router.callback_query(F.data == "onb_income_add")
async def onboarding_income_add(cb: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.answer()
    return await add_income_start(cb, state)


@router.callback_query(F.data == "onb_expense_add")
async def onboarding_expense_add(cb: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.answer()
    return await add_start(cb, state)


@router.callback_query(F.data == "onb_finish")
async def onboarding_finish(cb: types.CallbackQuery, state: FSMContext):
    await state.clear()

    today = date.today().isoformat()
    try:
        daily = await rpc("transaction.getDaily", {"tg_user_id": cb.from_user.id, "date": today})
    except (RPCError, RPCTransportError):
        daily = {}

    income = daily.get("income", 0)
    expense = daily.get("expense", 0)
    balance = float(income) - float(expense)

    lines = [
        money_line("Доход", income, "income", sign="+"),
        money_line("Расход", expense, "expense", sign="-"),
        SEPARATOR,
        money_line("Баланс", balance, "progress"),
    ]

    text = header("Сегодняшняя сводка", "insights") + "\n\n" + "\n".join(lines)

    await cb.message.edit_text(
        text,
        reply_markup=await get_main_menu(cb.from_user.id)
    )
    await cb.answer()
