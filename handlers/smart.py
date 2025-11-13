from aiogram import Router, types, F
from rpc import rpc

router = Router()


@router.callback_query(F.data == "menu_smart")
async def smart_save(cb: types.CallbackQuery):
    result = await rpc("smart.save.run", {
        "tg_user_id": cb.from_user.id
    })

    res = result.get("result") or result

    if res["status"] != "success":
        await cb.message.answer(f"⚠️ {res['message']}")
        return await cb.answer()

    goal = res["goal"]

    text = (
        f"🤖 Smart Save выполнен!\n\n"
        f"💰 Отложено: <b>{res['safe_save']:,} сум</b>\n"
        f"📊 Прогресс цели '{goal['title']}': {goal['progress']}%\n"
    )

    await cb.message.answer(text)
    await cb.answer()
