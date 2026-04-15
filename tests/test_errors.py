"""
Тесты для модуля обработки ошибок.

Проверяют:
- retry_async декоратор
- handle_api_errors декоратор
- CircuitBreaker класс
"""

import asyncio
import time

import pytest
from utils.errors import (
    APIError,
    CircuitBreaker,
    RateLimitError,
    ServiceUnavailableError,
    handle_api_errors,
    retry_async,
)


class TestRetryAsync:
    """Тесты для декоратора retry_async."""

    @pytest.mark.asyncio
    async def test_success_no_retry(self):
        """Проверка что успешный вызов не вызывает повторных попыток."""
        call_count = 0

        @retry_async(max_attempts=3, delay=0.1)
        async def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await successful_func()
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        """Проверка повторных попыток при ошибке."""
        call_count = 0

        @retry_async(max_attempts=3, delay=0.1)
        async def failing_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary error")
            return "success"

        result = await failing_then_success()
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_all_attempts_exhausted(self):
        """Проверка что после всех попыток ошибка пробрасывается."""
        call_count = 0

        @retry_async(max_attempts=3, delay=0.1)
        async def always_fails():
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")

        with pytest.raises(ValueError):
            await always_fails()

        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_only_specified_exceptions(self):
        """Проверка что retry работает только для указанных исключений."""
        call_count = 0

        @retry_async(max_attempts=3, delay=0.1, exceptions=(ValueError,))
        async def raises_type_error():
            nonlocal call_count
            call_count += 1
            raise TypeError("Wrong type")

        with pytest.raises(TypeError):
            await raises_type_error()

        # Должен быть вызван только 1 раз (TypeError не ловится)
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_backoff_delay(self):
        """Проверка экспоненциального увеличения задержки."""
        delays = []
        last_time = None

        @retry_async(max_attempts=3, delay=0.1, backoff=2.0)
        async def track_delays():
            nonlocal last_time
            current_time = time.time()
            if last_time:
                delays.append(current_time - last_time)
            last_time = current_time
            raise ValueError("Fail")

        with pytest.raises(ValueError):
            await track_delays()

        # Проверяем что задержки увеличиваются
        assert len(delays) == 2
        assert delays[1] > delays[0]


class TestHandleApiErrors:
    """Тесты для декоратора handle_api_errors."""

    @pytest.mark.asyncio
    async def test_success_passes_through(self):
        """Проверка что успешный вызов проходит без изменений."""

        @handle_api_errors(fallback_value="fallback")
        async def success_func():
            return "success"

        result = await success_func()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_fallback_value_on_error(self):
        """Проверка возврата fallback значения при ошибке."""

        @handle_api_errors(fallback_value="fallback")
        async def failing_func():
            raise APIError("API error")

        result = await failing_func()
        assert result == "fallback"

    @pytest.mark.asyncio
    async def test_fallback_callable_on_error(self):
        """Проверка вызова fallback функции при ошибке."""

        async def fallback_handler():
            return "fallback from callable"

        @handle_api_errors(fallback_callable=fallback_handler)
        async def failing_func():
            raise APIError("API error")

        result = await failing_func()
        assert result == "fallback from callable"

    @pytest.mark.asyncio
    async def test_rate_limit_error(self):
        """Проверка обработки RateLimitError."""

        @handle_api_errors(fallback_value="rate limited")
        async def rate_limited_func():
            raise RateLimitError("Rate limit exceeded")

        result = await rate_limited_func()
        assert result == "rate limited"

    @pytest.mark.asyncio
    async def test_service_unavailable_error(self):
        """Проверка обработки ServiceUnavailableError."""

        @handle_api_errors(fallback_value="service unavailable")
        async def unavailable_func():
            raise ServiceUnavailableError("Service down")

        result = await unavailable_func()
        assert result == "service unavailable"

    @pytest.mark.asyncio
    async def test_silent_mode(self):
        """Проверка тихого режима без логирования."""

        @handle_api_errors(fallback_value="error", silent=True)
        async def failing_func():
            raise APIError("Silent error")

        result = await failing_func()
        assert result == "error"


class TestCircuitBreaker:
    """Тесты для CircuitBreaker."""

    @pytest.mark.asyncio
    async def test_initial_state_closed(self):
        """Проверка начального состояния CLOSED."""
        breaker = CircuitBreaker()
        assert breaker.state == "CLOSED"
        assert breaker.is_closed

    @pytest.mark.asyncio
    async def test_opens_after_threshold_failures(self):
        """Проверка перехода в OPEN после превышения порога ошибок."""
        breaker = CircuitBreaker(failure_threshold=3)

        for i in range(3):
            try:
                async with breaker:
                    raise ValueError("Error")
            except ValueError:
                pass

        assert breaker.state == "OPEN"
        assert breaker.is_open

    @pytest.mark.asyncio
    async def test_resets_on_success(self):
        """Проверка сброса счетчика ошибок при успехе."""
        breaker = CircuitBreaker(failure_threshold=3)

        # 2 ошибки
        for i in range(2):
            try:
                async with breaker:
                    raise ValueError("Error")
            except ValueError:
                pass

        # Успех
        async with breaker:
            pass  # Успешное выполнение

        # Счетчик должен сброситься
        assert breaker._failures == 0
        assert breaker.state == "CLOSED"

    @pytest.mark.asyncio
    async def test_blocks_when_open(self):
        """Проверка блокировки запросов в состоянии OPEN."""
        breaker = CircuitBreaker(failure_threshold=1)

        # Переводим в OPEN
        try:
            async with breaker:
                raise ValueError("Error")
        except ValueError:
            pass

        assert breaker.state == "OPEN"

        # Следующий запрос должен быть заблокирован
        with pytest.raises(ServiceUnavailableError):
            async with breaker:
                pass

    @pytest.mark.asyncio
    async def test_half_open_after_recovery_timeout(self):
        """Проверка перехода в HALF_OPEN после timeout."""
        breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)

        # Переводим в OPEN
        try:
            async with breaker:
                raise ValueError("Error")
        except ValueError:
            pass

        assert breaker.state == "OPEN"

        # Ждем восстановления
        await asyncio.sleep(0.15)

        # Следующий запрос должен перевести в HALF_OPEN
        async with breaker:
            pass  # Успех

        assert breaker.state == "CLOSED"

    @pytest.mark.asyncio
    async def test_manual_reset(self):
        """Проверка ручного сброса."""
        breaker = CircuitBreaker(failure_threshold=1)

        # Переводим в OPEN
        try:
            async with breaker:
                raise ValueError("Error")
        except ValueError:
            pass

        # Ручной сброс
        breaker.reset()

        assert breaker.state == "CLOSED"
        assert breaker._failures == 0
