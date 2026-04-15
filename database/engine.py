import logging
import os

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from database.models import Base

logger = logging.getLogger("ai_bot.database.engine")

load_dotenv()

DB_URL = os.getenv("DB_URL")
if not DB_URL:
    raise RuntimeError("DB_URL not found in environment. Fill .env from .env.example")
engine = create_async_engine(DB_URL, echo=False, future=True)

session_maker = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)


async def create_db():
    async with engine.begin() as conn:
        logger.info("Creating tables...")
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Tables created successfully")


async def drop_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
