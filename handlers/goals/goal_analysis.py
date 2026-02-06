from aiogram import Router, types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder

from rpc import rpc, RPCError, RPCTransportError
from keyboards.keyboards import back_button
from i18n import t

router = Router()


def back_to_goal_keyboard(goal_id: int, lang: str | None = None):
    kb = InlineKeyboardBuilder()
    kb.button(text=t("common.back", lang), callback_data=f"goal_manage_{goal_id}")
    kb.adjust(1)
    return kb.as_markup()


@router.callback_query(F.data.startswith("analyze_goal_"))
async def analyze_goal(cb: types.CallbackQuery, lang: str | None = None):
    goal_id = int(cb.data.split("_")[-1])
    user_id = cb.from_user.id

    await cb.answer(t("goals.analysis.loading", lang))

    try:
        ai = await rpc("ai.goal.analysis", {
            "tg_user_id": user_id,
            "goal_id": goal_id
        })
    except RPCTransportError:
        await cb.message.edit_text(
            t("goals.analysis.error.service_unavailable", lang),
            reply_markup=back_button(lang)
        )
        return
    except RPCError:
        await cb.message.edit_text(
            t("goals.analysis.error.failed", lang),
            reply_markup=back_button(lang)
        )
        return

    summary = ai.get("summary", t("goals.analysis.no_data", lang))
    recommendation = ai.get("recommendation", t("goals.analysis.no_recommendations", lang))
    numbers = ai.get("numbers", {}) or {}
    score = numbers.get("score") or numbers.get("progress_percent")

    if score is not None and score <= 1:
        score_value = round(score * 100)
    elif score is not None:
        score_value = round(score)
    else:
        score_value = None

    score_text = t("goals.analysis.score", lang, score=score_value) if score_value is not None else ""

    text = (
        f"{t('goals.analysis.title', lang)}\n\n"
        f"{t('goals.analysis.summary_title', lang)}\n{summary}\n\n"
        f"{t('goals.analysis.recommendation_title', lang)}\n{recommendation}\n\n"
        f"{score_text}"
    )

    await cb.message.edit_text(text, reply_markup=back_to_goal_keyboard(goal_id, lang))
