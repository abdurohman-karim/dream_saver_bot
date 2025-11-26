# handlers/analysis.py
from aiogram import Router, types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder

from rpc import rpc, RPCError, RPCTransportError
from keyboards.keyboards import back_button

router = Router()


@router.callback_query(F.data == "menu_goal_analysis")
async def choose_goal_to_analyze(cb: types.CallbackQuery):
    user_id = cb.from_user.id

    try:
        res = await rpc("goal.list", {"tg_user_id": user_id})
    except (RPCError, RPCTransportError):
        await cb.message.edit_text(
            "⚠️ Не удалось получить список целей.",
            reply_markup=back_button()
        )
        return await cb.answer()

    goals = res.get("goals") or []
    if not goals:
        await cb.message.edit_text(
            "⚠️ У тебя пока нет целей.",
            reply_markup=back_button()
        )
        return await cb.answer()

    kb = InlineKeyboardBuilder()
    for g in goals:
        kb.button(
            text=f"{g['title']}",
            callback_data=f"analyze_goal_{g['id']}"
        )
    kb.button(text="⬅️ Назад", callback_data="menu_back")
    kb.adjust(1)

    await cb.message.edit_text(
        "Выбери цель, которую нужно проанализировать 👇",
        reply_markup=kb.as_markup()
    )
    await cb.answer()


@router.callback_query(F.data.startswith("analyze_goal_"))
async def analyze_goal(cb: types.CallbackQuery):
    goal_id = int(cb.data.split("_")[-1])
    user_id = cb.from_user.id

    await cb.answer("⌛ Анализирую цель, подожди пару секунд...")

    try:
        ai = await rpc("ai.goal.analysis", {
            "tg_user_id": user_id,
            "goal_id": goal_id
        })
    except RPCTransportError:
        await cb.message.edit_text(
            "⚠️ Сервер недоступен. Попробуй позже.",
            reply_markup=back_button()
        )
        return
    except RPCError as e:
        await cb.message.edit_text(
            f"⚠️ Ошибка анализа:\n{e}",
            reply_markup=back_button()
        )
        return

    summary = ai.get("summary", "Нет данных")
    recommendation = ai.get("recommendation", "Нет рекомендаций")
    numbers = ai.get("numbers", {}) or {}
    score = numbers.get("score") or numbers.get("progress_percent")

    if score is not None and score <= 1:
        # если бекенд возвращает 0–1
        score_value = round(score * 100)
    elif score is not None:
        score_value = round(score)
    else:
        score_value = None

    score_text = f"⭐ Оценка прогресса: <b>{score_value}%</b>" if score_value is not None else ""

    text = (
        "🧠 <b>Анализ цели</b>\n\n"
        f"📄 <b>Резюме:</b>\n{summary}\n\n"
        f"💡 <b>Рекомендация:</b>\n{recommendation}\n\n"
        f"{score_text}"
    )

    await cb.message.edit_text(
        text,
        reply_markup=back_button()
    )
