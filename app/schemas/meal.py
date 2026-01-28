from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class MealBase(BaseModel):
    bmi_category_id: int
    meal_type: str  # breakfast, lunch, dinner
    food_item: str
    calories: int


class MealCreate(MealBase):
    pass


class MealResponse(MealBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class MealWithCategory(MealResponse):
    bmi_category: Optional[dict] = None
