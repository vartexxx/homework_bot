import os
import time
import requests
import telegram
import logging
from http import HTTPStatus
from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    filename='main.log',
    filemode='w',
    format='%(funcName)s, %(lineno)s, %(levelname)s, %(message)s'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler('my_logger.log', encoding='UTF-8', maxBytes=5000000, backupCount=5)
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s, %(levelname)s, %(message)s, %(funcName)s, %(lineno)s'
)
handler.setFormatter(formatter)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Функция проверяет наличие перменных окружения"""
    if([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID].count(None) == 0):
        return True


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат по ID"""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug('Сообщение отправлено в чат {TELEGRAM_CHAT_ID}: {message}')
    except Exception:
        logger.error('Ошибка отправки сообщения')


def get_api_answer(timestamp):
    """Запрос к единственному ENDPOINT API-сервиса Яндекс Практикум.Домашка"""
    try:
        homework_status = requests.get(ENDPOINT, headers=HEADERS, params={'form_date': timestamp})
    except Exception as error:
        logging.error(f'Ошибка при запросе к API: {error}')
        raise Exception(f'Ошибка при запросе к API: {error}')
    if homework_status.status_code != HTTPStatus.OK:
        logging.error(f'Ошибка {homework_status.status_code}')
        raise Exception(f'Ошибка {homework_status.status_code}')
    try:
        return homework_status.json()
    except ValueError:
        logger.error('Ошибка ответа из формата JSON')
        raise ValueError('Ошибка ответа из формата JSON')


def check_response(response: dict) -> list:
    """Проверка ответа API на корректность"""
    if 'homeworks' not in response:
        raise KeyError('API вернуло неожидаемое значение')
    if not isinstance(response, dict):
        raise TypeError('Ответ API должен быть dict')
    try:
        homework_list = response['homeworks']
    except TypeError:
        raise TypeError('Тип значения \'homeworks\' не list')
    if not homework_list:
        raise Exception('Список домашних работ пуст')
    return homework_list


def parse_status(homework):
    """Извлечение статуса домашней работы"""
    try: 
        homework_name = homework['homework_name']
        homework_status = homework['status']
    except KeyError as error:
        logging.error(f'Ошибка доступа по ключу: {error}')
        send_message(f'Ошибка доступа по ключу: {error}')
        raise KeyError(f'Ошибка доступа по ключу: {error}')
    if homework_status not in HOMEWORK_VERDICTS:
        send_message(f'Неожиданный статус домашней работы: {homework_status}')
        raise Exception(f'Неожиданный статус домашней работы: {homework_status}')
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    current_status = ''
    current_error = ''
    if not check_tokens():
        logging.critical('Ошибка, определены не все переменные окружения')
        raise Exception('Ошибка, определены не все переменные окружения')
    while True:
        try:
            response = get_api_answer(timestamp)
            timestamp = response.get('current_date')
            message = parse_status(check_response(response))
            if message != current_status:
                send_message(bot, message)
                current_status = message
            time.sleep(RETRY_PERIOD)
        except Exception as error:
            logger.error(error)
            message = f'Сбой в работе программы: {error}'
            if(message != current_error):
                send_message(bot, message)
                current_error = message
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
