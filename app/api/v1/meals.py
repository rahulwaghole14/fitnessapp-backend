from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth_dependencies import get_current_user
from app.models import User
from app.schemas.meal import MealPlanResponse
from app.services.meal_service import MealService

router = APIRouter()


def get_meals_by_user_bmi(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> MealPlanResponse:
    """Generate a calorie-targeted BMI-based daily meal plan for the current user."""
    return MealService.generate_meal_plan(db, current_user)

