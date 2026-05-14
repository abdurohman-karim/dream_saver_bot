# handlers/progress.py
from aiogram import Router, types, F

from rpc import rpc, RPCError, RPCTransportError
from keyboards.keyboards import back_button
from utils.ui import format_amount
from ui.formatting import header, SEPARATOR
from i18n import t

router = Router()


@router.callback_query(F.data == "menu_progress")
async def menu_progress(cb: types.CallbackQuery, lang: str | None = None, currency: dict | None = None):
    user_id = cb.from_user.id

    try:
        res = await rpc("goal.list", {"tg_user_id": user_id})
    except (RPCError, RPCTransportError):
        await cb.message.edit_text(
            t("progress.error", lang),
            reply_markup=back_button(lang)
        )
        return await cb.answer()

    goals = res.get("goals", [])
    if not goals:
        await cb.message.edit_text(
            t("progress.empty", lang),
            reply_markup=back_button(lang)
        )
        return await cb.answer()

    text = header(t("progress.title", lang), "insights") + "\n\n"

    for g in goals:
        total = float(g.get("amount_total", 0) or 0)
        saved = float(g.get("amount_saved", 0) or 0)
        percent = int(saved / total * 100) if total else 0

        text += (
            f"🎯 <b>{g['title']}</b>\n"
            f"💰 {t('label.saved', lang)}: <b>{format_amount(saved, currency=g.get('currency') or currency)}</b> / {format_amount(total, currency=g.get('currency') or currency)}\n"
            f"📈 {t('label.progress', lang)}: <b>{percent}%</b>\n"
            f"{SEPARATOR}\n"
        )

    await cb.message.edit_text(
        text,
        reply_markup=back_button(lang)
    )
    await cb.answer()
