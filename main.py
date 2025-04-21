import telebot
import requests
import json
from datetime import datetime
from utils import calculate_yuan_rate, calculate_delivery_sdek  # Предполагаем, что эти функции будут в utils.py

# Замени 'YOUR_BOT_TOKEN' на токен своего бота
BOT_TOKEN = '7655184269:AAFnOEwzH3NhGYvOOjgfJNMuvkjFyrpbmhU'
bot = telebot.TeleBot(BOT_TOKEN)

YUAN_TO_RUB_CB_URL = "https://www.cbr.ru/currency_base/daily/?UniDbQuery.Posted=True&UniDbQuery.To=2024-04-22" # Замени на актуальную дату или сделай динамическим
CHINA_TO_MOSCOW_DELIVERY_RATE = 789  # руб/кг
COMMISSION_RATE = 0.10  # 10%

item_data = {
    "обувь": {"dimensions": [36, 26, 15], "weight": 1.5},
    "футболка\\кофта\\штаны": {"dimensions": [23, 17, 13], "weight": 0.6},
}

@bot.message_handler(commands=['start'])
def greet(message):
    bot.reply_to(message, "Привет! Я бот для расчета стоимости товаров с Poizon. Какой товар вы планируете заказать?")
    bot.send_message(message.chat.id, "Выберите категорию: обувь, футболка\\кофта\\штаны или другое.")
    bot.register_next_step_handler(message, ask_category)

def ask_category(message):
    if message.text.lower() in item_data:
        category = message.text.lower()
        bot.send_message(message.chat.id, f"Вы выбрали категорию '{category}'. Пожалуйста, укажите стоимость товара в юанях.")
        bot.register_next_step_handler(message, calculate_cost, category)
    elif message.text.lower() == "другое":
        bot.send_message(message.chat.id, "Пожалуйста, свяжитесь с менеджером @oleglobok для расчета стоимости нестандартных товаров.")
    else:
        bot.reply_to(message, "Некорректная категория. Пожалуйста, выберите из предложенных вариантов.")
        bot.register_next_step_handler(message, ask_category)

def calculate_cost(message, category):
    try:
        yuan_price = float(message.text)
        if yuan_price <= 0:
            bot.reply_to(message, "Стоимость товара должна быть положительным числом. Пожалуйста, введите корректную стоимость.")
            bot.register_next_step_handler(message, calculate_cost, category)
            return

        yuan_rate = calculate_yuan_rate()
        rub_price_without_commission = yuan_price * yuan_rate
        commission = rub_price_without_commission * COMMISSION_RATE
        rub_price_with_commission = rub_price_without_commission + commission

        weight = item_data[category]["weight"]
        delivery_china_to_moscow = weight * CHINA_TO_MOSCOW_DELIVERY_RATE

        total_without_sdek = rub_price_with_commission + delivery_china_to_moscow

        bot.send_message(
            message.chat.id,
            f"Предварительный расчет:\n"
            f"Курс юаня (ЦБ + 11%): {yuan_rate:.2f} ₽\n"
            f"Стоимость товара без комиссии: {rub_price_without_commission:.2f} ₽\n"
            f"Комиссия 10%: {commission:.2f} ₽\n"
            f"Стоимость товара с комиссией: {rub_price_with_commission:.2f} ₽\n"
            f"Доставка из Китая до Москвы ({weight} кг): {delivery_china_to_moscow:.2f} ₽\n"
            f"Итого без учета доставки по РФ: {total_without_sdek:.2f} ₽\n\n"
            f"Теперь укажите город доставки по России для расчета стоимости СДЭК."
        )
        bot.register_next_step_handler(message, get_sdek_delivery_cost, total_without_sdek)

    except ValueError:
        bot.reply_to(message, "Некорректный формат стоимости. Пожалуйста, введите число.")
        bot.register_next_step_handler(message, calculate_cost, category)

def get_sdek_delivery_cost(message, total_without_sdek):
    city = message.text
    sdek_delivery_cost = calculate_delivery_sdek(city, item_data.get("обувь", {"dimensions": [1, 1, 1], "weight": 1})) # Примерные габариты и вес, функцию нужно реализовать

    if sdek_delivery_cost is not None:
        total_cost = total_without_sdek + sdek_delivery_cost
        bot.send_message(
            message.chat.id,
            f"Стоимость доставки СДЭК в город {city}: {sdek_delivery_cost:.2f} ₽\n"
            f"Итоговая стоимость заказа: {total_cost:.2f} ₽"
        )
    else:
        bot.send_message(
            message.chat.id,
            f"Не удалось определить стоимость доставки СДЭК в город {city}. Пожалуйста, свяжитесь с менеджером @oleglobok для уточнения."
        )

    bot.send_message(message.chat.id, "Для нового расчета введите /start.")

if __name__ == '__main__':
    print("Бот запущен!")
    bot.polling(none_stop=True)
