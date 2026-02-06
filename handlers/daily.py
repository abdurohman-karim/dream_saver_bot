# handlers/daily.py
from aiogram import Router, types, F
from datetime import date

from rpc import rpc, RPCError, RPCTransportError
from keyboards.today_menu import today_menu
from utils.ui import format_amount, format_date, format_datetime, clean_text
from ui.formatting import header, money_line, SEPARATOR
from i18n import t
from utils.categories import localize_category

router = Router()


@router.callback_query(F.data == "menu_today")
async def show_today_transactions(cb: types.CallbackQuery, lang: str | None = None):
    today = date.today().isoformat()

    try:
        stats = await rpc("transaction.getDaily", {
            "tg_user_id": cb.from_user.id,
            "date": today,
        })
    except RPCTransportError:
        await cb.message.edit_text(
            t("daily.error.service_unavailable", lang),
            reply_markup=today_menu(lang)
        )
        return await cb.answer()
    except RPCError:
        await cb.message.edit_text(
            t("daily.error.failed", lang),
            reply_markup=today_menu(lang)
        )
        return await cb.answer()

    income = float(stats.get("income", 0))
    expense = float(stats.get("expense", 0))
    items = stats.get("items", [])

    if not items:
        text = (
            header(t("daily.title", lang), "insights")
            + "\n\n"
            + f"{t('daily.date_label', lang)}: <b>{format_date(stats.get('date'))}</b>\n"
            + t("daily.empty", lang)
        )
        await cb.message.edit_text(text, reply_markup=today_menu(lang))
        return await cb.answer()

    balance = income - expense
    text = (
        header(t("daily.title", lang), "insights")
        + "\n\n"
        + f"{t('daily.date_label', lang)}: <b>{format_date(stats.get('date'))}</b>\n"
        + money_line(t("label.income", lang), income, "income", sign="+") + "\n"
        + money_line(t("label.expense", lang), expense, "expense", sign="-") + "\n"
        + SEPARATOR + "\n"
        + money_line(t("label.balance", lang), balance, "progress") + "\n\n"
        + t("daily.operations", lang) + "\n"
    )

    for item in items:
        amount = float(item["amount"])
        sign = "➕" if amount > 0 else "➖"
        raw_cat = item.get("category") or t("daily.no_category", lang)
        cat = localize_category(raw_cat, lang) or raw_cat
        desc = clean_text(item.get("description") or "", 60)
        dt = format_datetime(item.get("datetime") or "")
        amount_text = format_amount(abs(amount))
        line = f"{sign} <b>{amount_text}</b> — {cat}"
        if dt:
            line += f" · {dt}"
        if desc:
            line += f" · {desc}"
        text += line + "\n"

    await cb.message.edit_text(
        text,
        reply_markup=today_menu(lang)
    )
    await cb.answer()
