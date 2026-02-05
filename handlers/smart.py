# handlers/smart.py
from aiogram import Router, types, F

from rpc import rpc, RPCError, RPCTransportError
from ui.menus import get_main_menu
from ui.formatting import header, money_line

router = Router()


@router.callback_query(F.data == "menu_smart")
async def smart_save(cb: types.CallbackQuery):
    try:
        res = await rpc("smart.save.run", {
            "tg_user_id": cb.from_user.id
        })
    except RPCTransportError:
        await cb.message.edit_text(
            "⚠️ Сервис недоступен. Попробуй позже.",
            reply_markup=await get_main_menu(cb.from_user.id)
        )
        return await cb.answer()
    except RPCError:
        await cb.message.edit_text(
            "⚠️ Не удалось выполнить Smart Save. Попробуй позже.",
            reply_markup=await get_main_menu(cb.from_user.id)
        )
        return await cb.answer()

    status = res.get("status")
    if status != "success":
        status_map = {
            "no_goal": "Нужна активная цель, чтобы включить Smart Save.",
            "no_budget": "Сначала настроим бюджет, чтобы рассчитать безопасную сумму.",
            "no_spare_money": "Сегодня нет безопасной суммы для отложений — это нормально.",
            "too_small": "Остаток слишком мал для отложений. Вернемся к этому завтра.",
        }
        message = status_map.get(status, "Не удалось выполнить операцию.")
        await cb.message.edit_text(
            f"ℹ️ {message}",
            reply_markup=await get_main_menu(cb.from_user.id)
        )
        return await cb.answer()

    goal = res.get("goal", {})

    text = (
        header("Smart Save", "smart")
        + "\n\n"
        + money_line("Отложено", res["safe_save"], "income")
        + "\n"
        + f"📊 Прогресс цели «{goal.get('title', '—')}»: <b>{goal.get('progress', 0)}%</b>\n\n"
        + "Небольшие шаги дают сильный результат. Продолжим?"
    )

    await cb.message.edit_text(text, reply_markup=await get_main_menu(cb.from_user.id))
    await cb.answer()
