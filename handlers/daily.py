# handlers/daily.py
from aiogram import Router, types, F
from datetime import date

from rpc import rpc, RPCError, RPCTransportError
from keyboards.keyboards import back_button
from keyboards.today_menu import today_menu

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
            "⚠️ Сервер недоступен. Попробуй позже.",
            reply_markup=today_menu()
        )
        return await cb.answer()
    except RPCError as e:
        await cb.message.edit_text(
            f"⚠️ Ошибка запроса транзакций:\n{e}",
            reply_markup=today_menu()
        )
        return await cb.answer()

    income = float(stats.get("income", 0))
    expense = float(stats.get("expense", 0))
    items = stats.get("items", [])

    if not items:
        text = (
            f"💸 <b>Сегодня ({stats.get('date')}) у тебя нет зарегистрированных трат.</b>\n"
            "Можно отложить чуть больше в цель 😉"
        )
        await cb.message.edit_text(text, reply_markup=today_menu())
        return await cb.answer()

    text = (
        f"💸 <b>Траты за {stats.get('date')}:</b>\n\n"
        f"➕ Доход: <b>{income:,.0f} сум</b>\n"
        f"➖ Расход: <b>{expense:,.0f} сум</b>\n\n"
        "Список операций:\n"
    )

    for t in items:
        amount = float(t["amount"])
        sign = "➕" if amount > 0 else "➖"
        cat = t.get("category") or "Без категории"
        desc = t.get("description") or ""
        dt = t.get("datetime") or ""
        text += f"{sign} <b>{amount:,.0f}</b> — {cat} ({dt}) {desc}\n"

    await cb.message.edit_text(
        text,
        reply_markup=today_menu()
    )
    await cb.answer()
