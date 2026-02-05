from aiogram.utils.keyboard import InlineKeyboardBuilder


EXPENSE_CATEGORIES = [
    ("🍔 Еда", "cat_food"),
    ("🚌 Транспорт", "cat_transport"),
    ("🛒 Супермаркет", "cat_market"),
    ("📦 Покупки", "cat_shopping"),
    ("💳 Подписки", "cat_subscriptions"),
    ("🎉 Развлечения", "cat_fun"),
]


def expense_category_keyboard():
    kb = InlineKeyboardBuilder()
    for text, code in EXPENSE_CATEGORIES:
        kb.button(text=text, callback_data=code)
    kb.button(text="⬅️ Назад", callback_data="add_expense_back")
    kb.button(text="❌ Отменить", callback_data="menu_cancel")
    kb.adjust(2)
    return kb.as_markup()
