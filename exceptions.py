class SendMessageError(Exception):
    """Ошибка отправки сообщения через telegram-бота."""
    pass


class HomeworkEndpointError(Exception):
    """Endpoint API Яндекс Практикум.Домашка недоступен."""
    pass


class ResponseError(Exception):
    """Ошибка при запросе к сервису Яндекс Практикум.Домашка."""
    pass


class MissingTokensError(Exception):
    """Отсутствуют одна или несколько переменных окружения."""
    pass
