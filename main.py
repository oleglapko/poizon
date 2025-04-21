import logging
import asyncio
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message
import aiohttp

# Токен
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения")

# Настройки
YUAN_CB_RATE_URL = "https://www.cbr-xml-daily.ru/daily_json.js"
DELIVERY_RATE = 789
COMMISSION = 0.1
YUAN_MARKUP = 1.11

# FSM
class Order(StatesGroup):
    choosing_category = State()
    entering_price = State()

# Инициализация
logging.basicConfig(level=logging.INFO)
storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)

# Клавиатура
category_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Обувь")],
        [KeyboardButton(text="Футболка/Кофта/Штаны")],
        [KeyboardButton(text="Другое")],
    ],
    resize_keyboard=True
)

@dp.message(F.text == "/start")
async def start(message: Message, state: FSMContext):
    await message.answer(
        "Привет! Я бот для расчёта стоимости доставки товаров с Poizon.\n"
        "Выбери категорию товара:",
        reply_markup=category_keyboard
    )
    await state.set_state(Order.choosing_category)

@dp.message(F.text.in_(["Обувь", "Футболка/Кофта/Штаны", "Другое"]))
async def choose_category(message: Message, state: FSMContext):
    category = message.text
    if category == "Другое":
        await message.answer("По товарам другой категории напиши менеджеру: @oleglobok")
        await state.clear()
        return

    await state.update_data(category=category)
    await message.answer("Введи стоимость товара в юанях (без доставки)")
    await state.set_state(Order.entering_price)

@dp.message(Order.entering_price, F.text.regexp(r"^\d+(\.\d+)?$"))
async def calculate_total(message: Message, state: FSMContext):
    data = await state.get_data()
    price_yuan = float(message.text)

    # Курс юаня
    async with aiohttp.ClientSession() as session:
        async with session.get(YUAN_CB_RATE_URL) as resp:
            cb_data = await resp.json()
            cb_yuan = cb_data['Valute']['CNY']['Value']
            rate = cb_yuan * YUAN_MARKUP

    category = data['category']
    weight = 1.5 if category == "Обувь" else 0.6

    rub_price = price_yuan * rate
    commission = rub_price * COMMISSION
    delivery = weight * DELIVERY_RATE
    total = rub_price + commission + delivery

    await message.answer(
        f"Стоимость товара: {rub_price:.0f} ₽\n"
        f"Комиссия (10%): {commission:.0f} ₽\n"
        f"Доставка из Китая в Москву: {delivery:.0f} ₽\n"
        f"\nПримерная стоимость: {total:.0f} ₽\n"
        f"\n⚠️ К этой сумме будет добавлена доставка СДЭК по России. "
        f"Точная сумма будет известна после оформления заказа."
    )
    await state.clear()

@dp.message()
async def fallback(message: Message):
    await message.answer("Пожалуйста, выбери категорию с кнопок или введи корректное число.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

