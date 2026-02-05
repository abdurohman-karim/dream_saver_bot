from aiogram.utils.keyboard import InlineKeyboardBuilder

def main_menu(flags: dict | None = None):
    flags = flags or {}
    has_goals = flags.get("has_goals", True)
    has_transactions = flags.get("has_transactions", True)
    has_budget = flags.get("has_budget", True)
    smart_save_available = flags.get("smart_save_available", True)

    kb = InlineKeyboardBuilder()
    if not has_goals:
        kb.button(text="🎯 Создать первую цель", callback_data="menu_newgoal")
    if not has_transactions:
        kb.button(text="💰 Добавить первый доход", callback_data="menu_add_income")
    if not has_budget:
        kb.button(text="📅 Настроить бюджет", callback_data="menu_budget")

    kb.button(text="➕ Расход", callback_data="menu_add_transaction")
    kb.button(text="➕ Доход", callback_data="menu_add_income")
    kb.button(text="📅 Сегодня", callback_data="menu_today")
    kb.button(text="📅 Бюджет", callback_data="menu_budget")

    if has_goals:
        kb.button(text="🎯 Цели", callback_data="menu_goals")
        kb.button(text="📊 Прогресс", callback_data="menu_progress")
    else:
        kb.button(text="🎯 Цели", callback_data="menu_goals")

    kb.button(text="📊 Insights", callback_data="menu_insights")

    if smart_save_available:
        kb.button(text="🤖 Smart Save", callback_data="menu_smart")

    kb.button(text="🗑 Очистить чат", callback_data="clear_chat")
    kb.adjust(1, 2, 2, 2, 2, 1)
    return kb.as_markup()

def back_button():
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Назад", callback_data="menu_back")
    return kb.as_markup()

def cancel_button():
    kb = InlineKeyboardBuilder()
    kb.button(text="❌ Отменить", callback_data="menu_cancel")
    return kb.as_markup()


def insights_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="📆 Обзор недели", callback_data="insights_week")
    kb.button(text="📉 Тренд расходов", callback_data="insights_trend")
    kb.button(text="🎯 Прогресс накоплений", callback_data="insights_savings")
    kb.button(text="💡 AI‑совет", callback_data="insights_tip")
    kb.button(text="⬅️ Назад", callback_data="menu_back")
    kb.adjust(1)
    return kb.as_markup()
