import logging
import math
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.enums.parse_mode import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
import asyncio

TOKEN = "7655184269:AAG__JJ6raD0fC-YTVO9S0zbusXMO3itnro"
WEBHOOK_HOST = "https://poizon-5ih7.onrender.com"
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())

class OrderState(StatesGroup):
    choosing_category = State()
    entering_price = State()
    entering_city = State()

categories = {
    "Обувь": {"weight": 1.5, "dimensions": (36, 26, 15)},
    "Футболка/Кофта/Штаны": {"weight": 0.6, "dimensions": (23, 17, 13)},
    "Другое": {}
}

def get_cny_rate():
    response = requests.get("https://www.cbr-xml-daily.ru/daily_json.js")
    data = response.json()
    rate = data["Valute"]["CNY"]["Value"]
    return rate * 1.11

def calc_total(price_cny, weight_kg):
    rate = get_cny_rate()
    price_rub = price_cny * rate
    commission = price_rub * 0.10
    shipping_china = weight_kg * 789
    return math.ceil(price_rub + commission + shipping_china)

def calc_cdek(to_city, weight, dimensions):
    url = "https://api.cdek.dev/v2/calculator/tariff"
    headers = {"Content-Type": "application/json"}
    payload = {
        "type": 1,
        "currency": 1,
        "lang": "rus",
        "from_location": {"city": "Москва"},
        "to_location": {"city": to_city},
        "packages": [{
            "weight": int(weight * 1000),
            "length": dimensions[0],
            "width": dimensions[1],
            "height": dimensions[2]
        }]
    }
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        tariffs = response.json().get("tariff_codes", [])
        if tariffs:
            return tariffs[0]["delivery_sum"]
    return None

@dp.message(commands=["start"])
async def start(message: types.Message, state: FSMContext):
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="Обувь")],
        [KeyboardButton(text="Футболка/Кофта/Штаны")],
        [KeyboardButton(text="Другое")]
    ], resize_keyboard=True)
    await message.answer("Привет! Что вы хотите заказать?", reply_markup=kb)
    await state.set_state(OrderState.choosing_category)

@dp.message(OrderState.choosing_category)
async def choose_category(message: types.Message, state: FSMContext):
    cat = message.text
    if cat not in categories:
        await message.answer("Пожалуйста, выбери категорию из списка.")
        return
    if cat == "Другое":
        await message.answer("Напишите нашему менеджеру: @oleglobok")
        await state.clear()
    else:
        await state.update_data(category=cat)
        await message.answer("Введите цену товара в юанях:")
        await state.set_state(OrderState.entering_price)

@dp.message(OrderState.entering_price)
async def enter_price(message: types.Message, state: FSMContext):
    try:
        price_cny = float(message.text)
    except ValueError:
        await message.answer("Пожалуйста, введите число.")
        return
    await state.update_data(price_cny=price_cny)
    await message.answer("Введите город для доставки СДЭКом:")
    await state.set_state(OrderState.entering_city)

@dp.message(OrderState.entering_city)
async def enter_city(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    category = user_data["category"]
    price_cny = user_data["price_cny"]
    weight = categories[category]["weight"]
    dimensions = categories[category]["dimensions"]
    total = calc_total(price_cny, weight)
    cdek_price = calc_cdek(message.text, weight, dimensions)
    if cdek_price is None:
        cdek_str = "Не удалось рассчитать доставку СДЭК."
    else:
        cdek_str = f"Доставка по России СДЭК: {cdek_price} ₽"
    await message.answer(
        f"<b>Итоговая стоимость:</b> {total} ₽
{cdek_str}"
    )
    await state.clear()

async def on_startup(bot: Bot) -> None:
    await bot.set_webhook(WEBHOOK_URL)

async def on_shutdown(bot: Bot) -> None:
    await bot.delete_webhook()

def create_app():
    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    app.on_startup.append(lambda app: on_startup(bot))
    app.on_shutdown.append(lambda app: on_shutdown(bot))
    return app

if __name__ == "__main__":
    app = create_app()
    web.run_app(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))