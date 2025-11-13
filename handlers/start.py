from aiogram import Router, types
from aiogram.filters import Command
from keyboards.keyboards import main_menu
from rpc import rpc

router = Router()


@router.message(Command("start"))
async def cmd_start(message: types.Message):
    tg_id = message.from_user.id

    # Регистрируем пользователя
    await rpc("user.register", {
        "tg_user_id": tg_id,
        "name": message.from_user.full_name
    })

    text = (
        "Привет! 😊\n"
        "Я — твой AI Dream-Saver бот.\n"
        "Помогу тебе копить деньги, анализировать расходы и достигать целей.\n\n"
        "Выбери действие 👇"
    )

    await message.answer(text, reply_markup=main_menu())
