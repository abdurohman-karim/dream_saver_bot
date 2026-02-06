# handlers/smart.py
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import date
import calendar

from rpc import rpc, RPCError, RPCTransportError
from ui.menus import get_main_menu
from ui.formatting import header, money_line, SEPARATOR
from states.smart_save import SmartSaveFallback
from utils.ui import format_amount
from i18n import t

router = Router()


@router.callback_query(F.data == "menu_smart")
async def smart_save(cb: types.CallbackQuery, state: FSMContext, lang: str | None = None):
    try:
        res = await rpc("smart.save.run", {
            "tg_user_id": cb.from_user.id
        })
    except RPCTransportError:
        await cb.message.edit_text(
            t("smart.error.service_unavailable", lang),
            reply_markup=await get_main_menu(cb.from_user.id, lang)
        )
        return await cb.answer()
    except RPCError:
        await cb.message.edit_text(
            t("smart.error.failed", lang),
            reply_markup=await get_main_menu(cb.from_user.id, lang)
        )
        return await cb.answer()

    status = res.get("status")
    if status != "success":
        if status in {"no_spare_money", "too_small", "no_budget"}:
            fallback = await build_fallback_smart_save(cb.from_user.id, res, lang)
            if fallback:
                await state.set_state(SmartSaveFallback.waiting_for_confirm)
                await state.update_data(
                    amount=fallback["amount"],
                    goal_id=fallback["goal"]["id"],
                    goal_title=fallback["goal"]["title"],
                )
                await cb.message.edit_text(
                    render_fallback_prompt(fallback, lang),
                    reply_markup=fallback_confirm_keyboard(lang)
                )
                return await cb.answer()

        status_map = {
            "no_goal": t("smart.status.no_goal", lang),
            "no_budget": t("smart.status.no_budget", lang),
            "no_spare_money": t("smart.status.no_spare_money", lang),
            "too_small": t("smart.status.too_small", lang),
        }
        message = status_map.get(status, t("smart.status.generic", lang))
        await cb.message.edit_text(
            f"ℹ️ {message}",
            reply_markup=await get_main_menu(cb.from_user.id, lang)
        )
        return await cb.answer()

    goal = res.get("goal", {})

    text = (
        header(t("smart.title", lang), "smart")
        + "\n\n"
        + money_line(t("smart.saved_label", lang), res["safe_save"], "income")
        + "\n"
        + t(
            "smart.success.progress_line",
            lang,
            title=goal.get("title", "—"),
            progress=goal.get("progress", 0),
        )
        + "\n\n"
        + t("smart.success.footer", lang)
    )

    await cb.message.edit_text(text, reply_markup=await get_main_menu(cb.from_user.id, lang))
    await cb.answer()


def fallback_confirm_keyboard(lang: str | None = None):
    kb = InlineKeyboardBuilder()
    kb.button(text=t("smart.fallback.button_confirm", lang), callback_data="smart_fallback_confirm")
    kb.button(text=t("common.cancel", lang), callback_data="menu_cancel")
    kb.adjust(1)
    return kb.as_markup()


def render_fallback_prompt(data: dict, lang: str | None = None) -> str:
    amount = data["amount"]
    goal = data["goal"]
    note = data["note"]

    return (
        header(t("smart.title", lang), "smart")
        + "\n\n"
        + f"💡 {t('smart.fallback.offer', lang, amount=f'<b>{format_amount(amount)}</b>')}\n"
        + f"🎯 {t('label.goal', lang)}: <b>{goal.get('title', '—')}</b>\n"
        + f"{SEPARATOR}\n"
        + f"{note}\n\n"
        + t("smart.fallback.confirm", lang)
    )


@router.callback_query(SmartSaveFallback.waiting_for_confirm, F.data == "smart_fallback_confirm")
async def smart_fallback_confirm(cb: types.CallbackQuery, state: FSMContext, lang: str | None = None):
    data = await state.get_data()
    amount = data.get("amount")
    goal_id = data.get("goal_id")

    if not amount or not goal_id:
        await state.clear()
        await cb.message.edit_text(
            t("smart.fallback.error.retry", lang),
            reply_markup=await get_main_menu(cb.from_user.id, lang)
        )
        return await cb.answer()

    try:
        result = await rpc("goal.deposit", {
            "tg_user_id": cb.from_user.id,
            "goal_id": goal_id,
            "amount": amount,
            "method": "smart_fallback"
        })
    except (RPCError, RPCTransportError):
        await state.clear()
        await cb.message.edit_text(
            t("smart.fallback.error.failed", lang),
            reply_markup=await get_main_menu(cb.from_user.id, lang)
        )
        return await cb.answer()

    goal = result.get("result") or result
    text = (
        header(t("smart.title", lang), "smart")
        + "\n\n"
        + money_line(t("smart.saved_label", lang), amount, "income")
        + "\n"
        + f"🎯 {t('label.goal', lang)}: <b>{goal.get('title', '—')}</b>\n"
        + f"📊 {t('label.progress', lang)}: <b>{goal.get('progress', 0)}%</b>\n\n"
        + t("smart.fallback.success", lang)
    )

    await state.clear()
    await cb.message.edit_text(text, reply_markup=await get_main_menu(cb.from_user.id, lang))
    await cb.answer(t("common.done", lang))


async def build_fallback_smart_save(tg_user_id: int, res: dict, lang: str | None = None) -> dict | None:
    today = date.today()
    last_day = calendar.monthrange(today.year, today.month)[1]
    end_of_month = date(today.year, today.month, last_day)
    days_left = (end_of_month - today).days + 1

    balance = None

    daily_limit = float(res.get("daily_limit", 0) or 0)
    if res.get("status") in {"no_spare_money", "too_small"} and daily_limit > 0:
        return None

    try:
        budget = await rpc("budget.recalculate", {
            "tg_user_id": tg_user_id,
            "month": today.strftime("%Y-%m"),
        })
        income = float(budget.get("income", 0))
        expense = float(budget.get("expenses", 0))
        balance = income - expense
    except (RPCError, RPCTransportError):
        return None

    if balance is None or balance <= 0:
        return None

    safe_amount = compute_safe_fallback(balance, days_left)
    if safe_amount <= 0:
        return None

    goal = await select_fallback_goal(tg_user_id)
    if not goal:
        return None

    note = (
        t("smart.fallback.note.no_budget", lang)
        if res.get("status") == "no_budget"
        else t("smart.fallback.note.balance", lang)
    )

    return {
        "amount": safe_amount,
        "goal": goal,
        "note": note,
    }


async def select_fallback_goal(tg_user_id: int) -> dict | None:
    try:
        goals_res = await rpc("goal.list", {"tg_user_id": tg_user_id})
    except (RPCError, RPCTransportError):
        return None

    goals = goals_res.get("goals", [])
    if not goals:
        return None

    primary = next((g for g in goals if g.get("is_primary")), None)
    return primary or goals[0]


def compute_safe_fallback(balance: float, days_left: int) -> int:
    days_left = max(1, days_left)
    base = balance / days_left
    safe = round(base * 0.5)
    if safe <= 0:
        return max(1, int(balance))
    # Minimum sensible amount
    if safe < 1000:
        safe = min(int(balance), 1000)
    return int(min(balance, safe))
