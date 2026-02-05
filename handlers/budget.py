# handlers/budget.py
from aiogram import Router, types, F
from datetime import date

from rpc import rpc, RPCError, RPCTransportError
from keyboards.keyboards import back_button
from ui.formatting import header, money_line

router = Router()


@router.callback_query(F.data == "menu_budget")
async def show_budget(cb: types.CallbackQuery):
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
            "⚠️ Сервис недоступен. Попробуй позже.",
            reply_markup=back_button()
        )
        return await cb.answer()
    except RPCError:
        await cb.message.edit_text(
            "⚠️ Не удалось получить бюджет. Попробуй позже.",
            reply_markup=back_button()
        )
        return await cb.answer()

    income = float(budget.get("income", 0))
    expenses = float(budget.get("expenses", 0))
    daily_limit = float(budget.get("recommended_daily_limit", 0))

    text = (
        header(f"Бюджет · {budget.get('month')}", "budget")
        + "\n\n"
        + money_line("Доходы", income, "income")
        + "\n"
        + money_line("Расходы", expenses, "expense")
        + "\n"
        + money_line("Дневной лимит", daily_limit, "progress")
        + "\n\n"
        + "Это ориентир, чтобы тратить спокойно и без стресса."
    )

    await cb.message.edit_text(
        text,
        reply_markup=back_button()
    )
    await cb.answer()
