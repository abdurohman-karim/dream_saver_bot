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
async def insights_savings(cb: types.CallbackQuery, lang: str | None = None, currency: dict | None = None):
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

    grouped: dict[str, dict] = {}
    for goal in goals:
        goal_currency = goal.get("currency") or currency
        code = str((goal_currency or {}).get("code") or "UZS")
        bucket = grouped.setdefault(code, {
            "currency": goal_currency,
            "saved": 0.0,
            "target": 0.0,
        })
        bucket["saved"] += float(goal.get("amount_saved") or 0)
        bucket["target"] += float(goal.get("amount_total") or 0)

    lines = []
    for bucket in grouped.values():
        saved = bucket["saved"]
        target = bucket["target"]
        percent = int((saved / target) * 100) if target else 0
        lines.extend([
            money_line(t("label.saved", lang), saved, "income", currency=bucket["currency"]),
            money_line(t("label.goal", lang), target, "goal", currency=bucket["currency"]),
            f"📈 {t('label.progress', lang)}: <b>{percent}%</b>",
            SEPARATOR,
        ])

    if lines and lines[-1] == SEPARATOR:
        lines.pop()

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
