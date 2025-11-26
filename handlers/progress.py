# handlers/progress.py
from aiogram import Router, types, F

from rpc import rpc, RPCError, RPCTransportError
from keyboards.keyboards import back_button

router = Router()


@router.callback_query(F.data == "menu_progress")
async def menu_progress(cb: types.CallbackQuery):
    user_id = cb.from_user.id

    try:
        res = await rpc("goal.list", {"tg_user_id": user_id})
    except (RPCError, RPCTransportError):
        await cb.message.edit_text(
            "⚠️ Не удалось получить прогресс.\nПопробуй позже.",
            reply_markup=back_button()
        )
        return await cb.answer()

    goals = res.get("goals", [])
    if not goals:
        await cb.message.edit_text(
            "📊 У тебя пока нет целей.\nСоздай первую 🎯",
            reply_markup=back_button()
        )
        return await cb.answer()

    text = "📊 <b>Твой прогресс по целям:</b>\n\n"

    for g in goals:
        total = float(g.get("amount_total", 0) or 0)
        saved = float(g.get("amount_saved", 0) or 0)
        percent = int(saved / total * 100) if total else 0

        text += (
            f"🎯 <b>{g['title']}</b>\n"
            f"💰 Накоплено: <b>{saved:,.0f}</b> / {total:,.0f}\n"
            f"📈 Прогресс: <b>{percent}%</b>\n"
            "──────────────\n"
        )

    await cb.message.edit_text(
        text,
        reply_markup=back_button()
    )
    await cb.answer()
