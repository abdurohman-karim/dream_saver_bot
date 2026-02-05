from aiogram import BaseMiddleware, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from rpc import telegram_status, RPCTransportError
from storage.registration_store import store


class RegistrationMiddleware(BaseMiddleware):
    def __init__(self):
        self.store = store

    async def __call__(self, handler, event, data):
        user = getattr(event, "from_user", None)
        if not user:
            return await handler(event, data)

        if self._is_allowed_event(event):
            return await handler(event, data)

        if self.store.is_registered(user.id):
            return await handler(event, data)

        try:
            if await telegram_status(user.id):
                self.store.set_registered(user.id, True)
                return await handler(event, data)
        except RPCTransportError:
            pass

        await self._prompt_registration(event)
        return None

    def _is_allowed_event(self, event) -> bool:
        if isinstance(event, types.Message):
            if event.text and event.text.startswith(("/start", "/register")):
                return True
            if event.contact:
                return True
        if isinstance(event, types.CallbackQuery):
            if event.data and event.data.startswith("onb_"):
                return True
        return False

    async def _prompt_registration(self, event):
        text = (
            "🔒 <b>Подтверждение номера</b>\n\n"
            "Чтобы защитить ваш аккаунт и финансы, подтвердите номер телефона.\n"
            "Мы принимаем только ваш собственный контакт."
        )

        keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="📲 Отправить номер", request_contact=True)]],
            resize_keyboard=True,
            one_time_keyboard=True,
        )

        if isinstance(event, types.CallbackQuery):
            await event.message.answer(text, reply_markup=keyboard)
            await event.answer()
        elif isinstance(event, types.Message):
            await event.answer(text, reply_markup=keyboard)
