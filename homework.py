import logging
import os
import telegram
import time
import requests

from http import HTTPStatus
from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler

from exceptions import *

load_dotenv()


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

logging.basicConfig(
    level=logging.DEBUG,
    filename='main.log',
    filemode='w',
    format='%(funcName)s, %(lineno)s, %(levelname)s, %(message)s'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler(
    'my_logger.log',
    encoding='UTF-8',
    maxBytes=5000000,
    backupCount=5
)
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s, %(levelname)s, %(message)s, %(funcName)s, %(lineno)s'
)
handler.setFormatter(formatter)


def check_tokens():
    """Функция проверяет наличие перменных окружения."""
    logger.info('Проверка наличия переменных окружения')
    if([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID].count(None) == 0):
        return True    


def send_message(bot, message):
    """Функция отправляет сообщениие через бота в чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug(f'Сообщение отправлено в чат {TELEGRAM_CHAT_ID}: {message}')
    except Exception:
        logger.error('Ошибка отправки сообщения')
        raise SendMessageError('Ошибка отправки сообщения')


def get_api_answer(timestamp):
    """Функция выполняет запрос к единственному ENDPOINT API."""
    playload = {'from_date': timestamp}
    try:
        homework_status = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=playload
        )
    except Exception as error:
        logger.error(f'Ошибка при запросе API: {error}')
        raise HomeworkEndpointError(f'Ошибка при запросе API: {error}')
    if homework_status.status_code == HTTPStatus.OK:
        return homework_status.json()
    else:
        raise ResponseError('API вернул статус отличный от 200')


def check_response(response):
    """Проверка ответа запроса от API."""
    try:
        homework_list = response['homeworks']
    except KeyError as error:
        logger.error(f'Ошибка доступа по ключу \'homeworks\': {error}')
    if not isinstance(homework_list, list):
        logger.error('Homeworks представлены не в виде списка')
        raise TypeError('Homeworks представлены не в виде списка')
    return homework_list


def parse_status(homework):
    """Функция проверяет наличие статуса домашней работы в ответе."""
    try:
        homework_name = homework['homework_name']
    except KeyError:
        logger.error('Неверный ответ сервера')
    homework_status = homework['status']
    if(homework_status not in HOMEWORK_VERDICTS) or (homework_status == ''):
        logger.error(f'Статус работы неккоректен: {homework_status}')
        raise KeyError(f'Статус работы неккоректен: {homework_status}')
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Отсутствуют необходимые пременные окружения')
        raise MissingTokensError('Отсутствуют необходимые переменные окружения')
    timestamp = int(time.time())
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    last_message = ''
    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks[0])
            else:
                logger.debug('Нет новых статусов проверки работы')
                message = 'Нет новых статусов проверки работы'
            if message != last_message:
                send_message(bot, message)
                last_message = message
            else:
                logger.info(message)
        except Exception as error:
            logger.error(f'Сбой в работе программы: {error}')
            send_message(bot, f'Сбой в работе программы: {error}')
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
