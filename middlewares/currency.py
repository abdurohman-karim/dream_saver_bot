from aiogram import BaseMiddleware

from rpc import telegram_status, RPCTransportError
from storage.currency_store import store


class CurrencyMiddleware(BaseMiddleware):
    def __init__(self):
        self.store = store

    async def __call__(self, handler, event, data):
        user = getattr(event, "from_user", None)
        if not user:
            return await handler(event, data)

        currency = self.store.get(user.id)
        if currency is None:
            try:
                status = await telegram_status(user.id)
                currency = status.get("currency")
                if currency:
                    self.store.set(user.id, currency)
            except RPCTransportError:
                currency = None

        data["currency"] = currency
        return await handler(event, data)
