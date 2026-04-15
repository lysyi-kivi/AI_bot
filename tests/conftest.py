"""
Fixtures для тестов.

Содержит общие фикстуры для всех тестов:
- event_loop для asyncio
- test_db для изолированной БД
- mock_ai_client для моков AI запросов
"""

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from database.models import Base


# === Fixtures для asyncio ===
@pytest.fixture(scope="session")
def event_loop_policy():
    """Используем DefaultEventLoopPolicy для asyncio тестов."""
    return asyncio.DefaultEventLoopPolicy()


# === Fixtures для базы данных ===
@pytest.fixture(scope="session")
def test_db_url():
    """URL тестовой SQLite базы данных в памяти."""
    return "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def test_engine(test_db_url):
    """Создает тестовый движок SQLAlchemy."""
    engine = create_async_engine(test_db_url, echo=False, future=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_session(test_engine):
    """Создает тестовую сессию SQLAlchemy."""
    async_session_maker = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_maker() as session:
        yield session


# === Fixtures для AI моков ===
@pytest.fixture
def mock_completion_response():
    """Возвращает мок ответа от AI API."""
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="Это тестовый ответ от AI ассистента."))
    ]
    return mock_response


@pytest_asyncio.fixture
async def mock_ai_client(mock_completion_response):
    """Мокает AI клиент для тестов."""
    with patch("ai_engine.main_engine.client") as mock_client:
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion_response)
        mock_client.close = AsyncMock()
        yield mock_client


# === Fixtures для Telegram бота ===
@pytest.fixture
def mock_telegram_message():
    """Создает мок Telegram сообщения."""
    message = MagicMock()
    message.text = "Привет, бот!"
    message.from_user.id = 123456789
    message.from_user.full_name = "Test User"
    message.answer = AsyncMock()
    return message


# === Fixtures для ModelManager ===
@pytest.fixture
def test_model_config():
    """Тестовая конфигурация моделей."""
    return [
        ("test/model-small", 1000),
        ("test/model-medium", 5000),
        ("test/model-large", 10000),
    ]


@pytest.fixture
def clean_usage_file(tmp_path):
    """Создает временный файл для usage статистики."""
    usage_file = tmp_path / "test_usage.json"
    old_value = os.environ.get("AI_MODEL_USAGE_FILE")
    os.environ["AI_MODEL_USAGE_FILE"] = str(usage_file)

    yield str(usage_file)

    if old_value:
        os.environ["AI_MODEL_USAGE_FILE"] = old_value
    elif "AI_MODEL_USAGE_FILE" in os.environ:
        del os.environ["AI_MODEL_USAGE_FILE"]
