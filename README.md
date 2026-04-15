# AI Telegram Bot

🤖 Telegram-бот с интеграцией AI-моделей для генерации текста, идей и контента.

## Особенности

- **Мульти-модельная архитектура** — автоматический выбор между Mistral, DeepSeek, Llama-3.3
- **Управление токенами** — ежедневные лимиты на каждую модель
- **Сжатие контекста** — автоматическое суммаризирование длинных диалогов
- **Асинхронность** — полная поддержка asyncio для высокой производительности
- **Сохранение истории** — PostgreSQL для хранения пользователей и сообщений

---

## Быстрый старт

### Требования

- Python 3.10+
- PostgreSQL 14+
- Docker (опционально)

### Установка

1. **Клонируйте репозиторий**
```bash
git clone <repository-url>
cd ai-bot
```

2. **Создайте виртуальное окружение**
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# или
venv\Scripts\activate     # Windows
```

3. **Установите зависимости**
```bash
pip install -r requirements.txt
```

4. **Настройте переменные окружения**
```bash
cp .env.example .env
# Отредактируйте .env и заполните своими значениями
```

5. **Запустите бота**
```bash
python AI_bot.py
```

---

## Конфигурация

### Переменные окружения

Скопируйте `.env.example` в `.env` и заполните:

| Переменная | Описание | Пример |
|------------|----------|--------|
| `TOKEN` | Токен Telegram бота | `123456789:ABCdefGHIjklMNOpqrsTUVwxyz` |
| `DB_URL` | URL подключения к PostgreSQL | `postgresql+asyncpg://user:pass@localhost:5432/aibot` |
| `IOINTELLIGENCE_API_KEY` | API ключ для AI-провайдера | `your-api-key` |
| `AI_BASE_URL` | Базовый URL AI API | `https://api.example.com/v1` |
| `SUMMARIZER_MODEL` | Модель для суммаризации | `mistralai/Magistral-Small-2506` |
| `SUMMARY_THRESHOLD_CHARS` | Порог для суммаризации (символы) | `8000` |

---

## Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                      AI_bot.py                              │
│                    (точка входа)                            │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐    ┌─────────────────┐    ┌──────────────┐
│   handlers/   │    │  ai_engine/     │    │  database/   │
│ user_private  │    │  general_engine │    │   models.py  │
│               │    │  manager.py     │    │   engine.py  │
│               │    │  summarizer.py  │    │   orm_query  │
│               │    │  sanitize.py    │    │              │
└───────────────┘    └─────────────────┘    └──────────────┘
        │                     │                     │
        │                     ▼                     │
        │            ┌─────────────────┐           │
        │            │  OpenAI API     │           │
        │            │  (AI модели)    │           │
        │            └─────────────────┘           │
        │                                          │
        └─────────────────────┬────────────────────┘
                              │
                    ┌─────────────────┐
                    │   PostgreSQL    │
                    │   (история)     │
                    └─────────────────┘
```

### Компоненты

| Компонент | Описание |
|-----------|----------|
| `AI_bot.py` | Точка входа, инициализация бота и диспетчера |
| `handlers/` | Обработчики команд и сообщений Telegram |
| `ai_engine/` | Логика работы с AI моделями |
| `ai_engine/general_engine.py` | Основной движок AI, запросы к моделям |
| `ai_engine/manager.py` | Управление моделями и лимитами токенов |
| `ai_engine/summarizer.py` | Сжатие длинных диалогов |
| `ai_engine/sanitize.py` | Очистка HTML для Telegram |
| `database/` | Модели ORM и подключение к БД |
| `utils/` | Утилиты: обработка ошибок, логирование |
| `middleware/` | Промежуточное ПО (сессии БД) |

---

## Запуск в Docker

### Сборка и запуск

```bash
docker-compose up --build
```

### Переменные для Docker

Создайте `.env` файл с необходимыми переменными (см. выше).

---

## Разработка

### Запуск тестов

```bash
pytest
```

---

## Структура проекта

```
ai-bot/
├── AI_bot.py                 # Точка входа
├── requirements.txt          # Зависимости
├── docker-compose.yml        # Docker конфигурация
├── Dockerfile                # Docker образ
├── .env.example              # Шаблон переменных окружения
│
├── ai_engine/
│   ├── general_engine.py     # Основной движок AI
│   ├── manager.py            # Менеджер моделей
│   ├── summarizer.py         # Суммаризатор диалогов
│   └── sanitize.py           # Очистка HTML
│
├── database/
│   ├── models.py             # SQLAlchemy модели
│   ├── engine.py             # Подключение к БД
│   └── orm_query.py          # ORM запросы
│
├── handlers/
│   └── user_private.py       # Обработчики сообщений
│
├── middleware/
│   └── middleware.py         # Middleware для сессий БД
│
├── utils/
│   ├── errors.py             # Обработка ошибок
│   └── logging_config.py     # Настройка логирования
│
└── tests/
    ├── conftest.py           # Fixtures для тестов
    ├── test_database.py      # Тесты базы данных
    ├── test_errors.py        # Тесты обработки ошибок
    ├── test_manager.py       # Тесты менеджера моделей
    └── test_sanitize.py      # Тесты очистки HTML
```

---

## API Модели

Бот использует следующие AI модели (настраивается в `ai_engine/manager.py`):

| Модель | Дневной лимит токенов | Назначение |
|--------|----------------------|------------|
| `mistralai/Mistral-Large-Instruct-2411` | 200,000 | Сложные запросы |
| `deepseek-ai/DeepSeek-R1-0528` | 150,000 | Средние запросы |
| `mistralai/Magistral-Small-2506` | 80,000 | Простые запросы |
| `meta-llama/Llama-3.3-70B-Instruct` | 100,000 | Резервная модель |

---

## Лицензия

MIT

---

## Контакты

Для вопросов и предложений создайте issue в репозитории.
