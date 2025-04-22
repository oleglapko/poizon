import math
import json
import os
from aiohttp import ClientSession
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from aiogram.types import CallbackQuery
from aiogram.utils.markdown import hbold
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram import types
from fastapi import FastAPI, Request
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiogram.client.bot import DefaultBotProperties
from aiogram.webhook.base import BaseWebhookServer
from aiogram.fsm.storage.memory import MemoryStorage

from dotenv import load_dotenv
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DOMAIN = os.getenv("DOMAIN")  # например: https://poizon-5ih7.onrender.com
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{DOMAIN}{WEBHOOK_PATH}"

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# Функция получения курса
async def get_cny_rate():
    async with ClientSession() as session:
        async with session.get("https://www.cbr-xml-daily.ru/daily_json.js") as resp:
            data = json.loads(await resp.text())  # фикс тут
            rate = data["Valute"]["CNY"]["Value"]
            return math.ceil(rate * 1.11)

# Старт
@dp.message(F.text == "/start")
async def cmd_start(message: Message, state: FSMContext):
    await message.answer(
        "Привет! Выбери категорию товара:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Обувь", callback_data="category_shoes")],
            [InlineKeyboardButton(text="Одежда", callback_data="category_clothes")],
            [InlineKeyboardButton(text="Другое", callback_data="category_other")],
        ])
    )

# Выбор категории
@dp.callback_query(F.data.startswith("category_"))
async def choose_category(callback: CallbackQuery, state: FSMContext):
    category = callback.data.split("_")[1]
    if category == "other":
        await callback.message.answer("Напиши @oleglobok для индивидуального расчёта.")
        return

    weight = {"shoes": 1.5, "clothes": 0.7}[category]
    await state.update_data(weight=weight)
    await callback.message.answer("Введи стоимость товара в юанях (¥):")

# Получение стоимости
@dp.message(F.text.regexp(r"^\d+(\.\d+)?$"))
async def calculate_total(message: Message, state: FSMContext):
    user_data = await state.get_data()
    if "weight" not in user_data:
        await message.answer("Сначала выбери категорию товара.")
        return

    price_yuan = float(message.text)
    cny_rate = await get_cny_rate()
    weight = user_data["weight"]

    price_rub = price_yuan * cny_rate
    price_with_fee = math.ceil(price_rub * 1.1)  # +10% комиссия
    shipping_cost = math.ceil(weight * 789)
    total = price_with_fee + shipping_cost

    await message.answer(
        f"{hbold('Курс юаня:')} {cny_rate}₽\n"
        f"{hbold('Товар:')} {price_with_fee}₽ (с комиссией)\n"
        f"{hbold('Доставка из Китая:')} {shipping_cost}₽\n"
        f"{hbold('Итого:')} {total}₽"
    )
    await state.clear()

# FastAPI-приложение для Render
app = FastAPI()
@app.on_event("startup")
async def on_startup():
    await bot.set_webhook(WEBHOOK_URL)

@app.on_event("shutdown")
async def on_shutdown():
    await bot.delete_webhook()

SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
