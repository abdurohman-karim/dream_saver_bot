from aiogram import Router, types, F
from keyboards.keyboards import main_menu

router = Router()

@router.callback_query(F.data == "clear_chat")
async def clear_chat(cb: types.CallbackQuery):
    chat_id = cb.message.chat.id

    messages = [cb.message.message_id]

    for msg_id in range(cb.message.message_id - 50, cb.message.message_id + 1):
        try:
            await cb.bot.delete_message(chat_id, msg_id)
        except:
            pass

    # 2. Отправляем новое "главное окно"
    await cb.message.answer(
        "🗑 <b>Чат очищен!</b>\n\n"
        "Telegram не позволяет удалять сообщения пользователя,\n"
        "поэтому очищены только сообщения бота.",
        reply_markup=main_menu()
    )

    await cb.answer()
