# handlers/budget.py
from aiogram import Router, types, F
from datetime import date

from rpc import rpc, RPCError, RPCTransportError
from keyboards.keyboards import back_button
from ui.formatting import header, money_line
from i18n import t

router = Router()


@router.callback_query(F.data == "menu_budget")
async def show_budget(cb: types.CallbackQuery, lang: str | None = None):
    today = date.today()
    month_str = today.strftime("%Y-%m")

    try:
        # сразу пересчитываем бюджет за месяц
        budget = await rpc("budget.recalculate", {
            "tg_user_id": cb.from_user.id,
            "month": month_str,
        })
    except RPCTransportError:
        await cb.message.edit_text(
            t("budget.error.service_unavailable", lang),
            reply_markup=back_button(lang)
        )
        return await cb.answer()
    except RPCError:
        await cb.message.edit_text(
            t("budget.error.failed", lang),
            reply_markup=back_button(lang)
        )
        return await cb.answer()

    income = float(budget.get("income", 0))
    expenses = float(budget.get("expenses", 0))
    daily_limit = float(budget.get("recommended_daily_limit", 0))

    text = (
        header(t("budget.title", lang, month=budget.get("month")), "budget")
        + "\n\n"
        + money_line(t("label.budget_incomes", lang), income, "income")
        + "\n"
        + money_line(t("label.budget_expenses", lang), expenses, "expense")
        + "\n"
        + money_line(t("label.daily_limit", lang), daily_limit, "progress")
        + "\n\n"
        + t("budget.footer", lang)
    )

    await cb.message.edit_text(
        text,
        reply_markup=back_button(lang)
    )
    await cb.answer()
