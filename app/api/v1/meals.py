from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List

from app.core.database import get_db
from app.core.auth_dependencies import get_current_user, get_current_user_id
from app.models import User
from app.models.bmi_classification import BMIClassification
from app.models.meal import Meal

router = APIRouter()


def get_meals_by_user_bmi(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):

    # Determine BMI value to use
    if current_user.bmi is None:
        bmi_value = 21.75  # Middle of Normal range (18.5-25)
    else:
        bmi_value = current_user.bmi

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
