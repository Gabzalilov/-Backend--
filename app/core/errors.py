class AppError(Exception):
    """Expected application error that may safely be shown to an API client."""

    status_code = 500
    code = "application_error"
    public_message = "Не удалось обработать запрос"

    def __init__(self, message: str | None = None, *, headers: dict[str, str] | None = None):
        super().__init__(message or self.public_message)
        self.public_message = message or self.public_message
        self.headers = headers or {}


class RateLimitExceeded(AppError):
    status_code = 429
    code = "rate_limit_exceeded"
    public_message = "Слишком много обращений. Попробуйте позже"


class EmailDeliveryError(AppError):
    status_code = 503
    code = "email_delivery_unavailable"
    public_message = "Обращение сохранено, но уведомление временно не отправлено"


class MetricsUnauthorized(AppError):
    status_code = 401
    code = "metrics_unauthorized"
    public_message = "Неверный или отсутствующий ключ метрик"
