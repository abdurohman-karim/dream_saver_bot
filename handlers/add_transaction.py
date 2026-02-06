from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import date, datetime

from states.transactions import TransactionStates
from keyboards.keyboards import cancel_button, back_button
from keyboards.expense_categories import expense_category_keyboard
from utils.categories import EXPENSE_CATEGORY_KEYS, expense_category_label, expense_category_backend_value
from rpc import rpc
from ui.menus import get_main_menu
from utils.ui import parse_amount, format_amount, format_date, clean_text
from i18n import t

router = Router()


async def safe_delete(msg: types.Message):
    try:
        await msg.delete()
    except:
        pass


@router.callback_query(F.data == "menu_add_transaction")
async def add_start(cb: types.CallbackQuery, state: FSMContext, lang: str | None = None):
    await state.set_state(TransactionStates.waiting_for_amount)

    msg = await cb.message.edit_text(
        f"{t('expense.new.title', lang)}\n\n{t('expense.new.body', lang)}",
        reply_markup=back_button(lang)
    )

    await state.update_data(bot_message_id=msg.message_id)
    await cb.answer()


@router.message(TransactionStates.waiting_for_amount)
async def set_amount(message: types.Message, state: FSMContext, lang: str | None = None):
    await safe_delete(message)

    amount = parse_amount(message.text)
    if amount is None:
        return await message.answer(t("expense.amount_invalid", lang))

    await state.update_data(amount=int(amount))
    await state.set_state(TransactionStates.waiting_for_category)

    data = await state.get_data()
    bot_msg_id = data["bot_message_id"]

    # редактируем основное окно
    await message.bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=bot_msg_id,
        text=t("expense.category.title", lang),
        reply_markup=expense_category_keyboard(lang)
    )


@router.callback_query(F.data.startswith("cat_"))
async def set_category(cb: types.CallbackQuery, state: FSMContext, lang: str | None = None):
    key = cb.data.replace("cat_", "")
    if key not in EXPENSE_CATEGORY_KEYS:
        return await cb.answer(t("expense.category.not_found", lang))

    await state.update_data(
        category_key=key,
        category_label=expense_category_label(key, lang),
        category_value=expense_category_backend_value(key),
    )
    await state.set_state(TransactionStates.waiting_for_description)

    data = await state.get_data()
    bot_msg_id = data["bot_message_id"]

    await cb.message.bot.edit_message_text(
        chat_id=cb.message.chat.id,
        message_id=bot_msg_id,
        text=t("expense.description.title", lang),
        reply_markup=description_keyboard(lang)
    )
    await cb.answer()


def description_keyboard(lang: str | None = None):
    kb = InlineKeyboardBuilder()
    kb.button(text=t("common.skip", lang), callback_data="desc_skip")
    kb.button(text=t("common.cancel", lang), callback_data="menu_cancel")
    kb.adjust(1)
    return kb.as_markup()


@router.callback_query(F.data == "desc_skip")
async def skip_description(cb: types.CallbackQuery, state: FSMContext, lang: str | None = None):
    await state.update_data(description=None)
    await state.set_state(TransactionStates.waiting_for_date)

    data = await state.get_data()
    bot_msg_id = data["bot_message_id"]

    await cb.message.bot.edit_message_text(
        chat_id=cb.message.chat.id,
        message_id=bot_msg_id,
        text=t("expense.date.title", lang),
        reply_markup=date_keyboard(lang)
    )
    await cb.answer()


@router.message(TransactionStates.waiting_for_description)
async def set_desc(message: types.Message, state: FSMContext, lang: str | None = None):
    await safe_delete(message)

    await state.update_data(description=message.text.strip())
    await state.set_state(TransactionStates.waiting_for_date)

    data = await state.get_data()
    bot_msg_id = data["bot_message_id"]

    await message.bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=bot_msg_id,
        text=t("expense.date.title", lang),
        reply_markup=date_keyboard(lang)
    )


def date_keyboard(lang: str | None = None):
    kb = InlineKeyboardBuilder()
    kb.button(text=t("deadline.today", lang, date=date.today()), callback_data="date_today")
    kb.button(text=t("deadline.manual", lang), callback_data="date_manual")
    kb.button(text=t("common.cancel", lang), callback_data="menu_cancel")
    kb.adjust(1)
    return kb.as_markup()


@router.callback_query(F.data == "date_today")
async def choose_today(cb: types.CallbackQuery, state: FSMContext, lang: str | None = None):
    await prepare_confirmation(cb, state, date.today().isoformat(), lang)


@router.callback_query(F.data == "date_manual")
async def date_manual(cb: types.CallbackQuery, state: FSMContext, lang: str | None = None):
    await state.set_state(TransactionStates.waiting_for_date_manual)

    data = await state.get_data()
    bot_msg_id = data["bot_message_id"]

    await cb.message.bot.edit_message_text(
        chat_id=cb.message.chat.id,
        message_id=bot_msg_id,
        text=t("expense.date.manual_prompt", lang),
        reply_markup=cancel_button(lang)
    )
    await cb.answer()


@router.message(TransactionStates.waiting_for_date_manual)
async def save_manual(message: types.Message, state: FSMContext, lang: str | None = None):
    await safe_delete(message)
    date_value = message.text.strip()
    try:
        datetime.strptime(date_value, "%Y-%m-%d")
    except ValueError:
        return await message.answer(t("expense.date.invalid", lang))
    await prepare_confirmation(message, state, date_value, lang)


def confirm_keyboard(lang: str | None = None):
    kb = InlineKeyboardBuilder()
    kb.button(text=t("common.save", lang), callback_data="expense_confirm")
    kb.button(text=t("common.cancel", lang), callback_data="menu_cancel")
    kb.adjust(1)
    return kb.as_markup()


async def prepare_confirmation(obj, state: FSMContext, date_value: str, lang: str | None = None):
    data = await state.get_data()
    await state.update_data(date=date_value)
    await state.set_state(TransactionStates.waiting_for_confirm)

    amount_text = format_amount(data["amount"])
    category = data.get("category_label") or data.get("category_value")
    description = clean_text(data.get("description") or "—", 120)
    date_text = format_date(date_value)

    text = (
        f"{t('expense.confirm.title', lang)}\n\n"
        f"💸 {t('label.amount', lang)}: <b>{amount_text}</b>\n"
        f"🏷 {t('label.category', lang)}: <b>{category}</b>\n"
        f"📝 {t('label.description', lang)}: <b>{description}</b>\n"
        f"📅 {t('label.date', lang)}: <b>{date_text}</b>\n\n"
        f"{t('expense.confirm.question', lang)}"
    )

    bot_msg_id = data["bot_message_id"]
    chat_id = obj.message.chat.id if isinstance(obj, types.CallbackQuery) else obj.chat.id
    await obj.bot.edit_message_text(
        chat_id=chat_id,
        message_id=bot_msg_id,
        text=text,
        reply_markup=confirm_keyboard(lang)
    )


@router.callback_query(TransactionStates.waiting_for_confirm, F.data == "expense_confirm")
async def finish_expense(cb: types.CallbackQuery, state: FSMContext, lang: str | None = None):
    data = await state.get_data()
    date_value = data.get("date")

    payload = {
        "tg_user_id": cb.from_user.id,
        "items": [{
            "amount": -abs(data["amount"]),
            "category": data.get("category_value"),
            "description": data.get("description"),
            "datetime": date_value,
        }],
        "source": "manual",
    }

    try:
        await rpc("transaction.import", payload)
    except Exception:
        await state.clear()
        return await cb.message.edit_text(
            t("expense.save.error", lang),
            reply_markup=await get_main_menu(cb.from_user.id, lang)
        )

    bot_msg_id = data["bot_message_id"]
    await state.clear()
    await cb.bot.edit_message_text(
        chat_id=cb.message.chat.id,
        message_id=bot_msg_id,
        text=(
            f"{t('expense.save.success', lang, amount=format_amount(data['amount']), category=data.get('category_label') or data.get('category_value'), date=format_date(date_value))}"
            f"\n{t('expense.save.success.footer', lang)}"
        ),
        reply_markup=await get_main_menu(cb.from_user.id, lang)
    )
    await cb.answer()


@router.callback_query(F.data == "add_expense_back")
async def back_to_amount(cb: types.CallbackQuery, state: FSMContext, lang: str | None = None):
    await state.set_state(TransactionStates.waiting_for_amount)

    data = await state.get_data()
    bot_msg_id = data.get("bot_message_id")

    if bot_msg_id:
        await cb.message.bot.edit_message_text(
            chat_id=cb.message.chat.id,
            message_id=bot_msg_id,
            text=f"{t('expense.new.title', lang)}\n\n{t('expense.new.body', lang)}",
            reply_markup=back_button(lang)
        )
    await cb.answer()
