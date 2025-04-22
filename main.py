import os
import math
import json
from aiohttp import web, ClientSession
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Update
from aiogram.utils.markdown import hbold
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DOMAIN = os.getenv("DOMAIN")  # Например: https://poizon-5ih7.onrender.com
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{DOMAIN}{WEBHOOK_PATH}"

bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())

# Получение курса юаня
async def get_cny_rate():
    async with ClientSession() as session:
        async with session.get("https://www.cbr-xml-daily.ru/daily_json.js") as resp:
            data = json.loads(await resp.text())
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

# Расчёт стоимости
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
    price_with_fee = math.ceil(price_rub * 1.1)  # комиссия 10%
    shipping_cost = math.ceil(weight * 789)
    total = price_with_fee + shipping_cost

    await message.answer(
        f"{hbold('Курс юаня:')} {cny_rate}₽\n"
        f"{hbold('Товар:')} {price_with_fee}₽ (с комиссией)\n"
        f"{hbold('Доставка из Китая:')} {shipping_cost}₽\n"
        f"{hbold('Итого:')} {total}₽"
    )
    await state.clear()

# Webhook-сервер (aiohttp)
async def on_startup(app):
    await bot.set_webhook(WEBHOOK_URL)
    print(f"✅ Webhook установлен: {WEBHOOK_URL}")

async def on_shutdown(app):
    await bot.delete_webhook()
    await bot.session.close()
    print("❌ Webhook удалён")

async def handle_webhook(request):
    try:
        data = await request.json()
        update = Update.model_validate(data)
        await dp.feed_update(bot, update)
    except Exception as e:
        print(f"Ошибка обработки webhook: {e}")
    return web.Response()

# Создание aiohttp-приложения
app = web.Application()
app.router.add_post(WEBHOOK_PATH, handle_webhook)
app.on_startup.append(on_startup)
app.on_shutdown.append(on_shutdown)

if __name__ == "__main__":
    web.run_app(app, port=10000)
