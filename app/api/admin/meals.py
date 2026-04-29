from fastapi import Depends, Query, UploadFile, File, Form
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
from app.services.meal_image_service import MealImageService


async def create_meal(
        bmi_category_id: int = Form(...),
        meal_type: str = Form(...),
        food_item: str = Form(...),
        calories: int = Form(...),
        description: Optional[str] = Form(None),
        image: Optional[UploadFile] = File(None),
        db: Session = Depends(get_db),
        current_admin: Admin = Depends(get_current_admin)
) -> MealResponse:

    # Handle image upload if provided
    meal_image_url = None
    if image and image.filename:
        image_service = MealImageService()
        meal_image_url = await image_service.save_meal_image(image)

    # Create meal instance
    new_meal = Meal(
        bmi_category_id=bmi_category_id,
        meal_type=meal_type,
        food_item=food_item,
        calories=calories,
        description=description,
        meal_image=meal_image_url
        )

    db.add(new_meal)
    db.commit()
    db.refresh(new_meal)

    return MealResponse(
        id=new_meal.id,
        bmi_category_id=new_meal.bmi_category_id,
        meal_type=new_meal.meal_type,
        food_item=new_meal.food_item,
        calories=new_meal.calories,
        description=new_meal.description,
        meal_image=new_meal.meal_image,
        created_at=new_meal.created_at
    )


async def get_meals_paginated(
        skip: int = Query(0, ge=0, description="Number of records to skip"),
        limit: int = Query(10, ge=1, le=1000, description="Maximum records to return"),
        search: Optional[str] = Query(None, description="Search term for food item"),
        meal_type: Optional[str] = Query(None, description="Filter by meal type"),
        min_calories: Optional[int] = Query(None, description="Filter by minimum calories"),
        max_calories: Optional[int] = Query(None, description="Filter by maximum calories"),
        db: Session = Depends(get_db),
        current_admin: Admin = Depends(get_current_admin)
) -> dict:

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

    # Get total count for pagination metadata
    total_count = query.count()

    # Apply pagination
    meals = query.offset(skip).limit(limit).all()

    # Convert meals to response format
    meal_responses = []
    for meal in meals:
        meal_response = MealResponse(
            id=meal.id,
            bmi_category_id=meal.bmi_category_id,
            meal_type=meal.meal_type,
            food_item=meal.food_item,
            calories=meal.calories,
            description=meal.description,
            meal_image=meal.meal_image,
            created_at=meal.created_at
        )
        meal_responses.append(meal_response)

    # Calculate pagination metadata
    total_pages = ceil(total_count / limit)
    current_page = skip // limit + 1

    return {
        "meals": meal_responses,
        "pagination": {
            "current_page": current_page,
            "page_size": limit,
            "total_items": total_count,
            "total_pages": total_pages,
            "has_next": current_page < total_pages,
            "has_prev": current_page > 1,
            "next_skip": skip + limit if current_page < total_pages else None,
            "prev_skip": skip - limit if current_page > 1 else None
        }
    }


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
        calories=meal.calories,
        description=meal.description,
        meal_image=meal.meal_image,
        created_at=meal.created_at
    )


async def update_meal(
        meal_id: int,
        food_item: Optional[str] = Form(None),
        calories: Optional[int] = Form(None),
        meal_type: Optional[str] = Form(None),
        bmi_category_id: Optional[int] = Form(None),
        description: Optional[str] = Form(None),
        image: Optional[UploadFile] = File(None),
        db: Session = Depends(get_db),
        current_admin: Admin = Depends(get_current_admin)
) -> Optional[MealResponse]:

    meal = db.query(Meal).filter(Meal.id == meal_id).first()

    if not meal:
        return None

    # Handle image upload if provided
    if image and image.filename:
        image_service = MealImageService()
        # Delete old image if exists
        if meal.meal_image:
            image_service.delete_old_meal_image(meal.meal_image)
        # Upload new image
        meal.meal_image = await image_service.save_meal_image(image, meal_id)

    # Update other fields if provided
    if food_item is not None:
        meal.food_item = food_item
    if calories is not None:
        meal.calories = calories
    if meal_type is not None:
        meal.meal_type = meal_type
    if bmi_category_id is not None:
        meal.bmi_category_id = bmi_category_id
    if description is not None:
        meal.description = description

    db.commit()
    db.refresh(meal)

    return MealResponse(
        id=meal.id,
        bmi_category_id=meal.bmi_category_id,
        meal_type=meal.meal_type,
        food_item=meal.food_item,
        calories=meal.calories,
        description=meal.description,
        meal_image=meal.meal_image,
        created_at=meal.created_at
    )


async def delete_meal(
        meal_id: int,
        db: Session = Depends(get_db),
        current_admin: Admin = Depends(get_current_admin)
) -> dict:

    meal = db.query(Meal).filter(Meal.id == meal_id).first()

    if not meal:
        return False

    # Delete meal image from Cloudinary if it exists
    if meal.meal_image:
        image_service = MealImageService()
        image_service.delete_old_meal_image(meal.meal_image)

    db.delete(meal)
    db.commit()

    return {"message": f"Meal with ID {meal_id} deleted successfully"}
