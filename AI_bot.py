import asyncio
import os

from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from dotenv import find_dotenv, load_dotenv

from middleware.middleware import DataBaseSession

load_dotenv(find_dotenv())


from database.engine import create_db, session_maker, drop_db
from handlers.user_private import user_private_router
from ai_engine.general_engine import client
ai_bot = Bot(token=os.getenv('TOKEN'), default=DefaultBotProperties(parse_mode=ParseMode.HTML))
 
dp = Dispatcher()

dp.include_router(user_private_router)


# === STARTUP ===
async def on_startup(bot: Bot):
    print("🚀 Начало:создание БД...")
    await create_db()
    print("✅ БД работает")


async def on_shutdown():
    print("🧹 Завершение работы...")
    await client.close()               # Закрываем OpenAI-сессию
    await ai_bot.session.close()       # Закрываем aiohttp-сессию бота
    print("✅ Все сессии закрыты")

async def main():
    # регистрируем middleware
    dp.update.middleware(DataBaseSession(session_pool=session_maker))
    # регистрируем startup
    dp.startup.register(on_startup)
    try:
        await ai_bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(ai_bot)
    finally:
        await on_shutdown()

if __name__ == "__main__":
    asyncio.run(main())

