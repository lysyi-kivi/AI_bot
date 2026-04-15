# Руководство по использованию

## 📋 Что было добавлено

Этот документ описывает все добавленные компоненты для превращения проекта в полноценный pet-проект.

---

## 1. Документация

### `README.md`
**Назначение:** Главная страница проекта с описанием, инструкциями по установке и использованию.

**Содержит:**
- Описание проекта и его особенностей
- Быстрый старт (установка, настройка, запуск)
- Таблицу переменных окружения
- Архитектурную схему
- Инструкции для Docker и разработки

**Как использовать:**
```bash
# Просто откройте в браузере на GitHub
# Или локально:
cat README.md
```

### `.env.example`
**Назначение:** Шаблон файла с переменными окружения.

**Содержит:**
- Все необходимые переменные с комментариями
- Примеры значений
- Описание каждой переменной

**Как использовать:**
```bash
# Скопируйте и заполните своими значениями
cp .env.example .env
# Отредактируйте .env
```

---

## 2. Конфигурация проекта

### `pyproject.toml`
**Назначение:** Единый файл конфигурации для зависимостей и инструментов.

**Содержит:**
- Зависимости проекта (dependencies)
- Dev-зависимости (pytest, ruff, mypy, black)
- Настройки pytest для тестов
- Настройки ruff для линтинга
- Настройки mypy для проверки типов
- Настройки coverage для тестов

**Как использовать:**
```bash
# Установка зависимостей
pip install -e ".[dev]"

# Запуск тестов
pytest

# Линтинг
ruff check .

# Форматирование
ruff format .

# Проверка типов
mypy .
```

---

## 3. Логирование

### `utils/logging_config.py`
**Назначение:** Централизованная настройка логирования.

**Функции:**
- `setup_logging()` — настраивает root logger
- `get_logger(name)` — получает logger для модуля

**Как использовать:**
```python
from utils.logging_config import setup_logging, get_logger

# В главном файле
logger = setup_logging(level="INFO", log_file="logs/bot.log")
log = get_logger("main")

# В любом модуле
log = get_logger("module_name")
log.info("Сообщение")
log.error("Ошибка", exc_info=True)
```

**Обновленные файлы:**
- `AI_bot.py` — логирование запуска/остановки
- `ai_engine/main_engine.py` — логирование запросов к моделям
- `ai_engine/summarizer.py` — логирование ошибок суммаризатора
- `database/engine.py` — логирование создания таблиц

---

## 4. Тесты

### Структура тестов
```
tests/
├── conftest.py          # Fixtures для всех тестов
├── test_manager.py      # Тесты ModelManager
├── test_sanitize.py     # Тесты sanitize_html
├── test_database.py     # Тесты ORM и моделей
└── test_errors.py       # Тесты обработки ошибок
```

### `conftest.py`
**Назначение:** Общие фикстуры для тестов.

**Фикстуры:**
- `test_session` — изолированная SQLite БД
- `mock_ai_client` — мок AI клиента
- `mock_telegram_message` — мок Telegram сообщения
- `test_model_config` — тестовая конфигурация моделей

### Запуск тестов
```bash
# Все тесты
pytest

# С покрытием
pytest --cov

# Конкретный файл
pytest tests/test_manager.py

# С выводом логов
pytest -s
```

---

## 5. Docker

### `Dockerfile`
**Назначение:** Образ для контейнеризации приложения.

**Особенности:**
- Multi-stage build для малого размера
- Запуск от не-root пользователя (безопасность)
- Health check для мониторинга
- Оптимизированные слои

### `docker-compose.yml`
**Назначение:** Оркестрация бота и PostgreSQL.

**Сервисы:**
- `db` — PostgreSQL 15 с health check
- `bot` — приложение с авто-перезапуском

**Как использовать:**
```bash
# Запуск
docker-compose up --build

# Запуск в фоне
docker-compose up -d

# Просмотр логов
docker-compose logs -f bot

# Остановка
docker-compose down

# Остановка с удалением данных
docker-compose down -v
```

### `.env` для Docker
```bash
# Создайте файл .env с переменными:
TOKEN=your_bot_token
DB_USER=postgres
DB_PASSWORD=postgres
DB_NAME=ai_bot_db
IOINTELLIGENCE_API_KEY=your_api_key
```

---

## 6. Pre-commit хуки

### `.pre-commit-config.yaml`
**Назначение:** Автоматические проверки перед коммитом.

**Инструменты:**
| Инструмент | Назначение |
|------------|------------|
| ruff | Линтинг и форматирование |
| black | Форматирование кода |
| isort | Сортировка импортов |
| mypy | Проверка типов |
| bandit | Проверка безопасности |
| pre-commit-hooks | Разные проверки (JSON, YAML, secrets) |

**Как использовать:**
```bash
# Установка pre-commit
pip install pre-commit
pre-commit install

# Запуск на всех файлах
pre-commit run --all-files

# Проверка конкретного файла
pre-commit run --files AI_bot.py
```

---

## 7. Обработка ошибок

### `utils/errors.py`
**Назначение:** Унифицированная обработка ошибок и retry-логика.

**Компоненты:**

#### Исключения
```python
from utils.errors import APIError, RateLimitError, ServiceUnavailableError

# Базовое исключение API
raise APIError("Ошибка API", status_code=500)

# Превышение лимита
raise RateLimitError("Слишком много запросов", retry_after=60)

# Сервис недоступен
raise ServiceUnavailableError("Сервис вниз")
```

#### Декоратор `retry_async`
```python
from utils.errors import retry_async

@retry_async(
    max_attempts=3,
    delay=1.0,
    backoff=2.0,
    exceptions=(ConnectionError, TimeoutError)
)
async def fetch_data():
    return await api_call()
```

#### Декоратор `handle_api_errors`
```python
from utils.errors import handle_api_errors

@handle_api_errors(
    fallback_value="Извините, сервис недоступен",
    silent=False
)
async def call_ai():
    return await ai_api()
```

#### CircuitBreaker
```python
from utils.errors import CircuitBreaker, ServiceUnavailableError

breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=30.0
)

async def make_request():
    async with breaker:
        return await api_call()
```

**Обновленные файлы:**
- `ai_engine/main_engine.py` — специфичная обработка ошибок OpenAI API

---

## 8. Обновлённый `.gitignore`

**Добавлено:**
- Логи (`logs/`, `*.log`)
- Базы данных (`*.db`, `*.sqlite`)
- Кэши тестов (`.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`)
- Покрытия (`htmlcov/`, `.coverage`)
- IDE файлы (`.idea/`, `*.swp`)

---

## 🚀 Быстрый старт после изменений

### 1. Установка зависимостей
```bash
# Создайте виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/macOS

# Установите зависимости
pip install -r requirements.txt

# Или для разработки
pip install -e ".[dev]"
```

### 2. Настройка
```bash
# Скопируйте шаблон
cp .env.example .env

# Заполните .env своими значениями
# TOKEN, DB_URL, IOINTELLIGENCE_API_KEY, AI_BASE_URL
```

### 3. Pre-commit (опционально)
```bash
pre-commit install
```

### 4. Запуск тестов
```bash
pytest
```

### 5. Запуск бота
```bash
# Обычный запуск
python AI_bot.py

# С логированием в файл
LOG_FILE=logs/bot.log python AI_bot.py
```

### 6. Docker (альтернатива)
```bash
# Создайте .env файл
# Запустите
docker-compose up --build
```

---

## 📊 Итоговая структура проекта

```
ai-bot/
├── AI_bot.py                 ✅ Обновлён (logging)
├── README.md                 ✅ Создан
├── .env.example              ✅ Создан
├── pyproject.toml            ✅ Создан
├── Dockerfile                ✅ Создан
├── docker-compose.yml        ✅ Создан
├── .pre-commit-config.yaml   ✅ Создан
├── .gitignore                ✅ Обновлён
│
├── ai_engine/
│   ├── main_engine.py        ✅ Обновлён (logging, error handling)
│   ├── manager.py
│   ├── summarizer.py         ✅ Обновлён (logging)
│   └── sanitize.py
│
├── database/
│   ├── models.py
│   ├── engine.py             ✅ Обновлён (logging)
│   └── orm_query.py
│
├── handlers/
│   └── user_private.py
│
├── middleware/
│   └── middleware.py
│
├── utils/                    ✅ Новая директория
│   ├── __init__.py
│   ├── logging_config.py     ✅ Создан
│   └── errors.py             ✅ Создан
│
└── tests/                    ✅ Новая директория
    ├── __init__.py
    ├── conftest.py           ✅ Создан
    ├── test_manager.py       ✅ Создан
    ├── test_sanitize.py      ✅ Создан
    ├── test_database.py      ✅ Создан
    └── test_errors.py        ✅ Создан
```

---

## 🔍 Проверка работоспособности

```bash
# 1. Проверка импортов
python -c "from AI_bot import dp, ai_bot; print('OK')"

# 2. Запуск тестов
pytest tests/test_manager.py -v
pytest tests/test_sanitize.py -v

# 3. Проверка линтером
ruff check .

# 4. Проверка типов
mypy ai_engine/ database/

# 5. Запуск бота
python AI_bot.py
```

---

## 📝 Следующие шаги (опционально)

1. **Admin panel** — веб-интерфейс для статистики
2. **Migrations** — Alembic для миграций БД
3. **CI/CD** — GitHub Actions для автотестов
4. **Rate limiting** — защита от злоупотреблений
5. **Мониторинг** — Prometheus/Grafana метрики
