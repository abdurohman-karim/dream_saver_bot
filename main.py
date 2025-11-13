import asyncio
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from handlers.router import main_router
from aiogram.client.default import DefaultBotProperties


async def main():
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML")
    )
    dp = Dispatcher()
    dp.include_router(main_router)

    print("Bot started...")
    await bot.delete_webhook(drop_pending_updates=True)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
