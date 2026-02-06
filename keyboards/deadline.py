# keyboards/deadline.py


from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import date, timedelta
from i18n import t


def deadline_keyboard(lang: str | None = None):
    kb = InlineKeyboardBuilder()

    today = date.today()
    plus_30 = today + timedelta(days=30)
    plus_90 = today + timedelta(days=90)

    kb.button(text=t("deadline.today", lang, date=today), callback_data=f"deadline_{today}")
    kb.button(text=t("deadline.plus_days", lang, days=30, date=plus_30), callback_data=f"deadline_{plus_30}")
    kb.button(text=t("deadline.plus_days", lang, days=90, date=plus_90), callback_data=f"deadline_{plus_90}")

    # 🔥 Новая кнопка — ввод вручную
    kb.button(text=t("deadline.manual", lang), callback_data="deadline_manual")

    kb.button(text=t("deadline.none", lang), callback_data="deadline_none")
    kb.button(text=t("common.cancel", lang), callback_data="menu_cancel")

    kb.adjust(1)
    return kb.as_markup()
