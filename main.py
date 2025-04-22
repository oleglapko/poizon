import math
import asyncio
import os
import requests
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from flask import Flask
from threading import Thread

# Загрузка .env
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

# Настройка бота и диспетчера
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# Состояния
class Form(StatesGroup):
    waiting_for_category = State()
    waiting_for_price = State()

# Получение курса юаня с сайта ЦБ РФ
def get_cbr_exchange_rate():
    try:
        response = requests.get("https://www.cbr.ru/scripts/XML_daily.asp")
        response.encoding = "windows-1251"
        tree = ET.fromstring(response.text)

        for valute in tree.findall("Valute"):
            if valute.find("CharCode").text == "CNY":
                value = valute.find("Value").text.replace(",", ".")
                nominal = int(valute.find("Nominal").text)
                return float(value) / nominal
    except Exception as e:
        print(f"Ошибка при получении курса ЦБ: {e}")
        return 11.5  # fallback-курс

# Хэндлер старт
@dp.message(F.text == "/start")
async def start_handler(message: Message, state: FSMContext):
    await message.answer(
        "Выберите категорию товара:\n"
        "1. Обувь 👟\n"
        "2. Футболка/штаны/худи 👕\n"
        "3. Другое ❓\n\n"
        "Введите номер категории (1, 2 или 3):"
    )
    await state.set_state(Form.waiting_for_category)

# Хэндлер категории
@dp.message(Form.waiting_for_category)
async def category_handler(message: Message, state: FSMContext):
    category = message.text.strip()
    if category not in ["1", "2", "3"]:
        await message.answer("Пожалуйста, введите 1, 2 или 3.")
        return

    if category == "3":
        await message.answer("Свяжитесь с менеджером: @oleglobok")
        await state.clear()
        return

    await state.update_data(category=category)
    await message.answer("Введите цену товара в юанях ¥ (только число):")
    await state.set_state(Form.waiting_for_price)

# Хэндлер цены
@dp.message(Form.waiting_for_price)
async def price_handler(message: Message, state: FSMContext):
    try:
        price_yuan = float(message.text.strip())
    except ValueError:
        await message.answer("Введите число, например: 289")
        return

    data = await state.get_data()
    category = data["category"]
    weight =
