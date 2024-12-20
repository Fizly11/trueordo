import asyncio

from handlers import router
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart, Command
from config import TOKEN

bot = Bot(token=TOKEN)
dp = Dispatcher()

async def main():
    try:
        dp.include_router(router)
        print('Starting bot polling...')
        await dp.start_polling(bot)
    finally:
        print('Bot polling stopped')

if __name__ == "__main__":
    asyncio.run(main())