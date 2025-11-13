from aiogram import Router, types, F
from rpc import rpc

router = Router()


@router.callback_query(F.data == "menu_daily")
async def ai_daily(cb: types.CallbackQuery):
    result = await rpc("ai.insight.daily", {
        "tg_user_id": cb.from_user.id
    })

    print("RPC RESPONSE:", result)

    res = result.get("result") or result

    insight = res.get("insight", None)
    if not insight:
        await cb.message.answer("⚠️ Ошибка AI:\n\nСервер не вернул insight.")
        return await cb.answer()

    text = f"💡 Совет от ИИ:\n\n{insight}"
    await cb.message.answer(text)
    await cb.answer()

