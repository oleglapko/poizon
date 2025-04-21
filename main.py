import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.utils import executor
from keep_alive import keep_alive

TOKEN = "7655184269:AAFnOEwzH3NhGYvOOjgfJNMuvkjFyrpbmhU"
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(commands=["start"])
async def start_cmd(message: Message):
    await message.answer("Привет! Я бот для расчёта стоимости доставки с Poizon.")

if __name__ == "__main__":
    keep_alive()
    executor.start_polling(dp, skip_updates=True)