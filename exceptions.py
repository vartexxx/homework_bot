class SendMessageError(Exception):
    """Ошибка отправки сообщения через telegram-бота."""


class HomeworkEndpointError(Exception):
    """Endpoint API Яндекс Практикум.Домашка недоступен."""


class ResponseError(Exception):
    """Ошибка при запросе к сервису Яндекс Практикум.Домашка."""


class MissingTokensError(Exception):
    """Отсутствуют одна или несколько переменных окружения."""
