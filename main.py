
import os
import math
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor
from dotenv import load_dotenv

load_dotenv()
bot = Bot(token=os.getenv("TOKEN"))
dp = Dispatcher(bot)

# Константы
DP_EXPRESS_RATE = 789  # ₽/кг
COMMISSION = 0.10
YUAN_MARKUP_PERCENT = 0.11

# Клавиатура
keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton("👟 Обувь"), KeyboardButton("👕 Футболка / Худи / Штаны")],
        [KeyboardButton("❓ Другое")],
        [KeyboardButton("🔁 Новый расчёт")]
    ],
    resize_keyboard=True
)

# Временное хранилище веса
user_weights = {}

# Получение курса ЦБ РФ
def get_cb_yuan_rate():
    try:
        response = requests.get("https://www.cbr-xml-daily.ru/daily_json.js")
        data = response.json()
        return data["Valute"]["CNY"]["Value"]
    except:
        return 12.0  # запасной курс

@dp.message_handler(commands=["start"])
@dp.message_handler(lambda message: message.text == "🔁 Новый расчёт")
async def cmd_start(message: types.Message):
    user_weights.pop(message.chat.id, None)
    await message.answer("Выберите тип товара:", reply_markup=keyboard)

@dp.message_handler(lambda message: message.text.startswith("👟"))
async def handle_shoes(message: types.Message):
    user_weights[message.chat.id] = 1.5
    await message.answer("Введите цену товара в юанях:")

@dp.message_handler(lambda message: "футболка" in message.text.lower() or "худи" in message.text.lower() or "штаны" in message.text.lower())
async def handle_clothes(message: types.Message):
    user_weights[message.chat.id] = 0.7
    await message.answer("Введите цену товара в юанях:")

@dp.message_handler(lambda message: "другое" in message.text.lower())
async def handle_other(message: types.Message):
    await message.answer("📩 По доставке других товаров свяжитесь с менеджером: @oleglobok")

@dp.message_handler()
async def handle_price(message: types.Message):
    if message.chat.id not in user_weights:
        await message.answer("Сначала выберите тип товара. Нажмите /start")
        return

    try:
        yuan_price = float(message.text.replace(",", "."))
    except ValueError:
        await message.answer("Введите корректную цену в юанях (например, 199.9).")
        return

    weight = user_weights[message.chat.id]
    rub_yuan_rate = get_cb_yuan_rate() * (1 + YUAN_MARKUP_PERCENT)
    price_rub = yuan_price * rub_yuan_rate
    price_with_commission = price_rub * (1 + COMMISSION)
    delivery = weight * DP_EXPRESS_RATE
    total = price_with_commission + delivery

    await message.answer(
        f"💸 Курс юаня: {rub_yuan_rate:.2f}₽\n"
        f"🛍️ Цена с комиссией (10%): {math.ceil(price_with_commission)}₽\n"
        f"📦 Доставка: {math.ceil(delivery)}₽\n"
        f"💰 Итог: {math.ceil(total)}₽\n\n"
        f"🔁 Хочешь сделать новый расчёт? Нажми /start или кнопку ниже 👇",
        reply_markup=keyboard
    )

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
