# handlers/registration.py
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

import logging

from rpc import telegram_register, RegistrationError, RPCTransportError
from storage.registration_store import store
from ui.menus import get_main_menu, get_user_flags
from handlers.onboarding import start_onboarding

router = Router()


def contact_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📲 Отправить номер", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


async def send_registration_prompt(message: types.Message):
    await message.answer(
        "🔒 <b>Подтверждение номера</b>\n\n"
        "Это защищает ваш аккаунт и дает доступ к финансовым функциям.\n"
        "Мы примем только ваш собственный контакт.",
        reply_markup=contact_keyboard()
    )


@router.message(Command("register"))
async def register_start(message: types.Message, state: FSMContext):
    await state.clear()
    await send_registration_prompt(message)


@router.message(lambda m: m.contact is not None)
async def register_contact(message: types.Message, state: FSMContext):
    contact = message.contact

    if not contact.user_id or contact.user_id != message.from_user.id:
        return await message.answer(
            "⚠️ Пожалуйста, отправьте свой номер через кнопку ниже.",
            reply_markup=contact_keyboard()
        )

    try:
        await telegram_register(
            tg_user_id=message.from_user.id,
            phone=contact.phone_number,
            name=message.from_user.full_name,
        )
    except RegistrationError as e:
        if e.code == "phone_in_use":
            text = "Этот номер уже используется другим аккаунтом."
        elif e.code == "invalid_phone":
            text = "Номер выглядит некорректно. Попробуйте отправить контакт еще раз."
        else:
            text = "Не удалось завершить регистрацию. Попробуйте позже."

        return await message.answer(
            f"⚠️ {text}",
            reply_markup=contact_keyboard()
        )
    except RPCTransportError:
        logging.exception("Registration transport error")
        return await message.answer(
            "⚠️ Не удалось подтвердить номер. Повторите попытку.",
            reply_markup=contact_keyboard()
        )

    store.set_registered(message.from_user.id, True)
    await state.clear()

    await message.answer(
        "✅ <b>Номер подтвержден</b>\n\n"
        "Спасибо. Это повышает безопасность вашего аккаунта.",
        reply_markup=ReplyKeyboardRemove()
    )

    flags = await get_user_flags(message.from_user.id)
    if flags.get("is_new_user"):
        return await start_onboarding(message, state)

    await message.answer(
        "Готов продолжить. Что сделаем дальше?",
        reply_markup=await get_main_menu(message.from_user.id)
    )
