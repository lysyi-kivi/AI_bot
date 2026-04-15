"""
Модуль обработки ошибок и retry-логики.

Предоставляет:
- Декораторы для автоматических повторных попыток
- Обработку специфичных ошибок API
- Graceful degradation при недоступности сервисов
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any

logger = logging.getLogger("ai_bot.utils.errors")


class APIError(Exception):
    """Базовое исключение для ошибок API."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class RateLimitError(APIError):
    """Превышен лимит запросов."""

    def __init__(self, message: str, retry_after: int | None = None):
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


class ServiceUnavailableError(APIError):
    """Сервис недоступен."""

    def __init__(self, message: str):
        super().__init__(message, status_code=503)


def retry_async(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
    logger: logging.Logger | None = None,
) -> Callable:
    """
    Декоратор для автоматических повторных попыток асинхронных функций.

    Args:
        max_attempts: Максимальное количество попыток
        delay: Начальная задержка между попытками (секунды)
        backoff: Множитель задержки (экспоненциальный backoff)
        exceptions: Кортеж исключений для обработки
        logger: Logger для вывода сообщений

    Returns:
        Декорированная функция

    Example:
        @retry_async(max_attempts=3, delay=1.0, exceptions=(ConnectionError,))
        async def fetch_data():
            ...
    """

    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            current_delay = delay
            last_exception: Exception | None = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if logger:
                        logger.warning(
                            f"Попытка {attempt}/{max_attempts} не удалась: {e}. "
                            f"Следующая попытка через {current_delay:.1f}с"
                        )

                    if attempt < max_attempts:
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        if logger:
                            logger.error(
                                f"Все {max_attempts} попыток исчерпаны. Последняя ошибка: {e}"
                            )

            # Достижение этой точки означает что все попытки исчерпаны
            if last_exception:
                raise last_exception
            raise RuntimeError("Unexpected state in retry_async")

        return wrapper

    return decorator


def handle_api_errors(
    fallback_value: Any = None,
    fallback_callable: Callable | None = None,
    silent: bool = False,
) -> Callable:
    """
    Декоратор для обработки ошибок API с fallback значением.

    Args:
        fallback_value: Значение для возврата при ошибке
        fallback_callable: Функция для вызова при ошибке (имеет приоритет)
        silent: Не логировать ошибки

    Returns:
        Декорированная функция

    Example:
        @handle_api_errors(fallback_value="Извините, сервис временно недоступен")
        async def call_ai_api():
            ...
    """

    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except RateLimitError as e:
                if not silent:
                    logger.warning(f"Rate limit exceeded: {e}")
                if fallback_callable:
                    return await fallback_callable(*args, **kwargs)
                return fallback_value
            except ServiceUnavailableError as e:
                if not silent:
                    logger.error(f"Service unavailable: {e}")
                if fallback_callable:
                    return await fallback_callable(*args, **kwargs)
                return fallback_value
            except APIError as e:
                if not silent:
                    logger.error(f"API error: {e}")
                if fallback_callable:
                    return await fallback_callable(*args, **kwargs)
                return fallback_value
            except Exception as e:
                if not silent:
                    logger.exception(f"Unexpected error in {func.__name__}: {e}")
                if fallback_callable:
                    return await fallback_callable(*args, **kwargs)
                return fallback_value

        return wrapper

    return decorator


class CircuitBreaker:
    """
    Circuit Breaker паттерн для защиты от каскадных сбоев.

    Состояния:
    - CLOSED: Нормальная работа, запросы проходят
    - OPEN: Сбой, запросы блокируются
    - HALF_OPEN: Проверка восстановления

    Example:
        breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=30)

        async def make_request():
            async with breaker:
                return await api_call()
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        logger: logging.Logger | None = None,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.logger = logger or logger

        self._failures = 0
        self._last_failure_time: float | None = None
        self._state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self._lock = asyncio.Lock()

    @property
    def state(self) -> str:
        return self._state

    @property
    def is_closed(self) -> bool:
        return self._state == "CLOSED"

    @property
    def is_open(self) -> bool:
        return self._state == "OPEN"

    async def __aenter__(self) -> "CircuitBreaker":
        import time

        async with self._lock:
            if self._state == "OPEN":
                elapsed = time.time() - (self._last_failure_time or 0)
                if elapsed >= self.recovery_timeout:
                    self._state = "HALF_OPEN"
                    if self.logger:
                        self.logger.info("Circuit breaker переход в HALF_OPEN")
                else:
                    raise ServiceUnavailableError("Circuit breaker OPEN")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        async with self._lock:
            if exc_type is not None:
                self._failures += 1
                self._last_failure_time = asyncio.get_event_loop().time()

                if self._failures >= self.failure_threshold:
                    self._state = "OPEN"
                    if self.logger:
                        self.logger.warning(
                            f"Circuit breaker переход в OPEN ({self._failures} ошибок)"
                        )
            else:
                # Успех - сбрасываем счетчики
                self._failures = 0
                self._state = "CLOSED"

    def reset(self) -> None:
        """Сброс circuit breaker в начальное состояние."""
        self._failures = 0
        self._last_failure_time = None
        self._state = "CLOSED"
