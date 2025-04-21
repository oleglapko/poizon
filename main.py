import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.enums import ParseMode
import asyncio

TOKEN = '7655184269:AAFnOEwzH3NhGYvOOjgfJNMuvkjFyrpbmhU'

bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())

# Кнопки
keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Рассчитать доставку")]
    ],
    resize_keyboard=True
)

# Машина состояний
class DeliveryState(StatesGroup):
    choosing_category = State()
    entering_city = State()

# Обработчики
@dp.message(F.text == "/start")
async def cmd_start(message: Message, state: FSMContext):
    await message.answer("Привет! Я бот для расчёта доставки с Poizon. Нажми кнопку ниже👇", reply_markup=keyboard)
    await state.clear()

@dp.message(F.text == "Рассчитать доставку")
async def choose_category(message: Message, state: FSMContext):
    await message.answer("Выбери категорию:\n👟 Обувь\n👕 Одежда\n📦 Другое")
    await state.set_state(DeliveryState.choosing_category)

@dp.message(DeliveryState.choosing_category)
async def handle_category(message: Message, state: FSMContext):
    category = message.text.lower()

    if "обувь" in category:
        weight = 1.5
    elif "одежда" in category:
        weight = 0.7
    elif "другое" in category:
        await message.answer("Напиши менеджеру @oleglobok для уточнения доставки.")
        await state.clear()
        return
    else:
        await message.answer("Пожалуйста, выбери одну из категорий: 👟 Обувь, 👕 Одежда, 📦 Другое")
        return

    await state.update_data(weight=weight)
    await message.answer("Введи город получения (для расчета СДЭК):")
    await state.set_state(DeliveryState.entering_city)

@dp.message(DeliveryState.entering_city)
async def handle_city(message: Message, state: FSMContext):
    city = message.text
    data = await state.get_data()
    weight = data.get("weight", 1.0)

    # Пример расчета стоимости
    delivery_price = weight * 789
    yuan_rate = 13.5 * 1.11
    commission = 0.1
    total_price = int((delivery_price * yuan_rate) * (1 + commission)) + 1

    await message.answer(f"📦 Примерная стоимость доставки: <b>{total_price} ₽</b>")
    await state.clear()

async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

