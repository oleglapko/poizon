import logging
import math
import os
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.types import Message
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.webhook import WebhookRunner, WebhookRequestHandler
from aiohttp import web
import aiohttp
from dotenv import load_dotenv

# Загрузка .env (если используешь)
load_dotenv()

TOKEN = os.getenv("BOT_TOKEN", "7655184269:AAG__JJ6raD0fC-YTVO9S0zbusXMO3itnro")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://poizon-5ih7.onrender.com/webhook")

bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

# Курс и параметры
YUAN_BASE = 11  # Наценка к курсу ЦБ в %
DELIVERY_RATE = 789  # руб/кг
COMMISSION = 0.1

# Клавиатура
keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="👟 Обувь"), KeyboardButton(text="👕 Футболка / Худи / Штаны")],
        [KeyboardButton(text="❓ Другое")],
        [KeyboardButton(text="🔁 Новый расчёт")]
    ],
    resize_keyboard=True,
)

@dp.message(F.text == "/start")
async def start(message: Message):
    await message.answer("Выбери категорию товара:", reply_markup=keyboard)

@dp.message(F.text.in_({"👟 Обувь", "👕 Футболка / Худи / Штаны"}))
async def handle_category(message: Message):
    category = message.text
    weight = 1.5 if "Обувь" in category else 0.7
    await message.answer("Укажи цену в юанях:")

    @dp.message()
    async def get_price(message: Message):
        try:
            price_yuan = float(message.text)
            rate = round(12.31, 2)
            rate_with_fee = round(rate * (1 + YUAN_BASE / 100), 2)
            price_rub = math.ceil(price_yuan * rate_with_fee * (1 + COMMISSION))
            delivery_china = math.ceil(weight * DELIVERY_RATE)

            await message.answer("Введи город получателя для расчёта СДЭК:")

            @dp.message()
            async def get_city(message: Message):
                city = message.text
                try:
                    # Расчёт СДЭК
                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            "https://api.cdek.dev/v1/calculate",
                            json={
                                "from_location": {"city": "Москва"},
                                "to_location": {"city": city},
                                "packages": [{"weight": weight * 1000, "length": 30, "width": 20, "height": 10}],
                            },
                        ) as response:
                            cdek_data = await response.json()
                            cdek_price = int(cdek_data["total_price"])
                except Exception as e:
                    cdek_price = 600  # fallback

                total = price_rub + delivery_china + cdek_price

                await message.answer(
                    f"💱 Курс юаня: {rate_with_fee}₽\n"
                    f"🎁 Цена с комиссией: {price_rub}₽\n"
                    f"📦 Доставка из Китая: {delivery_china}₽\n"
                    f"📮 Доставка СДЭК: {cdek_price}₽\n"
                    f"💰 Итого: {total}₽\n\n"
                    "🔁 Нажми /start для нового расчёта"
                )
        except ValueError:
            await message.answer("Введи число (цену в юанях).")

@dp.message(F.text == "❓ Другое")
async def handle_other(message: Message):
    await message.answer("Напиши @oleglobok — он поможет рассчитать доставку под конкретный товар.")

@dp.message(F.text == "🔁 Новый расчёт")
async def handle_reset(message: Message):
    await start(message)

# === Webhook ===
async def on_startup(app):
    await bot.set_webhook(WEBHOOK_URL)

async def on_shutdown(app):
    await bot.delete_webhook()

app = web.Application()
app.router.add_post("/webhook", WebhookRequestHandler(dp))
app.on_startup.append(on_startup)
app.on_shutdown.append(on_shutdown)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    web.run_app(app, port=10000)


