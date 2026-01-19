from contextlib import asynccontextmanager
from typing import Any, Dict, List

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import Ingredient, Recipe, create_tables, get_db
from schemas import RecipeCreate, RecipeDetailResponse, RecipeListResponse


# Перед запуском приложения выполняется создание таблиц (замена event_start)
@asynccontextmanager
async def lifespan(app: FastAPI):

    print("=" * 40)
    print("🍳 Запуск Кулинарной книги API...")

    # Создаем таблицы при запуске
    await create_tables()
    print("✅ Таблицы базы данных созданы")
    print("=" * 40)

    yield  # Здесь приложение работает

    print("👋 Завершение работы...")


# Создаем приложение
app = FastAPI(
    title="Кулинарная книга API",
    description="API для управления рецептами",
    version="1.0.0",
    lifespan=lifespan,
)


# Стартовый endpoint
@app.get("/", summary="Главная страница")
async def read_root() -> Dict[str, Any]:
    """
    Главная страница API кулинарной книги.
    """
    return {
        "message": "Добро пожаловать в Кулинарную книгу!",
        "description": "API для управления вашими рецептами",
        "documentation": {"swagger": "/docs", "redoc": "/redoc"},
        "endpoints": [
            {
                "method": "GET",
                "path": "/recipes",
                "description": "Получить список всех рецептов",
            },
            {
                "method": "GET",
                "path": "/recipes/{id}",
                "description": "Получить детальную информацию о рецепте",
            },
            {
                "method": "POST",
                "path": "/recipes",
                "description": "Создать новый рецепт",
            },
        ],
    }


# Получение рецептов с сортировкой
@app.get(
    "/recipes",
    response_model=List[RecipeListResponse],
    summary="Получить список всех рецептов",
    description="Получает список всех рецептов, "
    "отсортированный по популярности и времени приготовления.",
)
async def get_all_recipes(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)
):
    """
    Получение списка всех рецептов.

    Args:
        skip: Количество рецептов для пропуска (пагинация)
        limit: Максимальное количество возвращаемых рецептов
        db: Асинхронная сессия базы данных

    Returns:
        Список рецептов с мета-информацией
    """
    # Получаем рецепты с сортировкой
    query = (
        select(Recipe)
        .order_by(desc(Recipe.views), Recipe.cooking_time)
        .offset(skip)
        .limit(limit)
    )

    result = await db.execute(query)
    recipes = result.scalars().all()

    # Преобразуем SQLAlchemy объекты в Pydantic модели
    return [RecipeListResponse.model_validate(recipe) for recipe in recipes]


# ========== GET /recipes/{id} - КОНКРЕТНЫЙ РЕЦЕПТ ==========
@app.get(
    "/recipes/{recipe_id}",
    response_model=RecipeDetailResponse,
    summary="Получить детальную информацию о рецепте",
    description="Получает рецепт по ID и увеличивает счетчик просмотров.",
)
async def get_recipe_by_id(recipe_id: int, db: AsyncSession = Depends(get_db)):
    """
    Получение рецепта по ID.

    Args:
        recipe_id: ID рецепта для поиска
        db: Асинхронная сессия базы данных

    Returns:
        Детальная информация о рецепте

    Raises:
        HTTPException: 404 если рецепт не найден
    """

    # Ищем рецепт с ингредиентами
    query = (
        select(Recipe)
        .options(selectinload(Recipe.ingredients))
        .where(Recipe.id == recipe_id)
    )

    result = await db.execute(query)
    recipe = result.scalar_one_or_none()

    # Если рецепт не найден
    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Рецепт с ID {recipe_id} не найден",
        )

    # Увеличиваем счетчик просмотров
    recipe.views += 1
    await db.commit()
    await db.refresh(recipe)

    # Преобразуем SQLAlchemy объект в Pydantic модель
    return RecipeDetailResponse.model_validate(recipe)


# ========== POST /recipes - СОЗДАТЬ РЕЦЕПТ ==========
@app.post(
    "/recipes",
    response_model=RecipeDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать новый рецепт",
    description="Создает новый рецепт с ингредиентами.",
)
async def create_recipe(
    recipe_data: RecipeCreate, db: AsyncSession = Depends(get_db)
):
    """
    Создание нового рецепта.

    Args:
        recipe_data: Данные для создания рецепта
        db: Асинхронная сессия базы данных

    Returns:
        Информация о созданном рецепте
    """

    # Создаем объект рецепта
    new_recipe = Recipe(
        title=recipe_data.title,
        cooking_time=recipe_data.cooking_time,
        description=recipe_data.description,
        views=0,
    )

    # Добавляем рецепт в базу
    db.add(new_recipe)
    await db.flush()  # Получаем ID рецепта

    # Добавляем ингредиенты
    for ingredient in recipe_data.ingredients:
        new_ingredient = Ingredient(
            name=ingredient.name,
            quantity=ingredient.quantity,
            recipe_id=new_recipe.id,
        )
        db.add(new_ingredient)

    # Сохраняем все изменения
    await db.commit()
    await db.refresh(new_recipe)

    # Загружаем ингредиенты для ответа
    await db.refresh(new_recipe, attribute_names=["ingredients"])

    # Преобразуем SQLAlchemy объект в Pydantic модель
    return RecipeDetailResponse.model_validate(new_recipe)


# ========== ЗАПУСК СЕРВЕРА ==========
if __name__ == "__main__":
    import uvicorn

    print("🚀 Сервер запускается...")
    print("📚 Документация: http://localhost:8000/docs")
    print("📖 ReDoc: http://localhost:8000/redoc")

    uvicorn.run(app, port=8000)
