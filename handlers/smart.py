# handlers/smart.py
from aiogram import Router, types, F

from rpc import rpc, RPCError, RPCTransportError

router = Router()


@router.callback_query(F.data == "menu_smart")
async def smart_save(cb: types.CallbackQuery):
    try:
        res = await rpc("smart.save.run", {
            "tg_user_id": cb.from_user.id
        })
    except RPCTransportError:
        await cb.message.answer("⚠️ Сервер недоступен. Попробуй позже.")
        return await cb.answer()
    except RPCError as e:
        await cb.message.answer(f"⚠️ Ошибка Smart Save:\n{e}")
        return await cb.answer()

    status = res.get("status")
    if status != "success":
        await cb.message.answer(f"⚠️ {res.get('message', 'Неизвестная ошибка')}")
        return await cb.answer()

    goal = res.get("goal", {})

    text = (
        f"🤖 Smart Save выполнен!\n\n"
        f"💰 Отложено: <b>{res['safe_save']:,} сум</b>\n"
        f"📊 Прогресс цели '{goal.get('title', '—')}': {goal.get('progress', 0)}%\n"
    )

    await cb.message.answer(text)
    await cb.answer()
