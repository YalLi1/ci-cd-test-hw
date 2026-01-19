from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.ext.asyncio import (AsyncSession,
                                    create_async_engine, async_sessionmaker)
from sqlalchemy.orm import relationship, DeclarativeBase
from typing import AsyncGenerator


# Создаем базовый класс для моделей
class Base(DeclarativeBase):
    """Base class for all models"""
    pass


class Recipe(Base):
    """
    Модель рецепта в базе данных.
    """
    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    cooking_time = Column(Integer, nullable=False)
    description = Column(Text, nullable=False)
    views = Column(Integer, default=0, nullable=False)

    # Связь один-ко-многим с ингредиентами
    ingredients = relationship(
        "Ingredient", back_populates="recipe", cascade="all, delete-orphan")


class Ingredient(Base):
    """
    Модель ингредиента в базе данных.
    """
    __tablename__ = "ingredients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    quantity = Column(String(100), nullable=False)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)

    # Обратная связь с рецептом
    recipe = relationship("Recipe", back_populates="ingredients")


# Используем async версию SQLite
DATABASE_URL = "sqlite+aiosqlite:///./cookbook.db"

# Создаем асинхронный движок
engine = create_async_engine(
    DATABASE_URL,
    echo=True,  # Показывать SQL запросы в консоли (можно отключить)
    future=True
)

# Создаем асинхронную фабрику сессий
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def create_tables():
    """
    Асинхронное создание таблиц в базе данных.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Асинхронный генератор сессий базы данных.

    Yields:
        AsyncSession: Асинхронная сессия SQLAlchemy
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()  # Commit success transfer
        except Exception:
            await session.rollback()  # Откатываем при ошибке
            raise
        finally:
            await session.close()
