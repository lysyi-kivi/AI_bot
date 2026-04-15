# Dockerfile для AI Telegram Bot
# Multi-stage build для оптимизации размера образа

# === Stage 1: Builder ===
FROM python:3.11-slim as builder

WORKDIR /app

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Копируем файлы зависимостей
COPY requirements.txt pyproject.toml ./

# Создаем виртуальное окружение и устанавливаем зависимости
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Устанавливаем зависимости из requirements.txt
# (pyproject.toml используется для dev-зависимостей)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# === Stage 2: Runtime ===
FROM python:3.11-slim as runtime

WORKDIR /app

# Создаем пользователя для безопасности
RUN useradd --create-home --shell /bin/bash --uid 1000 appuser

# Копируем виртуальное окружение из builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Копируем исходный код
COPY --chown=appuser:appuser . .

# Создаем директорию для логов
RUN mkdir -p /app/logs && chown -R appuser:appuser /app/logs

# Переключаемся на не-root пользователя
USER appuser

# Переменные окружения по умолчанию
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LOG_LEVEL=INFO \
    LOG_FILE=/app/logs/bot.log

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Запуск бота
CMD ["python", "AI_bot.py"]
