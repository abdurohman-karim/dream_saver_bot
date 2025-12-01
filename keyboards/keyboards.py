from aiogram.utils.keyboard import InlineKeyboardBuilder

def main_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="🎯 Мои цели", callback_data="menu_goals")
    kb.button(text="🤖 Smart Save", callback_data="menu_smart")
    kb.button(text="💡 Совет дня", callback_data="menu_daily")
    kb.button(text="📊 Прогресс", callback_data="menu_progress")
    kb.button(text="🧠 Анализ цели", callback_data="menu_goal_analysis")
    kb.button(text="📅 Мой бюджет", callback_data="menu_budget")
    kb.button(text="💸 Сегодняшние траты", callback_data="menu_today")
    kb.button(text="➕ Добавить трату", callback_data="menu_add_transaction")
    kb.button(text="💵 Добавить доход", callback_data="menu_add_income")
    kb.adjust(1)
    return kb.as_markup()

def back_button():
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Назад", callback_data="menu_back")
    return kb.as_markup()

def cancel_button():
    kb = InlineKeyboardBuilder()
    kb.button(text="❌ Отменить", callback_data="menu_cancel")
    return kb.as_markup()
