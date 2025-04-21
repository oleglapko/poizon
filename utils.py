import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

def calculate_yuan_rate():
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        url = f"https://www.cbr.ru/currency_base/daily/?UniDbQuery.Posted=True&UniDbQuery.To={today}"
        response = requests.get(url)
        response.raise_for_status()  # Проверка на ошибки HTTP

        soup = BeautifulSoup(response.text, 'html.parser')
        yuan_row = soup.find('td', text='Китайский юань').find_parent('tr')
        yuan_value_str = yuan_row.find_all('td')[4].text.replace(',', '.')
        yuan_value = float(yuan_value_str) / float(yuan_row.find_all('td')[3].text)
        return yuan_value * 1.11  # Курс ЦБ + 11%

    except requests.exceptions.RequestException as e:
        print(f"Ошибка при получении курса валют: {e}")
        return None
    except (AttributeError, ValueError) as e:
        print(f"Ошибка при обработке данных курса валют: {e}")
        return None

def calculate_delivery_sdek(city, item_info):
    """
    Функция для расчета стоимости доставки СДЭК.
    В реальном проекте здесь нужно будет интегрироваться с API СДЭК.
    Пока что это заглушка, возвращающая примерные значения или None.
    """
    # Внимание: Для реальной работы потребуется интеграция с API СДЭК.
    # Это может включать отправку запросов к их API с информацией о габаритах, весе и городах.
    # Для этого вам нужно будет изучить документацию СДЭК API.

    # Примерная логика (не является реальным расчетом СДЭК):
    if city.lower() == "москва":
        return 300  # Примерная стоимость
    elif city.lower() == "санкт-петербург":
        return 400  # Примерная стоимость
    elif city.lower() == "новосибирск":
        return 500  # Примерная стоимость
    else:
        return None # Не удалось определить стоимость

if __name__ == '__main__':
    yuan_rate = calculate_yuan_rate()
    if yuan_rate:
        print(f"Текущий курс юаня (ЦБ + 11%): {yuan_rate:.2f}")
    else:
        print("Не удалось получить курс юаня.")

    # Пример использования заглушки СДЭК
    print(f"Доставка СДЭК в Москву: {calculate_delivery_sdek('Москва', {'dimensions': [36, 26, 15], 'weight': 1.5})} ₽")
    print(f"Доставка СДЭК в Новосибирск: {calculate_delivery_sdek('Новосибирск', {'dimensions': [23, 17, 13], 'weight': 0.6})} ₽")
    print(f"Доставка СДЭК в несуществующий город: {calculate_delivery_sdek('Марс', {'dimensions': [1, 1, 1], 'weight': 0.1})} ₽")
