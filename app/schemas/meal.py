from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class MealBase(BaseModel):
    bmi_category_id: int
    meal_type: str  # breakfast, lunch, dinner
    food_item: str
    calories: int
    description: Optional[str] = None
    meal_image: Optional[str] = None


class MealCreate(MealBase):
    pass


class MealResponse(MealBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class MealWithCategory(MealResponse):
    bmi_category: Optional[dict] = None


class MealPlanSection(BaseModel):
    target_calories: int
    actual_calories: int
    meals: List[MealResponse]


class MealPlanResponse(BaseModel):
    bmi_category: str
    daily_target_calories: int
    breakfast: MealPlanSection
    lunch: MealPlanSection
    dinner: MealPlanSection
    total_actual_calories: int

    class Config:
        from_attributes = True

