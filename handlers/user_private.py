from aiogram import F, types, Router
from aiogram.filters import CommandStart

from database.orm_query import add_message, get_last_messages, get_or_create_user
from ai_engine.general_engine import ask_ai_engine
from sqlalchemy.ext.asyncio import AsyncSession


user_private_router = Router()

@user_private_router.message(CommandStart())
async def start_cmd(message: types.Message, session: AsyncSession):
    user = await get_or_create_user(
        session,
        telegram_id=message.from_user.id,
        name=message.from_user.full_name
        )
    

    await message.answer(
        "Привет! Я бот AI-бот, я могу придумывать идеи, писать тексты и генерировать контент."
        )


@user_private_router.message(F.text)
async def handle_user_message(message: types.Message, session: AsyncSession):

    # 1. Получаем пользователя
    user = await get_or_create_user(
        session,
        telegram_id=message.from_user.id,
        name=message.from_user.full_name
    )

    # 2. Забираем историю (включая контекст)
    history = await get_last_messages(session, user, limit=10)

    # 3. Добавляем новое сообщение пользователя
    user_message = {"role": "user", "content": message.text}
    history.append(user_message)

    # 4. Сохраняем сообщение в БД
    await add_message(session, user, "user", message.text)

    # 5. Отправляем историю в ИИ
    ai_answer = await ask_ai_engine(history)

    # 6. Записываем ответ
    await add_message(session, user, "assistant", ai_answer)

    # 7. Отправляем пользователю
    await message.answer(ai_answer)
    
