from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Message, User


async def get_or_create_user(
    session: AsyncSession, telegram_id: int, name: str | None = None
) -> User:
    # 1. Пытаемся получить юзера
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()

    if user:
        return user

    # 2. Создаём пользователя
    user = User(telegram_id=telegram_id, name=name)
    session.add(user)

    # Коммитим и обновляем
    await session.commit()
    await session.refresh(user)

    return user


async def add_message(session: AsyncSession, user: User, role: str, content: str):
    message = Message(user_id=user.id, role=role, content=content)
    session.add(message)
    await session.commit()
    return message


async def get_last_messages(session: AsyncSession, user: User, limit: int = 20):
    result = await session.execute(
        select(Message)
        .where(Message.user_id == user.id)
        .order_by(Message.id.desc())
        .limit(limit)
    )

    messages = result.scalars().all()

    # Возвращаем в порядке стар→нов
    return [{"role": m.role, "content": m.content} for m in reversed(messages)]
