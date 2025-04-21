import telebot
import requests
import json
from datetime import datetime
from utils import calculate_yuan_rate
from keyboards import category_keyboard

# Замени 'YOUR_BOT_TOKEN' на токен своего бота
BOT_TOKEN = '7655184269:AAFnOEwzH3NhGYvOOjgfJNMuvkjFyrpbmhU'
bot = telebot.TeleBot(BOT_TOKEN)

CHINA_TO_MOSCOW_DELIVERY_RATE = 789  # руб/кг
COMMISSION_RATE = 0.10  # 10%

item_data = {
    "обувь": {"dimensions": [36, 26, 15], "weight": 1.5},
    "футболка\\кофта\\штаны": {"dimensions": [23, 17, 13], "weight": 0.6},
}

user_data = {}

@bot.message_handler(commands=['start'])
def greet(message):
    bot.reply_to(message, "Привет! Я бот для расчета стоимости товаров с Poizon. Какой товар вы планируете заказать?")
    bot.send_message(message.chat.id, "Выберите категорию товара:", reply_markup=category_keyboard())
    user_data[message.chat.id] = {}

@bot.callback_query_handler(func=lambda call: call.data in item_data)
def process_category(call):
    category = call.data
    user_data[call.message.chat.id]['category'] = category
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text=f"Вы выбрали категорию '{category}'. Пожалуйста, укажите стоимость товара в юанях.",
                          reply_markup=None)
    bot.register_next_step_handler(call.message, ask_yuan_price)

@bot.callback_query_handler(func=lambda call: call.data == 'другое')
def handle_other_category(call):
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text="Пожалуйста, свяжитесь с менеджером @oleglobok для расчета стоимости нестандартных товаров.",
                          reply_markup=None)

def ask_yuan_price(message):
    try:
        yuan_price = float(message.text)
        if yuan_price <= 0:
            bot.reply_to(message, "Стоимость товара должна быть положительным числом. Пожалуйста, введите корректную стоимость.")
            bot.register_next_step_handler(message, ask_yuan_price)
            return

        chat_id = message.chat.id
        user_data[chat_id]['yuan_price'] = yuan_price
        category = user_data[chat_id]['category']

        yuan_rate = calculate_yuan_rate()
        if yuan_rate is None:
            bot.send_message(chat_id, "Произошла ошибка при получении курса валют. Пожалуйста, попробуйте позже.")
            return

        rub_price_without_commission = yuan_price * yuan_rate
        commission = rub_price_without_commission * COMMISSION_RATE
        rub_price_with_commission = rub_price_without_commission + commission

        weight = item_data[category]["weight"]
        delivery_china_to_moscow = weight * CHINA_TO_MOSCOW_DELIVERY_RATE

        total_without_sdek = rub_price_with_commission + delivery_china_to_moscow

        bot.send_message(
            chat_id,
            f"Предварительный расчет:\n"
            f"Курс юаня (ЦБ + 11%): {yuan_rate:.2f} ₽\n"
            f"Стоимость товара без комиссии: {rub_price_without_commission:.2f} ₽\n"
            f"Комиссия 10%: {commission:.2f} ₽\n"
            f"Стоимость товара с комиссией: {rub_price_with_commission:.2f} ₽\n"
            f"Доставка из Китая до Москвы ({weight} кг): {delivery_china_to_moscow:.2f} ₽\n"
            f"Итого без учета доставки по РФ: {total_without_sdek:.2f} ₽\n\n"
            f"Обратите внимание: к этой стоимости будет добавлена стоимость доставки СДЭК по России. "
            f"Точная стоимость доставки СДЭК будет известна после оформления заказа."
        )

    except ValueError:
        bot.reply_to(message, "Некорректный формат стоимости. Пожалуйста, введите число.")
        bot.register_next_step_handler(message, ask_yuan_price)
    except KeyError:
        bot.send_message(message.chat.id, "Пожалуйста, выберите категорию товара перед вводом стоимости.")
        bot.register_next_step_handler(message, ask_category)

if __name__ == '__main__':
    print("Бот запущен!")
    bot.polling(none_stop=True)
