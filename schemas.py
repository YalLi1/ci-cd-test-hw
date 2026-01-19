from pydantic import BaseModel, Field
from typing import List

class IngredientBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, example="Мясо")
    quantity: str = Field(..., min_length=1, max_length=100, example="250 г")


class IngredientCreate(IngredientBase):
    pass


class IngredientResponse(IngredientBase):
    id: int

    class Config:
        from_attributes = True


class RecipeBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, example="Борщ")
    cooking_time: int = Field(..., gt=0, example=60)
    description: str = Field(..., min_length=10, example="Традиционный украинский суп...")


class RecipeCreate(RecipeBase):
    ingredients: List[IngredientCreate]


class RecipeListResponse(BaseModel):
    id: int
    title: str
    cooking_time: int
    views: int

    class Config:
        from_attributes = True


class RecipeDetailResponse(RecipeBase):
    id: int
    views: int
    ingredients: List[IngredientResponse]

    class Config:
        from_attributes = True