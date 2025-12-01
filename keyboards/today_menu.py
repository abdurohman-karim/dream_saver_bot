# keyboards/today_menu.py
from aiogram.utils.keyboard import InlineKeyboardBuilder

def today_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Добавить трату", callback_data="menu_add_transaction")
    kb.button(text="💵 Добавить доход", callback_data="menu_add_income")
    kb.button(text="⬅️ Назад", callback_data="menu_back")
    kb.adjust(1)
    return kb.as_markup()
