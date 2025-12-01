from aiogram.utils.keyboard import InlineKeyboardBuilder

def goals_list_keyboard(goals):
    kb = InlineKeyboardBuilder()
    for g in goals:
        primary = "⭐" if g.get("is_primary") else ""
        pr = g.get("priority", 1)
        icon = g.get("icon", "🎯")

        kb.button(
            text=f"{icon} {g['title']} {primary} (P{pr})",
            callback_data=f"goal_manage_{g['id']}"
        )
        kb.button(text="➕ Создать новый цель", callback_data="menu_newgoal")

    kb.button(text="⬅️ Назад", callback_data="menu_back")
    kb.adjust(1)
    return kb.as_markup()


def goal_manage_keyboard(goal_id, is_primary, status):
    kb = InlineKeyboardBuilder()

    if status == "active":
        if not is_primary:
            kb.button(
                text="⭐ Сделать основной",
                callback_data=f"goal_set_primary_{goal_id}"
            )

        kb.button(
            text="📥 Пополнить цель",
            callback_data=f"goal_deposit_{goal_id}"
        )

        kb.adjust(1)

        kb.button(
            text="🔼 Приоритет +",
            callback_data=f"goal_priority_up_{goal_id}"
        )
        kb.button(
            text="🔽 Приоритет –",
            callback_data=f"goal_priority_down_{goal_id}"
        )
        kb.adjust(2)

        kb.button(
            text="🛑 Завершить цель",
            callback_data=f"goal_close_completed_{goal_id}"
        )
    else:
        kb.button(
            text="♻️ Сделать активной",
            callback_data=f"goal_reopen_{goal_id}"
        )

    kb.button(text="🧠 Анализ цели", callback_data=f"goal_ai_{goal_id}")
    kb.button(text="⬅️ Назад", callback_data="menu_goals")
    kb.adjust(1)

    return kb.as_markup()
