# handlers/insights.py
from aiogram import Router, types, F

from rpc import rpc, RPCError, RPCTransportError
from keyboards.keyboards import insights_menu
from ui.formatting import header, money_line, SEPARATOR
from utils.ui import clean_text
from i18n import t

router = Router()


@router.callback_query(F.data == "menu_insights")
async def menu_insights(cb: types.CallbackQuery, lang: str | None = None):
    text = (
        header(t("insights.menu.title", lang), "insights")
        + "\n\n"
        + t("insights.menu.body", lang)
    )
    await cb.message.edit_text(text, reply_markup=insights_menu(lang))
    await cb.answer()


@router.callback_query(F.data == "insights_week")
async def insights_week(cb: types.CallbackQuery, lang: str | None = None):
    await cb.answer(t("insights.week.loading", lang))
    try:
        res = await rpc("ai.transaction.analysis", {
            "tg_user_id": cb.from_user.id,
            "days": 7,
        })
    except (RPCError, RPCTransportError):
        await cb.message.edit_text(
            t("insights.week.error", lang),
            reply_markup=insights_menu(lang)
        )
        return await cb.answer()

    summary = clean_text(res.get("summary") or t("insights.week.empty", lang), 600)
    recommendation = clean_text(res.get("recommendation") or "", 300)

    text = (
        header(t("insights.week.title", lang), "insights")
        + "\n\n"
        + summary
    )
    if recommendation:
        text += "\n\n" + header(t("insights.week.recommendation_title", lang), "tip") + "\n" + recommendation

    await cb.message.edit_text(text, reply_markup=insights_menu(lang))
    await cb.answer()


@router.callback_query(F.data == "insights_trend")
async def insights_trend(cb: types.CallbackQuery, lang: str | None = None):
    await cb.answer(t("insights.trend.loading", lang))
    try:
        res = await rpc("ai.transaction.analysis", {
            "tg_user_id": cb.from_user.id,
            "days": 30,
        })
    except (RPCError, RPCTransportError):
        await cb.message.edit_text(
            t("insights.trend.error", lang),
            reply_markup=insights_menu(lang)
        )
        return await cb.answer()

    summary = clean_text(res.get("summary") or t("insights.trend.empty", lang), 600)
    recommendation = clean_text(res.get("recommendation") or "", 300)

    text = (
        header(t("insights.trend.title", lang), "insights")
        + "\n\n"
        + summary
    )
    if recommendation:
        text += "\n\n" + header(t("insights.week.recommendation_title", lang), "tip") + "\n" + recommendation

    await cb.message.edit_text(text, reply_markup=insights_menu(lang))
    await cb.answer()


@router.callback_query(F.data == "insights_savings")
async def insights_savings(cb: types.CallbackQuery, lang: str | None = None):
    try:
        res = await rpc("goal.list", {"tg_user_id": cb.from_user.id})
    except (RPCError, RPCTransportError):
        await cb.message.edit_text(
            t("insights.savings.error", lang),
            reply_markup=insights_menu(lang)
        )
        return await cb.answer()

    goals = res.get("goals", [])
    if not goals:
        await cb.message.edit_text(
            header(t("insights.savings.title", lang), "goal")
            + "\n\n"
            + t("insights.savings.empty", lang),
            reply_markup=insights_menu(lang)
        )
        return await cb.answer()

    total_saved = sum(float(g.get("amount_saved") or 0) for g in goals)
    total_target = sum(float(g.get("amount_total") or 0) for g in goals)
    percent = int((total_saved / total_target) * 100) if total_target else 0

    lines = [
        money_line(t("label.saved", lang), total_saved, "income"),
        money_line(t("label.goal", lang), total_target, "goal"),
        SEPARATOR,
        f"📈 {t('label.progress', lang)}: <b>{percent}%</b>",
    ]

    text = header(t("insights.savings.title", lang), "goal") + "\n\n" + "\n".join(lines)
    await cb.message.edit_text(text, reply_markup=insights_menu(lang))
    await cb.answer()


@router.callback_query(F.data == "insights_tip")
async def insights_tip(cb: types.CallbackQuery, lang: str | None = None):
    await cb.answer(t("insights.tip.loading", lang))
    try:
        res = await rpc("ai.insight.daily", {"tg_user_id": cb.from_user.id})
    except (RPCError, RPCTransportError):
        await cb.message.edit_text(
            t("insights.tip.error", lang),
            reply_markup=insights_menu(lang)
        )
        return await cb.answer()

    insight = res.get("insight") or t("insights.tip.empty", lang)
    text = header(t("insights.tip.title", lang), "tip") + "\n\n" + insight
    await cb.message.edit_text(text, reply_markup=insights_menu(lang))
    await cb.answer()
