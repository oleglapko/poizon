import requests
from datetime import datetime
from bs4 import BeautifulSoup
import logging

# Настройка базового логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def calculate_yuan_rate():
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        url = f"https://www.cbr.ru/currency_base/daily/?UniDbQuery.Posted=True&UniDbQuery.To={today}"
        response = requests.get(url)
        response.raise_for_status()  # Проверка на ошибки HTTP

        soup = BeautifulSoup(response.text, 'html.parser')
        yuan_row = soup.find('td', text='Китайский юань')
        if not yuan_row:
            logging.error("Не удалось найти строку с курсом юаня на сайте ЦБ РФ.")
            return None

        parent_row = yuan_row.find_parent('tr')
        if not parent_row:
            logging.error("Не удалось найти родительскую строку для курса юаня на сайте ЦБ РФ.")
            return None

        cells = parent_row.find_all('td')
        if len(cells) < 5:
            logging.error(f"Недостаточно данных в строке курса юаня на сайте ЦБ РФ. Найдено {len(cells)} ячеек.")
            return None

        try:
            nominal_str = cells[3].text
            value_str = cells[4].text.replace(',', '.')
            nominal = float(nominal_str)
            value = float(value_str)
            yuan_value = value / nominal
            return yuan_value * 1.11  # Курс ЦБ + 11%
        except ValueError as e:
            logging.error(f"Ошибка при преобразовании курса юаня в число: {e}. Значения: nominal='{nominal_str}', value_str='{value_str}'")
            return None

    except requests.exceptions.RequestException as e:
        logging.error(f"Ошибка при получении курса валют с сайта ЦБ РФ: {e}")
        return None
    except Exception as e:
        logging.error(f"Непредвиденная ошибка при получении курса валют: {e}")
        return None

if __name__ == '__main__':
    yuan_rate = calculate_yuan_rate()
    if yuan_rate:
        print(f"Текущий курс юаня (ЦБ + 11%): {yuan_rate:.2f}")
    else:
        print("Не удалось получить курс юаня.")
