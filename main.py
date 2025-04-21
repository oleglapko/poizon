import os
import math
import aiohttp
import requests
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler
from aiohttp import web
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv("TOKEN")
WEBHOOK_HOST = os.getenv("WEBHOOK_URL")  # Например, https://your-app.onrender.com
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Константы
DP_EXPRESS_RATE = 789
COMMISSION = 0.10
YUAN_MARKUP_PERCENT = 0.11

keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="👟 Обувь"), KeyboardButton(text="👕 Футболка / Худи / Штаны")],
        [KeyboardButton(text="❓ Другое")],
        [KeyboardButton(text="🔁 Новый расчёт")]
    ],
    resize_keyboard=True
)

user_weights = {}
user_cities = {}

def get_cb_yuan_rate():
    try:
        response = requests.get("https://www.cbr-xml-daily.ru/daily_json.js")
        data = response.json()
        return data["Valute"]["CNY"]["Value"]
    except:
        return 12.0

async def get_cdek_delivery_price(city_to: str, weight: float) -> float:
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://api.cdek.dev/v1/public/tariff"
            params = {
                "type": 1,
                "from_location": "Москва",
                "to_location": city_to,
                "weight": weight,
            }
            async with session.get(url, params=params) as resp:
                data = await resp.json()
                return float(data.get("price", 600))
    except:
        return 600

@dp.message(F.text == "/start")
@dp.message(F.text == "🔁 Новый расчёт")
async def cmd_start(message: Message):
    user_weights.pop(message.chat.id, None)
    user_cities.pop(message.chat.id, None)
    await message.answer("Выберите тип товара:", reply_markup=keyboard)

@dp.message(F.text.startswith("👟"))
async def handle_shoes(message: Message):
    user_weights[message.chat.id] = 1.5
    await message.answer("Введите цену товара в юанях:")

@dp.message(F.text.lower().contains("футболка") | F.text.lower().contains("худи") | F.text.lower().contains("штаны"))
async def handle_clothes(message: Message):
    user_weights[message.chat.id] = 0.7
    await message.answer("Введите цену товара в юанях:")

@dp.message(F.text.lower().contains("другое"))
async def handle_other(message: Message):
    await message.answer("📩 По доставке других товаров свяжитесь с менеджером: @oleglobok")

@dp.message(F.text)
async def process_price_or_city(message: Message):
    chat_id = message.chat.id

    # Ожидаем цену
    if chat_id in user_weights and chat_id not in user_cities:
        try:
            yuan_price = float(message.text.replace(",", "."))
            user_cities[chat_id] = {"yuan_price": yuan_price}
            await message.answer("Введите ваш город для расчета доставки СДЭК:")
        except ValueError:
            await message.answer("Введите корректную цену в юанях (например, 199.9).")

    # Ожидаем город
    elif chat_id in user_cities and "city_to" not in user_cities[chat_id]:
        user_cities[chat_id]["city_to"] = message.text

        yuan_price = user_cities[chat_id]["yuan_price"]
        city_to = user_cities[chat_id]["city_to"]
        weight = user_weights[chat_id]

        rub_yuan_rate = get_cb_yuan_rate() * (1 + YUAN_MARKUP_PERCENT)
        price_rub = yuan_price * rub_yuan_rate
        price_with_commission = price_rub * (1 + COMMISSION)
        dp_delivery = weight * DP_EXPRESS_RATE
        sdek_delivery = await get_cdek_delivery_price(city_to, weight)

        total = price_with_commission + dp_delivery + sdek_delivery

        await message.answer(
            f"💸 Курс юаня: {rub_yuan_rate:.2f}₽\n"
            f"🛍️ Цена с комиссией: {math.ceil(price_with_commission)}₽\n"
            f"📦 Доставка из Китая: {math.ceil(dp_delivery)}₽\n"
            f"📦 Доставка СДЭК: {math.ceil(sdek_delivery)}₽\n"
            f"💰 Итог: {math.ceil(total)}₽"
        )

        await message.answer("🔁 Нажми /start для нового расчета", reply_markup=keyboard)

# Веб-сервер
async def on_startup(app):
    await bot.set_webhook(WEBHOOK_URL)

async def on_shutdown(app):
    await bot.delete_webhook()

app = web.Application()
app.on_startup.append(on_startup)
app.on_shutdown.append(on_shutdown)

# Подключаем Telegram webhook-хендлер
SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)

# Ручка для установки вручную
async def manual_set_webhook(request):
    await bot.set_webhook(WEBHOOK_URL)
    return web.Response(text="Webhook установлен!")

app.router.add_get("/set_webhook", manual_set_webhook)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=8080)

