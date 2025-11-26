from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import date, timedelta


def deadline_keyboard():
    kb = InlineKeyboardBuilder()

    today = date.today()
    plus_30 = today + timedelta(days=30)
    plus_90 = today + timedelta(days=90)

    kb.button(text=f"📅 Сегодня ({today})", callback_data=f"deadline_{today}")
    kb.button(text=f"📅 +30 дней ({plus_30})", callback_data=f"deadline_{plus_30}")
    kb.button(text=f"📅 +90 дней ({plus_90})", callback_data=f"deadline_{plus_90}")
    kb.button(text="⏳ Без дедлайна", callback_data="deadline_none")
    kb.button(text="❌ Отменить", callback_data="menu_cancel")

    kb.adjust(1)
    return kb.as_markup()
