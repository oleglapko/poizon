import os
import math
import asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

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
    weight = 1.5 if category == "1" else 0.6

    # Расчёты
    cbr_rate = get_cbr_exchange_rate()
    rate = cbr_rate * 1.11
    item_price_rub = price_yuan * rate
    delivery_cost = weight * 789
    subtotal = item_price_rub + delivery_cost
    commission = subtotal * 0.10
    total_cost = math.ceil(subtotal + commission)

    await message.answer(
        f"<b>Расчёт стоимости:</b>\n"
        f"Стоимость товара: {math.ceil(item_price_rub)} ₽\n"
        f"Доставка из Китая ({weight} кг): {math.ceil(delivery_cost)} ₽\n"
        f"Комиссия (10%): {math.ceil(commission)} ₽\n\n"
        f"<b>Итого:</b> {total_cost} ₽"
    )
    await state.clear()

def get_cbr_exchange_rate():
    return 11.5  # Фиксированный курс ЦБ РФ, можно подключить API

# Основная функция запуска
async def main():
    print("Бот запущен на long polling!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

