import logging
import os
import telegram
import time
import requests

from http import HTTPStatus
from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler
from requests import RequestException

from exceptions import (
    SendMessageError,
    HomeworkEndpointError,
    ResponseError,
    MissingTokensError
)

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
GLOBAL_VARIABLES = ('PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID')
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


def check_tokens() -> None:
    """Функция проверяет наличие перменных окружения."""
    logger.info('Проверка наличия переменных окружения')
    for value in GLOBAL_VARIABLES:
        if globals()[value] is None:
            logger.critical(f'Пременная окружения: {value} отсутствует.')
            raise MissingTokensError(f'Пременная окружения: {value} отсутствует.')


def send_message(bot: telegram.Bot, message: str) -> None:
    """Функция отправляет сообщениие через бота в чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug(
            f'Сообщение отправлено в чат {TELEGRAM_CHAT_ID}: {message}'
        )
    except telegram.error.TelegramError as error:
        logger.error(
            f'Ошибка - {error} при отправке сообщения: {message}'
        )
        raise SendMessageError('Ошибка отправки сообщения')


def get_api_answer(timestamp: int) -> dict:
    """Функция выполняет запрос к единственному ENDPOINT API."""
    playload = {'from_date': timestamp}
    try:
        homework_status = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=playload
        )
    except RequestException as error:
        logger.error(f'Ошибка при запросе API: {error}')
        raise HomeworkEndpointError(f'Ошибка при запросе API: {error}')
    if homework_status.status_code != HTTPStatus.OK:
        raise ResponseError('API вернул статус отличный от 200')
    return homework_status.json()


def check_response(response: dict) -> list:
    """Проверка ответа запроса от API."""
    if not isinstance(response, dict):
        logger.error(f'Ответ запроса - не словарь. {type(response)}')
        raise TypeError(f'Ответ запроса - не словарь. {type(response)}')
    if 'homeworks' not in response:
        logger.error(f'Ошибка доступа по ключу \'homeworks\':')
        raise KeyError('Ошибка доступа по ключу \'homeworks\'')
    homework_list = response['homeworks']
    if not isinstance(homework_list, list):
        logger.error(
            f'Homeworks представлены не в виде списка: {type(homework_list)}'
        )
        raise TypeError('Homeworks представлены не в виде списка')
    return homework_list


def parse_status(homework: dict) -> str:
    """Функция проверяет наличие статуса домашней работы в ответе."""
    if 'homework_name' not in homework:
        logger.error('Неверный ответ сервера по ключу \'homework_name\'')
        raise KeyError('Неверный ответ сервера по ключу \'homework_name\'')
    if 'status' not in homework:
        logger.error('Неверный ответ сервера по ключу \'status\'')
        raise KeyError('Неверный ответ сервера по ключу \'status\'')
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if(homework_status not in HOMEWORK_VERDICTS) or not homework_status:
        logger.error(f'Статус работы неккоректен: {homework_status}')
        raise KeyError(f'Статус работы неккоректен: {homework_status}')
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
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
