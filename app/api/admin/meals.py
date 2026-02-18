from fastapi import Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, List
from math import ceil
from datetime import datetime

from app.models.meal import Meal
from app.models.admin import Admin
from app.core.database import get_db
from .dependencies import get_current_admin
from .schemas import (
    MealResponse, MealCreate, MealUpdate, PaginatedResponse, PaginationInfo
)


async def create_meal(
        meal_data: MealCreate,
        db: Session = Depends(get_db),
        current_admin: Admin = Depends(get_current_admin)
) -> MealResponse:

    # Create meal instance
    new_meal = Meal(
        bmi_category_id=meal_data.bmi_category_id,
        meal_type=meal_data.meal_type,
        food_item=meal_data.food_item,
        calories=meal_data.calories,
        )

    db.add(new_meal)
    db.commit()
    db.refresh(new_meal)

    return MealResponse(
        id=new_meal.id,
        bmi_category_id=new_meal.bmi_category_id,
        meal_type=new_meal.meal_type,
        food_item=new_meal.food_item,
        calories=new_meal.calories
    )


async def get_meals_paginated(
        search: Optional[str] = Query(None, description="Search term for food item"),
        meal_type: Optional[str] = Query(None, description="Filter by meal type"),
        min_calories: Optional[int] = Query(None, description="Filter by minimum calories"),
        max_calories: Optional[int] = Query(None, description="Filter by maximum calories"),
        db: Session = Depends(get_db),
        current_admin: Admin = Depends(get_current_admin)
) -> List[MealResponse]:

    # Build query
    query = db.query(Meal)

    # Apply filters
    if search:
        query = query.filter(Meal.food_item.ilike(f"%{search}%"))

    if meal_type:
        query = query.filter(Meal.meal_type == meal_type)

    if min_calories is not None:
        query = query.filter(Meal.calories >= min_calories)

    if max_calories is not None:
        query = query.filter(Meal.calories <= max_calories)

    # Get all results (no pagination)
    meals = query.all()

    # Convert meals to response format
    meal_responses = []
    for meal in meals:
        meal_response = MealResponse(
            id=meal.id,
            bmi_category_id=meal.bmi_category_id,
            meal_type=meal.meal_type,
            food_item=meal.food_item,
            calories=meal.calories
        )
        meal_responses.append(meal_response)

    return meal_responses


async def get_meal_by_id(
        meal_id: int,
        db: Session = Depends(get_db),
        current_admin: Admin = Depends(get_current_admin)
) -> Optional[MealResponse]:

    meal = db.query(Meal).filter(Meal.id == meal_id).first()

    if not meal:
        return None

    return MealResponse(
        id=meal.id,
        bmi_category_id=meal.bmi_category_id,
        meal_type=meal.meal_type,
        food_item=meal.food_item,
        calories=meal.calories
    )


async def update_meal(
        meal_id: int,
        meal_data: MealUpdate,
        db: Session = Depends(get_db),
        current_admin: Admin = Depends(get_current_admin)
) -> Optional[MealResponse]:

    meal = db.query(Meal).filter(Meal.id == meal_id).first()

    if not meal:
        return None

    # Update fields that are provided
    update_data = meal_data.model_dump(exclude_unset=True)

    # Map schema fields to model fields
    if 'name' in update_data:
        meal.food_item = update_data['name']

    if 'calories' in update_data:
        meal.calories = update_data['calories']

    if 'meal_type' in update_data:
        meal.meal_type = update_data['meal_type']

    if 'bmi_category_id' in update_data:
        meal.bmi_category_id = update_data['bmi_category_id']


    db.commit()
    db.refresh(meal)

    return MealResponse(
        id=meal.id,
        bmi_category_id=meal.bmi_category_id,
        meal_type=meal.meal_type,
        food_item=meal.food_item,
        calories=meal.calories
    )


async def delete_meal(
        meal_id: int,
        db: Session = Depends(get_db),
        current_admin: Admin = Depends(get_current_admin)
) -> dict:

    meal = db.query(Meal).filter(Meal.id == meal_id).first()

    if not meal:
        return False

    db.delete(meal)
    db.commit()

    return {"message": f"Meal with ID {meal_id} deleted successfully"}
