from aiogram.utils.keyboard import InlineKeyboardBuilder


# =======================
#   Главное меню
# =======================
def main_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="🎯 Создать цель", callback_data="menu_newgoal")
    kb.button(text="🤖 Smart Save", callback_data="menu_smart")
    kb.button(text="💡 Совет дня", callback_data="menu_daily")
    kb.button(text="📊 Прогресс", callback_data="menu_progress")
    kb.button(text="🧠 Анализ цели", callback_data="menu_goal_analysis")
    kb.adjust(1)
    return kb.as_markup()


# =======================
#   Кнопка «Назад»
# =======================
def back_button():
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Назад", callback_data="menu_back")
    return kb.as_markup()

# =======================
#   Кнопка «Отменить»
# =======================
def cancel_button():
    kb = InlineKeyboardBuilder()
    kb.button(text="❌ Отменить", callback_data="menu_cancel")
    return kb.as_markup()
