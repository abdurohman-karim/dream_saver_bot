# handlers/start.py
from aiogram import Router, types
from aiogram.filters import Command

from keyboards.keyboards import main_menu
from rpc import rpc, RPCError, RPCTransportError

router = Router()


@router.message(Command("start"))
async def cmd_start(message: types.Message):
    tg_id = message.from_user.id

    try:
        await rpc("user.register", {
            "tg_user_id": tg_id,
            "name": message.from_user.full_name
        })
    except (RPCError, RPCTransportError):
        # юзера всё равно пустим в меню, но предупредим
        await message.answer(
            "⚠️ Не удалось связаться с сервером, но ты всё равно можешь открыть меню.\n"
            "Попробуй команды чуть позже."
        )

    text = (
        "Привет! 😊\n"
        "Я — твой Finora AI бот.\n"
        "Помогу тебе копить деньги, анализировать расходы и достигать целей.\n\n"
        "Выбери действие 👇"
    )

    await message.answer(text, reply_markup=main_menu())
