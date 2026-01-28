from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List

from app.core.database import get_db
from app.models import User
from app.models.bmi_classification import BMIClassification
from app.models.meal import Meal
from app.schemas.meal import MealResponse, MealCreate
from app.schemas.bmi_classification import BMIClassificationCreate, BMIClassificationResponse
router = APIRouter()


def get_meals_by_user_bmi(user_id: int, db: Session = Depends(get_db)):
    """
    Get meals based on user's BMI.
    """
    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Determine BMI value to use
    if user.bmi is None:
        bmi_value = 21.75  # Middle of Normal range (18.5-25)
    else:
        bmi_value = user.bmi

    # Find BMI category
    bmi_category = db.query(BMIClassification).filter(
        or_(
            and_(BMIClassification.min_bmi <= bmi_value, BMIClassification.max_bmi >= bmi_value),
            and_(BMIClassification.min_bmi.is_(None), BMIClassification.max_bmi >= bmi_value),
            and_(BMIClassification.min_bmi <= bmi_value, BMIClassification.max_bmi.is_(None))
        )
    ).first()

    if not bmi_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No BMI category found for the calculated BMI"
        )

    # Get all meals for the BMI category
    meals = db.query(Meal).filter(Meal.bmi_category_id == bmi_category.id).all()

    return meals


def create_bmi_classification(
        bmi_data: BMIClassificationCreate,
        db: Session = Depends(get_db)
):
    """Create a new BMI classification."""
    bmi_classification = BMIClassification(**bmi_data.dict())
    db.add(bmi_classification)
    db.commit()
    db.refresh(bmi_classification)
    return bmi_classification


def create_meal(meal_data: MealCreate, db: Session = Depends(get_db)):
    """Create a new meal."""
    # Check if BMI category exists
    bmi_category = db.query(BMIClassification).filter(
        BMIClassification.id == meal_data.bmi_category_id
    ).first()

    if not bmi_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="BMI category not found"
        )

    meal = Meal(**meal_data.dict())
    db.add(meal)
    db.commit()
    db.refresh(meal)
    return meal
