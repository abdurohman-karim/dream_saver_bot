# handlers/progress.py
from aiogram import Router, types, F

from rpc import rpc, RPCError, RPCTransportError
from keyboards.keyboards import back_button
from utils.ui import format_amount
from ui.formatting import header, SEPARATOR

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
            "📊 Пока нет целей.\nСоздай первую — и начнем отслеживать прогресс.",
            reply_markup=back_button()
        )
        return await cb.answer()

    text = header("Прогресс по целям", "insights") + "\n\n"

    for g in goals:
        total = float(g.get("amount_total", 0) or 0)
        saved = float(g.get("amount_saved", 0) or 0)
        percent = int(saved / total * 100) if total else 0

        text += (
            f"🎯 <b>{g['title']}</b>\n"
            f"💰 Накоплено: <b>{format_amount(saved)}</b> / {format_amount(total)}\n"
            f"📈 Прогресс: <b>{percent}%</b>\n"
            f"{SEPARATOR}\n"
        )

    await cb.message.edit_text(
        text,
        reply_markup=back_button()
    )
    await cb.answer()
