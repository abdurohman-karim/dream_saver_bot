# handlers/ai.py
from aiogram import Router, types, F

from rpc import rpc, RPCError, RPCTransportError
from keyboards.keyboards import back_button
from ui.formatting import header

router = Router()


@router.callback_query(F.data == "menu_daily")
async def ai_daily(cb: types.CallbackQuery):
    try:
        res = await rpc("ai.insight.daily", {
            "tg_user_id": cb.from_user.id
        })
    except RPCTransportError:
        await cb.message.edit_text(
            "⚠️ Сервис недоступен. Попробуй позже.",
            reply_markup=back_button()
        )
        return await cb.answer()
    except RPCError:
        await cb.message.edit_text(
            "⚠️ Не удалось получить совет. Попробуй позже.",
            reply_markup=back_button()
        )
        return await cb.answer()

    insight = res.get("insight")
    if not insight:
        await cb.message.edit_text(
            "⚠️ Совет временно недоступен. Попробуй позже.",
            reply_markup=back_button()
        )
        return await cb.answer()

    text = header("Совет дня", "tip") + "\n\n" + insight
    await cb.message.edit_text(text, reply_markup=back_button())
    await cb.answer()
    return None
