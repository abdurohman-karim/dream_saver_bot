# handlers/insights.py
from aiogram import Router, types, F

from rpc import rpc, RPCError, RPCTransportError
from keyboards.keyboards import insights_menu
from ui.formatting import header, money_line, SEPARATOR
from utils.ui import clean_text

router = Router()


@router.callback_query(F.data == "menu_insights")
async def menu_insights(cb: types.CallbackQuery):
    text = (
        header("Insights", "insights")
        + "\n\n"
        + "Аналитика и подсказки по твоим финансам.\n"
        + "Выбери раздел ниже."
    )
    await cb.message.edit_text(text, reply_markup=insights_menu())
    await cb.answer()


@router.callback_query(F.data == "insights_week")
async def insights_week(cb: types.CallbackQuery):
    await cb.answer("Готовлю обзор недели...")
    try:
        res = await rpc("ai.transaction.analysis", {
            "tg_user_id": cb.from_user.id,
            "days": 7,
        })
    except (RPCError, RPCTransportError):
        await cb.message.edit_text(
            "⚠️ Не удалось подготовить обзор. Попробуй позже.",
            reply_markup=insights_menu()
        )
        return await cb.answer()

    summary = clean_text(res.get("summary") or "Обзор пока недоступен.", 600)
    recommendation = clean_text(res.get("recommendation") or "", 300)

    text = (
        header("Обзор недели", "insights")
        + "\n\n"
        + summary
    )
    if recommendation:
        text += "\n\n" + header("Рекомендация", "tip") + "\n" + recommendation

    await cb.message.edit_text(text, reply_markup=insights_menu())
    await cb.answer()


@router.callback_query(F.data == "insights_trend")
async def insights_trend(cb: types.CallbackQuery):
    await cb.answer("Смотрю динамику расходов...")
    try:
        res = await rpc("ai.transaction.analysis", {
            "tg_user_id": cb.from_user.id,
            "days": 30,
        })
    except (RPCError, RPCTransportError):
        await cb.message.edit_text(
            "⚠️ Не удалось получить тренд. Попробуй позже.",
            reply_markup=insights_menu()
        )
        return await cb.answer()

    summary = clean_text(res.get("summary") or "Тренд пока недоступен.", 600)
    recommendation = clean_text(res.get("recommendation") or "", 300)

    text = (
        header("Тренд расходов", "insights")
        + "\n\n"
        + summary
    )
    if recommendation:
        text += "\n\n" + header("Рекомендация", "tip") + "\n" + recommendation

    await cb.message.edit_text(text, reply_markup=insights_menu())
    await cb.answer()


@router.callback_query(F.data == "insights_savings")
async def insights_savings(cb: types.CallbackQuery):
    try:
        res = await rpc("goal.list", {"tg_user_id": cb.from_user.id})
    except (RPCError, RPCTransportError):
        await cb.message.edit_text(
            "⚠️ Не удалось получить прогресс. Попробуй позже.",
            reply_markup=insights_menu()
        )
        return await cb.answer()

    goals = res.get("goals", [])
    if not goals:
        await cb.message.edit_text(
            header("Прогресс накоплений", "goal")
            + "\n\n"
            + "Пока нет целей. Создай первую — и прогресс появится здесь.",
            reply_markup=insights_menu()
        )
        return await cb.answer()

    total_saved = sum(float(g.get("amount_saved") or 0) for g in goals)
    total_target = sum(float(g.get("amount_total") or 0) for g in goals)
    percent = int((total_saved / total_target) * 100) if total_target else 0

    lines = [
        money_line("Накоплено", total_saved, "income"),
        money_line("Цель", total_target, "goal"),
        SEPARATOR,
        f"📈 Прогресс: <b>{percent}%</b>",
    ]

    text = header("Прогресс накоплений", "goal") + "\n\n" + "\n".join(lines)
    await cb.message.edit_text(text, reply_markup=insights_menu())
    await cb.answer()


@router.callback_query(F.data == "insights_tip")
async def insights_tip(cb: types.CallbackQuery):
    await cb.answer("Подбираю совет...")
    try:
        res = await rpc("ai.insight.daily", {"tg_user_id": cb.from_user.id})
    except (RPCError, RPCTransportError):
        await cb.message.edit_text(
            "⚠️ Совет временно недоступен. Попробуй позже.",
            reply_markup=insights_menu()
        )
        return await cb.answer()

    insight = res.get("insight") or "Совет пока недоступен."
    text = header("AI‑совет", "tip") + "\n\n" + insight
    await cb.message.edit_text(text, reply_markup=insights_menu())
    await cb.answer()
