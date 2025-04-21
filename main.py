from keep_alive import keep_alive
keep_alive()

import os
import math
import requests
from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor
from dotenv import load_dotenv

# Flask-сервер для Render
app = Flask(__name__)

@app.route("/ping")
def ping():
    return "pong", 200

def run_flask():
    app.run(host="0.0.0.0", port=8080)

Thread(target=run_flask).start()

# Загрузка токена
load_dotenv()
bot = Bot(token=os.getenv("TOKEN"))
dp = Dispatcher(bot)

# Константы
DP_EXPRESS_RATE = 789  # ₽/кг
COMMISSION = 0.10
YUAN_MARKUP_PERCENT = 0.11
SENDER_CITY = "Москва"

# Клавиатура
keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton("\U0001F45F Обувь"), KeyboardButton("\U0001F455 Футболка / Худи / Штаны")],
        [KeyboardButton("\u2753 Другое")],
        [KeyboardButton("\U0001F501 Новый расчёт")]
    ],
    resize_keyboard=True
)

# Временное хранилище веса и цены
user_data = {}

# Получение курса ЦБ РФ
def get_cb_yuan_rate():
    try:
        response = requests.get("https://www.cbr-xml-daily.ru/daily_json.js")
        data = response.json()
        return data["Valute"]["CNY"]["Value"]
    except:
        return 12.0  # запасной курс

# Расчёт доставки СДЭК через API
def get_sdek_price(receiver_city):
    try:
        response = requests.get(
            "https://api.cdek.dev/getTariff",
            params={
                "from": SENDER_CITY,
                "to": receiver_city,
                "weight": 1
            },
            timeout=5
        )
        data = response.json()
        return data.get("price", 0)
    except:
        return 0

@dp.message_handler(commands=["start"])
@dp.message_handler(lambda message: message.text == "\U0001F501 Новый расчёт")
async def cmd_start(message: types.Message):
    user_data.pop(message.chat.id, None)
    await message.answer("Выберите тип товара:", reply_markup=keyboard)

@dp.message_handler(lambda message: message.text.startswith("\U0001F45F"))
async def handle_shoes(message: types.Message):
    user_data[message.chat.id] = {"weight": 1.5}
    await message.answer("Введите цену товара в юанях:")

@dp.message_handler(lambda message: "футболка" in message.text.lower() or "худи" in message.text.lower() or "штаны" in message.text.lower())
async def handle_clothes(message: types.Message):
    user_data[message.chat.id] = {"weight": 0.7}
    await message.answer("Введите цену товара в юанях:")

@dp.message_handler(lambda message: "другое" in message.text.lower())
async def handle_other(message: types.Message):
    await message.answer("\U0001F4E9 По доставке других товаров свяжитесь с менеджером: @oleglobok")

@dp.message_handler()
async def handle_input(message: types.Message):
    user_id = message.chat.id

    if user_id not in user_data:
        await message.answer("Сначала выберите тип товара. Нажмите /start")
        return

    user_entry = user_data[user_id]

    if "price" not in user_entry:
        try:
            yuan_price = float(message.text.replace(",", "."))
            user_entry["price"] = yuan_price
            await message.answer("Введите город, куда будет отправлен товар:")
        except ValueError:
            await message.answer("Введите корректную цену в юанях (например, 199.9).")
    else:
        # Финальный расчёт
        receiver_city = message.text
        rub_yuan_rate = get_cb_yuan_rate() * (1 + YUAN_MARKUP_PERCENT)
        price_rub = user_entry["price"] * rub_yuan_rate
        price_with_commission = price_rub * (1 + COMMISSION)
        delivery_china = user_entry["weight"] * DP_EXPRESS_RATE
        sdek_delivery = get_sdek_price(receiver_city)
        total = price_with_commission + delivery_china + sdek_delivery

        await message.answer(
            f"\U0001F4B8 Курс юаня: {rub_yuan_rate:.2f}₽\n"
            f"\U0001F6CD️ Цена с комиссией (10%): {math.ceil(price_with_commission)}₽\n"
            f"\U0001F4E6 Доставка из Китая: {math.ceil(delivery_china)}₽\n"
            f"\U0001F69A Доставка СДЭК до {receiver_city}: {math.ceil(sdek_delivery)}₽\n"
            f"\n\U0001F4B0 Итог: {math.ceil(total)}₽\n\n"
            f"\U0001F501 Хочешь сделать новый расчёт? Нажми /start или кнопку ниже \U0001F447",
            reply_markup=keyboard
        )
        user_data.pop(user_id, None)

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
