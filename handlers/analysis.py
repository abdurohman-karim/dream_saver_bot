from aiogram import Router, types
from rpc import rpc
from keyboards.keyboards import back_button
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()


# 1️⃣ Пользователь нажал "Анализ цели"
@router.callback_query(lambda c: c.data == "menu_goal_analysis")
async def choose_goal_to_analyze(cb: types.CallbackQuery):
    user_id = cb.from_user.id

    result = await rpc("goal.list", {"tg_user_id": user_id})

    res = result.get("result")
    if not res or not res.get("goals"):
        await cb.message.edit_text(
            "⚠️ У тебя пока нет целей.",
            reply_markup=back_button()
        )
        return await cb.answer()

    goals = res["goals"]

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


# 2️⃣ Пользователь нажал на конкретную цель
@router.callback_query(lambda c: c.data.startswith("analyze_goal_"))
async def analyze_goal(cb: types.CallbackQuery):
    goal_id = int(cb.data.split("_")[-1])
    user_id = cb.from_user.id

    await cb.answer("⌛ Анализирую цель, подожди пару секунд...")

    result = await rpc("ai.goal.analysis", {
        "tg_user_id": user_id,
        "goal_id": goal_id
    })

    if "error" in result:
        await cb.message.edit_text(
            f"⚠️ Ошибка анализа:\n{result['error']['message']}",
            reply_markup=back_button()
        )
        return

    ai = result.get("result", {})

    # Это то, что возвращает GoalService::goalAnalysis()
    summary = ai.get("summary", "Нет данных")
    recommendation = ai.get("recommendation", "Нет рекомендаций")
    score = ai.get("numbers", {}).get("score", None)

    score_text = f"⭐ Оценка прогресса: <b>{round(score * 100)}%</b>" if score else ""

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
