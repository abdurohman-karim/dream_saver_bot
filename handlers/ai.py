# handlers/ai.py
from aiogram import Router, types, F

from rpc import rpc, RPCError, RPCTransportError

router = Router()


@router.callback_query(F.data == "menu_daily")
async def ai_daily(cb: types.CallbackQuery):
    try:
        res = await rpc("ai.insight.daily", {
            "tg_user_id": cb.from_user.id
        })
    except RPCTransportError:
        await cb.message.answer("⚠️ Сервер недоступен. Попробуй позже.")
        return await cb.answer()
    except RPCError as e:
        await cb.message.answer(f"⚠️ Ошибка AI:\n{e}")
        return await cb.answer()

    insight = res.get("insight")
    if not insight:
        await cb.message.answer("⚠️ Ошибка AI: сервер не вернул insight.")
        return await cb.answer()

    text = f"💡 Совет от ИИ:\n\n{insight}"
    await cb.message.answer(text)
    await cb.answer()
