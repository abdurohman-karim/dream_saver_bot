# handlers/start.py
from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command

from rpc import rpc, RPCError, RPCTransportError, telegram_status
from ui.menus import get_main_menu, get_user_flags
from handlers.onboarding import start_onboarding
from handlers.registration import send_registration_prompt
from storage.registration_store import store

router = Router()


@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    tg_id = message.from_user.id

    try:
        await rpc("user.register", {
            "tg_user_id": tg_id,
            "name": message.from_user.full_name
        })
    except (RPCError, RPCTransportError):
        # юзера всё равно пустим в меню, но предупредим
        await message.answer(
            "⚠️ Сервис сейчас недоступен. Меню откроется, но некоторые действия могут не работать."
        )

    await state.clear()

    try:
        is_registered = await telegram_status(tg_id)
    except RPCTransportError:
        is_registered = store.is_registered(tg_id)

    if not is_registered:
        return await send_registration_prompt(message)

    store.set_registered(tg_id, True)

    flags = await get_user_flags(tg_id)
    if flags.get("is_new_user"):
        return await start_onboarding(message, state)

    text = (
        "Добро пожаловать обратно.\n"
        "Готов помочь держать финансы под контролем."
    )

    await message.answer(text, reply_markup=await get_main_menu(tg_id))
