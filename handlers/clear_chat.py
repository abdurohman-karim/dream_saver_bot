from aiogram import Router, types, F
from ui.menus import get_main_menu
from i18n import t
import logging

router = Router()

@router.callback_query(F.data == "clear_chat")
async def clear_chat(cb: types.CallbackQuery, lang: str | None = None):
    chat_id = cb.message.chat.id

    for msg_id in range(cb.message.message_id - 50, cb.message.message_id + 1):
        try:
            await cb.bot.delete_message(chat_id, msg_id)
        except Exception:
            logging.debug("Clear chat skipped message_id=%s", msg_id)

    # 2. Отправляем новое "главное окно"
    await cb.message.answer(
        f"{t('clear_chat.title', lang)}\n\n{t('clear_chat.body', lang)}",
        reply_markup=await get_main_menu(cb.from_user.id, lang)
    )

    await cb.answer()
