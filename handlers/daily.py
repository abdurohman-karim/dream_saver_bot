# handlers/daily.py
from aiogram import Router, types, F
from datetime import date

from rpc import rpc, RPCError, RPCTransportError
from keyboards.today_menu import today_menu
from utils.ui import format_amount, format_date, format_datetime, clean_text
from ui.formatting import header, money_line, SEPARATOR

router = Router()


@router.callback_query(F.data == "menu_today")
async def show_today_transactions(cb: types.CallbackQuery):
    today = date.today().isoformat()

    try:
        stats = await rpc("transaction.getDaily", {
            "tg_user_id": cb.from_user.id,
            "date": today,
        })
    except RPCTransportError:
        await cb.message.edit_text(
            "⚠️ Сервис недоступен. Попробуй позже.",
            reply_markup=today_menu()
        )
        return await cb.answer()
    except RPCError:
        await cb.message.edit_text(
            "⚠️ Не удалось получить операции. Попробуй позже.",
            reply_markup=today_menu()
        )
        return await cb.answer()

    income = float(stats.get("income", 0))
    expense = float(stats.get("expense", 0))
    items = stats.get("items", [])

    if not items:
        text = (
            header("Сегодня", "insights")
            + "\n\n"
            + f"Дата: <b>{format_date(stats.get('date'))}</b>\n"
            + "Пока нет операций за сегодня.\n"
            + "Добавим первую запись, чтобы видеть динамику."
        )
        await cb.message.edit_text(text, reply_markup=today_menu())
        return await cb.answer()

    balance = income - expense
    text = (
        header("Сегодня", "insights")
        + "\n\n"
        + f"Дата: <b>{format_date(stats.get('date'))}</b>\n"
        + money_line("Доход", income, "income", sign="+") + "\n"
        + money_line("Расход", expense, "expense", sign="-") + "\n"
        + SEPARATOR + "\n"
        + money_line("Баланс", balance, "progress") + "\n\n"
        + "Операции:\n"
    )

    for t in items:
        amount = float(t["amount"])
        sign = "➕" if amount > 0 else "➖"
        cat = t.get("category") or "Без категории"
        desc = clean_text(t.get("description") or "", 60)
        dt = format_datetime(t.get("datetime") or "")
        amount_text = format_amount(abs(amount))
        line = f"{sign} <b>{amount_text}</b> — {cat}"
        if dt:
            line += f" · {dt}"
        if desc:
            line += f" · {desc}"
        text += line + "\n"

    await cb.message.edit_text(
        text,
        reply_markup=today_menu()
    )
    await cb.answer()
