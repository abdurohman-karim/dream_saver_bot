# handlers/smart.py
from aiogram import Router, types, F
from datetime import date
import calendar

from rpc import rpc, RPCError, RPCTransportError
from ui.menus import get_main_menu
from ui.formatting import header, money_line
from utils.ui import format_amount

router = Router()


@router.callback_query(F.data == "menu_smart")
async def smart_save(cb: types.CallbackQuery):
    try:
        res = await rpc("smart.save.run", {
            "tg_user_id": cb.from_user.id
        })
    except RPCTransportError:
        await cb.message.edit_text(
            "⚠️ Сервис недоступен. Попробуй позже.",
            reply_markup=await get_main_menu(cb.from_user.id)
        )
        return await cb.answer()
    except RPCError:
        await cb.message.edit_text(
            "⚠️ Не удалось выполнить Smart Save. Попробуй позже.",
            reply_markup=await get_main_menu(cb.from_user.id)
        )
        return await cb.answer()

    status = res.get("status")
    if status != "success":
        if status in {"no_spare_money", "too_small", "no_budget"}:
            fallback_text = await build_fallback_smart_save(cb.from_user.id, res)
            if fallback_text:
                await cb.message.edit_text(
                    fallback_text,
                    reply_markup=await get_main_menu(cb.from_user.id)
                )
                return await cb.answer()

        status_map = {
            "no_goal": "Нужна активная цель, чтобы включить Smart Save.",
            "no_budget": "Сначала настроим бюджет, чтобы рассчитать безопасную сумму.",
            "no_spare_money": "Сегодня нет безопасной суммы для отложений — это нормально.",
            "too_small": "Остаток слишком мал для отложений. Вернемся к этому завтра.",
        }
        message = status_map.get(status, "Не удалось выполнить операцию.")
        await cb.message.edit_text(
            f"ℹ️ {message}",
            reply_markup=await get_main_menu(cb.from_user.id)
        )
        return await cb.answer()

    goal = res.get("goal", {})

    text = (
        header("Smart Save", "smart")
        + "\n\n"
        + money_line("Отложено", res["safe_save"], "income")
        + "\n"
        + f"📊 Прогресс цели «{goal.get('title', '—')}»: <b>{goal.get('progress', 0)}%</b>\n\n"
        + "Небольшие шаги дают сильный результат. Продолжим?"
    )

    await cb.message.edit_text(text, reply_markup=await get_main_menu(cb.from_user.id))
    await cb.answer()


async def build_fallback_smart_save(tg_user_id: int, res: dict) -> str | None:
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

    note = (
        "Это рассчитано без установленного бюджета."
        if res.get("status") == "no_budget"
        else "Это рассчитано на основе текущего баланса."
    )

    return (
        "💡 Сегодня вы можете безопасно отложить\n"
        f"<b>{format_amount(safe_amount)}</b>\n\n"
        f"{note}"
    )


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
