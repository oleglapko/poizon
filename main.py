import logging
import math
import aiohttp
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import F
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

TOKEN = "7655184269:AAG__JJ6raD0fC-YTVO9S0zbusXMO3itnro"
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = "https://poizon-5ih7.onrender.com/webhook"

bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())

logging.basicConfig(level=logging.INFO)

CATEGORY_WEIGHTS = {
    "Обувь": 1.5,
    "Футболка / Худи / Штаны": 0.7,
}

class OrderStates(StatesGroup):
    waiting_for_price = State()
    waiting_for_city = State()

@dp.message(F.text == "/start")
async def start(message: Message, state: FSMContext):
    await state.clear()
    builder = InlineKeyboardBuilder()
    builder.button(text="👟 Обувь", callback_data="Обувь")
    builder.button(text="👕 Футболка / Худи / Штаны", callback_data="Футболка / Худи / Штаны")
    builder.button(text="❓ Другое", callback_data="Другое")
    builder.button(text="🆕 Новый расчёт", callback_data="new")
    builder.adjust(2, 1, 1)
    await message.answer("Выбери категорию товара:", reply_markup=builder.as_markup())

@dp.callback_query(F.data == "new")
async def new_calc(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await start(callback.message, state)

@dp.callback_query(F.data.in_(CATEGORY_WEIGHTS.keys()))
async def category_chosen(callback: CallbackQuery, state: FSMContext):
    await state.update_data(category=callback.data)
    await callback.message.answer("Введи цену товара в юанях:")
    await state.set_state(OrderStates.waiting_for_price)

@dp.callback_query(F.data == "Другое")
async def other_category(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Для расчёта другой категории напиши @oleglobok 👤")

@dp.message(OrderStates.waiting_for_price)
async def price_entered(message: Message, state: FSMContext):
    try:
        price_yuan = float(message.text.replace(",", "."))
        await state.update_data(price_yuan=price_yuan)
        await message.answer("Введи город доставки (получатель, СДЭК):")
        await state.set_state(OrderStates.waiting_for_city)
    except ValueError:
        await message.answer("Пожалуйста, введи корректное число.")

@dp.message(OrderStates.waiting_for_city)
async def city_entered(message: Message, state: FSMContext):
    user_data = await state.get_data()
    category = user_data["category"]
    weight = CATEGORY_WEIGHTS[category]
    price_yuan = user_data["price_yuan"]
    city_to = message.text

    # 1. Курс
    cbr_url = "https://www.cbr-xml-daily.ru/daily_json.js"
    async with aiohttp.ClientSession() as session:
        async with session.get(cbr_url) as resp:
            data = await resp.json()
            yuan_rate = data["Valute"]["CNY"]["Value"]
            final_rate = yuan_rate * 1.11

    # 2. Цена с комиссией
    price_rub = math.ceil(price_yuan * final_rate)
    delivery_from_china = math.ceil(weight * 789)
    total_before_sdek = price_rub + delivery_from_china

    # 3. СДЭК
    sdek_payload = {
        "version": "1.0",
        "senderCityId": 44,  # Москва
        "receiverCityName": city_to,
        "tariffId": 137,
        "goods": [{"weight": weight}]
    }

    sdek_url = "https://api.cdek.ru/calculator/tariff"
    async with aiohttp.ClientSession() as session:
        async with session.post(sdek_url, json=sdek_payload) as resp:
            sdek_result = await resp.json()
            sdek_price = sdek_result.get("result", {}).get("price", 0)

    total_price = total_before_sdek + sdek_price

    # Ответ
    text = (
        f"💴 Курс юаня: {final_rate:.2f}₽\n"
        f"🎁 Цена с комиссией: {price_rub}₽\n"
        f"📦 Доставка из Китая: {delivery_from_china}₽\n"
        f"📦 Доставка СДЭК: {sdek_price}₽\n"
        f"💰 Итого: {total_price}₽"
    )

    await message.answer(text)
    await message.answer("🔁 Нажми /start для нового расчета")
    await state.clear()

# Webhook setup
async def on_startup(dispatcher: Dispatcher):
    await bot.set_webhook(WEBHOOK_URL)

async def on_shutdown(dispatcher: Dispatcher):
    await bot.delete_webhook()

app = web.Application()
dp.startup.register(on_startup)
dp.shutdown.register(on_shutdown)
SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
setup_application(app, dp, bot=bot)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=8000)


