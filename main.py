import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext, MessageHandler, Filters
import requests
from config import TOKEN, MANAGER_USERNAME

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Константы
CB_RATE_MARKUP = 0.11  # Наценка 11% к курсу ЦБ
COMMISSION = 0.10      # Комиссия 10%
SHIPPING_RATE = 789    # Доставка из Китая (руб/кг)

CATEGORIES = {
    'shoes': {'name': 'Обувь', 'weight': 1.5},
    'clothes': {'name': 'Футболка/Кофта/Штаны', 'weight': 0.6},
    'other': {'name': 'Другое', 'weight': None}
}

def start(update: Update, context: CallbackContext) -> None:
    """Приветствие и запрос категории товара."""
    user = update.effective_user
    update.message.reply_text(
        f"Привет, {user.first_name}! Я помогу рассчитать стоимость товара с Poizon.\n"
        "Выбери категорию товара:",
        reply_markup=get_categories_keyboard()
    )

def get_categories_keyboard():
    """Создает клавиатуру с категориями товаров."""
    keyboard = [
        [InlineKeyboardButton(CATEGORIES['shoes']['name'], callback_data='shoes')],
        [InlineKeyboardButton(CATEGORIES['clothes']['name'], callback_data='clothes')],
        [InlineKeyboardButton(CATEGORIES['other']['name'], callback_data='other')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_cny_rate():
    """Получает курс юаня от ЦБ РФ и добавляет 11%."""
    try:
        response = requests.get('https://www.cbr-xml-daily.ru/daily_json.js', timeout=5)
        response.raise_for_status()
        rate = response.json()['Valute']['CNY']['Value']
        return rate * (1 + CB_RATE_MARKUP)
    except Exception as e:
        logger.error(f"Ошибка при получении курса: {e}")
        return None

def calculate_cost(price_cny, weight_kg):
    """Рассчитывает итоговую стоимость."""
    cny_rate = get_cny_rate()
    if cny_rate is None:
        return None, "Не удалось получить курс юаня. Попробуйте позже."

    product_cost_rub = price_cny * cny_rate
    commission = product_cost_rub * COMMISSION
    shipping_china = weight_kg * SHIPPING_RATE
    total = product_cost_rub + commission + shipping_china

    message = (
        f"📊 Расчет стоимости:\n"
        f"• Цена товара: {price_cny} ¥ ≈ {product_cost_rub:.2f} ₽ (курс: {cny_rate:.2f} ₽/¥)\n"
        f"• Комиссия 10%: {commission:.2f} ₽\n"
        f"• Доставка из Китая: {shipping_china:.2f} ₽\n"
        f"➖➖➖➖➖➖➖➖➖\n"
        f"💰 Итого: {total:.2f} ₽\n\n"
        f"ℹ️ К этой сумме добавится стоимость доставки СДЭК, которая будет известна после оформления заказа."
    )
    return total, message

def handle_category(update: Update, context: CallbackContext) -> None:
    """Обрабатывает выбор категории."""
    query = update.callback_query
    query.answer()  # Важно для работы кнопок!
    
    category = query.data
    context.user_data['category'] = category

    if category == 'other':
        query.edit_message_text(f"Для категории '{CATEGORIES[category]['name']}' свяжитесь с менеджером @{MANAGER_USERNAME}.")
        return

    query.edit_message_text(f"Выбрана категория: {CATEGORIES[category]['name']}\nВведите цену товара в юанях:")

def handle_price(update: Update, context: CallbackContext) -> None:
    """Обрабатывает ввод цены и выводит расчет."""
    try:
        price_cny = float(update.message.text.replace(',', '.'))
        category = context.user_data.get('category')

        if category not in ['shoes', 'clothes']:
            update.message.reply_text("Пожалуйста, выберите категорию через /start")
            return

        weight_kg = CATEGORIES[category]['weight']
        total, message = calculate_cost(price_cny, weight_kg)

        if total is not None:
            update.message.reply_text(message)
        else:
            update.message.reply_text(message)
    except ValueError:
        update.message.reply_text("Пожалуйста, введите корректную цену (например, 299.99)")

def error_handler(update: Update, context: CallbackContext) -> None:
    """Логирует ошибки."""
    logger.error(f"Ошибка при обработке сообщения: {context.error}")

def main() -> None:
    """Запуск бота."""
    updater = Updater(TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # Обработчики команд
    dispatcher.add_handler(CommandHandler('start', start))
    
    # Обработчики кнопок
    dispatcher.add_handler(CallbackQueryHandler(handle_category))
    
    # Обработчик текстовых сообщений
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_price))
    
    # Обработчик ошибок
    dispatcher.add_error_handler(error_handler)

    updater.start_polling()
    logger.info("Бот запущен и работает...")
    updater.idle()

if __name__ == '__main__':
    main()
