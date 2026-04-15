"""
Тесты для database модуля.

Проверяют:
- Создание и получение пользователей
- Добавление и получение сообщений
- Связи между моделями
"""

import pytest
import pytest_asyncio

from database.models import Message, User
from database.orm_query import add_message, get_last_messages, get_or_create_user


class TestUserModel:
    """Тесты для модели User."""

    @pytest_asyncio.fixture
    async def user(self, test_session):
        """Создает тестового пользователя."""
        user = User(telegram_id=123456789, name="Test User")
        test_session.add(user)
        await test_session.commit()
        await test_session.refresh(user)
        return user

    async def test_create_user(self, test_session):
        """Проверка создания пользователя."""
        user = User(telegram_id=987654321, name="Another User")
        test_session.add(user)
        await test_session.commit()

        assert user.id is not None
        assert user.telegram_id == 987654321
        assert user.name == "Another User"

    async def test_user_unique_telegram_id(self, test_session):
        """Проверка уникальности telegram_id."""
        user1 = User(telegram_id=111111111, name="User 1")
        test_session.add(user1)
        await test_session.commit()

        # Попытка создать пользователя с тем же telegram_id должна вызвать ошибку
        from sqlalchemy.exc import IntegrityError

        user2 = User(telegram_id=111111111, name="User 2")
        test_session.add(user2)

        with pytest.raises(IntegrityError):
            await test_session.commit()

    async def test_user_messages_relationship(self, test_session, user):
        """Проверка связи пользователя с сообщениями."""
        message = Message(user_id=user.id, role="user", content="Привет!")
        test_session.add(message)
        await test_session.commit()

        # Используем select для получения сообщений пользователя
        from sqlalchemy import select
        result = await test_session.execute(
            select(Message).where(Message.user_id == user.id)
        )
        messages = result.scalars().all()
        assert len(messages) == 1
        assert messages[0].content == "Привет!"


class TestMessageModel:
    """Тесты для модели Message."""

    @pytest_asyncio.fixture
    async def user(self, test_session):
        """Создает тестового пользователя."""
        user = User(telegram_id=123456789, name="Test User")
        test_session.add(user)
        await test_session.commit()
        return user

    async def test_create_message(self, test_session, user):
        """Проверка создания сообщения."""
        message = Message(user_id=user.id, role="user", content="Тестовое сообщение")
        test_session.add(message)
        await test_session.commit()

        assert message.id is not None
        assert message.role == "user"
        assert message.content == "Тестовое сообщение"
        assert message.user_id == user.id

    async def test_message_user_relationship(self, test_session, user):
        """Проверка связи сообщения с пользователем."""
        message = Message(user_id=user.id, role="assistant", content="Ответ бота")
        test_session.add(message)
        await test_session.commit()

        await test_session.refresh(message)
        assert message.user is not None
        assert message.user.telegram_id == 123456789


class TestOrmQueries:
    """Тесты для ORM запросов."""

    async def test_get_or_create_user_new(self, test_session):
        """Проверка создания нового пользователя."""
        user = await get_or_create_user(test_session, telegram_id=999999999, name="New User")

        assert user is not None
        assert user.telegram_id == 999999999
        assert user.name == "New User"

    async def test_get_or_create_user_existing(self, test_session):
        """Проверка получения существующего пользователя."""
        # Создаем пользователя
        user1 = await get_or_create_user(test_session, telegram_id=888888888, name="First Name")

        # Получаем того же пользователя
        user2 = await get_or_create_user(test_session, telegram_id=888888888, name="Updated Name")

        # Должен вернуться тот же пользователь
        assert user1.id == user2.id
        # Имя может обновиться (зависит от реализации)
        assert user2.telegram_id == 888888888

    async def test_add_message(self, test_session):
        """Проверка добавления сообщения."""
        user = await get_or_create_user(test_session, telegram_id=777777777, name="Test User")

        message = await add_message(test_session, user, role="user", content="Сообщение для теста")

        assert message is not None
        assert message.role == "user"
        assert message.content == "Сообщение для теста"

    async def test_get_last_messages(self, test_session):
        """Проверка получения последних сообщений."""
        user = await get_or_create_user(test_session, telegram_id=666666666, name="Test User")

        # Добавляем несколько сообщений
        for i in range(5):
            await add_message(
                test_session,
                user,
                role="user" if i % 2 == 0 else "assistant",
                content=f"Сообщение {i}",
            )

        messages = await get_last_messages(test_session, user, limit=3)

        assert len(messages) == 3
        # Проверяем формат
        for msg in messages:
            assert "role" in msg
            assert "content" in msg

    async def test_get_last_messages_empty(self, test_session):
        """Проверка получения сообщений когда их нет."""
        user = await get_or_create_user(test_session, telegram_id=555555555, name="Test User")

        messages = await get_last_messages(test_session, user, limit=10)

        assert messages == []

    async def test_get_last_messages_with_context(self, test_session):
        """Проверка получения сообщений с контекстом."""
        user = await get_or_create_user(test_session, telegram_id=444444444, name="Test User")

        # Добавляем сообщения
        await add_message(test_session, user, "user", "Первое")
        await add_message(test_session, user, "assistant", "Ответ 1")
        await add_message(test_session, user, "user", "Второе")

        messages = await get_last_messages(test_session, user, limit=10)

        # Должны вернуться все сообщения в правильном формате
        assert len(messages) == 3
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Первое"
