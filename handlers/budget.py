# handlers/budget.py
from aiogram import Router, types, F
from datetime import date

from rpc import rpc, RPCError, RPCTransportError
from keyboards.keyboards import back_button

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
            "⚠️ Сервер недоступен. Попробуй позже.",
            reply_markup=back_button()
        )
        return await cb.answer()
    except RPCError as e:
        await cb.message.edit_text(
            f"⚠️ Ошибка при получении бюджета:\n{e}",
            reply_markup=back_button()
        )
        return await cb.answer()

    income = float(budget.get("income", 0))
    expenses = float(budget.get("expenses", 0))
    daily_limit = float(budget.get("recommended_daily_limit", 0))

    text = (
        f"📅 <b>Бюджет за {budget.get('month')}</b>\n\n"
        f"💸 Доходы: <b>{income:,.0f} сум</b>\n"
        f"💰 Расходы: <b>{expenses:,.0f} сум</b>\n"
        f"📉 Рекомендуемый дневной лимит: <b>{daily_limit:,.0f} сум</b>\n"
    )

    await cb.message.edit_text(
        text,
        reply_markup=back_button()
    )
    await cb.answer()
