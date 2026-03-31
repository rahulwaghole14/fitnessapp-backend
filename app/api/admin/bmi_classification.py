from fastapi import HTTPException, status, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from math import ceil
from datetime import datetime

from app.core.database import get_db
from app.models.bmi_classification import BMIClassification
from app.api.admin.schemas import BMIClassificationCreate, BMIClassificationResponse, BMIClassificationUpdate
from app.api.admin.dependencies import get_current_active_admin
from app.models.admin import Admin


def create_bmi_classification(
    bmi_data: BMIClassificationCreate,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_active_admin)
) -> BMIClassificationResponse:
    """
    Create a new BMI classification category.
    """
    # Check if category name already exists
    existing_category = db.query(BMIClassification).filter(
        BMIClassification.category_name == bmi_data.category_name
    ).first()
    
    if existing_category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="BMI category with this name already exists"
        )
    
    # Check for overlapping BMI ranges
    if bmi_data.min_bmi is not None or bmi_data.max_bmi is not None:
        overlapping_categories = db.query(BMIClassification).filter(
            (
                (BMIClassification.min_bmi <= bmi_data.max_bmi) if bmi_data.max_bmi is not None else False
            ) &
            (
                (BMIClassification.max_bmi >= bmi_data.min_bmi) if bmi_data.min_bmi is not None else False
            )
        ).all()
        
        if overlapping_categories:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="BMI range overlaps with existing categories"
            )
    
    bmi_classification = BMIClassification(
        category_name=bmi_data.category_name,
        min_bmi=bmi_data.min_bmi,
        max_bmi=bmi_data.max_bmi
    )
    
    db.add(bmi_classification)
    db.commit()
    db.refresh(bmi_classification)
    
    return BMIClassificationResponse(
        id=bmi_classification.id,
        category_name=bmi_classification.category_name,
        min_bmi=bmi_classification.min_bmi,
        max_bmi=bmi_classification.max_bmi,
        created_at=bmi_classification.created_at or datetime.utcnow()
    )


def get_bmi_classifications_paginated(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(10, ge=1, le=1000, description="Maximum records to return"),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_active_admin)
) -> dict:
    """
    Get all BMI classifications with pagination.
    """
    # Get total count for pagination metadata
    total_count = db.query(BMIClassification).count()
    
    # Apply pagination
    bmi_classifications = db.query(BMIClassification).offset(skip).limit(limit).all()
    
    # Convert SQLAlchemy objects to Pydantic response models
    bmi_classification_responses = []
    for bmi in bmi_classifications:
        bmi_response = BMIClassificationResponse(
            id=bmi.id,
            category_name=bmi.category_name,
            min_bmi=bmi.min_bmi,
            max_bmi=bmi.max_bmi,
            created_at=bmi.created_at or datetime.utcnow()
        )
        bmi_classification_responses.append(bmi_response)
    
    # Calculate pagination metadata
    total_pages = ceil(total_count / limit)
    current_page = skip // limit + 1
    
    return {
        "bmi_classifications": bmi_classification_responses,
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


def get_bmi_classification_by_id(
    bmi_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_active_admin)
) -> BMIClassificationResponse:
    """
    Get a specific BMI classification by ID.
    """
    bmi_classification = db.query(BMIClassification).filter(BMIClassification.id == bmi_id).first()
    
    if not bmi_classification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="BMI classification not found"
        )
    
    return BMIClassificationResponse(
        id=bmi_classification.id,
        category_name=bmi_classification.category_name,
        min_bmi=bmi_classification.min_bmi,
        max_bmi=bmi_classification.max_bmi,
        created_at=bmi_classification.created_at or datetime.utcnow()
    )


def update_bmi_classification(
    bmi_id: int,
    bmi_data: BMIClassificationUpdate,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_active_admin)
) -> BMIClassificationResponse:
    """
    Update an existing BMI classification.
    """
    bmi_classification = db.query(BMIClassification).filter(BMIClassification.id == bmi_id).first()
    
    if not bmi_classification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="BMI classification not found"
        )
    
    # Check if category name already exists (if being updated)
    if bmi_data.category_name and bmi_data.category_name != bmi_classification.category_name:
        existing_category = db.query(BMIClassification).filter(
            BMIClassification.category_name == bmi_data.category_name,
            BMIClassification.id != bmi_id
        ).first()
        
        if existing_category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="BMI category with this name already exists"
            )
    
    # Check for overlapping BMI ranges (if being updated)
    min_bmi = bmi_data.min_bmi if bmi_data.min_bmi is not None else bmi_classification.min_bmi
    max_bmi = bmi_data.max_bmi if bmi_data.max_bmi is not None else bmi_classification.max_bmi
    
    if (bmi_data.min_bmi is not None or bmi_data.max_bmi is not None) and (min_bmi is not None or max_bmi is not None):
        overlapping_categories = db.query(BMIClassification).filter(
            BMIClassification.id != bmi_id,
            (
                (BMIClassification.min_bmi <= max_bmi) if max_bmi is not None else False
            ) &
            (
                (BMIClassification.max_bmi >= min_bmi) if min_bmi is not None else False
            )
        ).all()
        
        if overlapping_categories:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="BMI range overlaps with existing categories"
            )
    
    # Update fields
    if bmi_data.category_name is not None:
        bmi_classification.category_name = bmi_data.category_name
    if bmi_data.min_bmi is not None:
        bmi_classification.min_bmi = bmi_data.min_bmi
    if bmi_data.max_bmi is not None:
        bmi_classification.max_bmi = bmi_data.max_bmi
    
    db.commit()
    db.refresh(bmi_classification)
    
    return BMIClassificationResponse(
        id=bmi_classification.id,
        category_name=bmi_classification.category_name,
        min_bmi=bmi_classification.min_bmi,
        max_bmi=bmi_classification.max_bmi,
        created_at=bmi_classification.created_at or datetime.utcnow()
    )


def delete_bmi_classification(
    bmi_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_active_admin)
) -> dict:
    """
    Delete a BMI classification.
    """
    bmi_classification = db.query(BMIClassification).filter(BMIClassification.id == bmi_id).first()
    
    if not bmi_classification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="BMI classification not found"
        )
    
    # Check if there are any meals associated with this BMI category
    from app.models.meal import Meal
    associated_meals = db.query(Meal).filter(Meal.bmi_category_id == bmi_id).count()
    
    if associated_meals > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete BMI category. {associated_meals} meal(s) are associated with this category."
        )
    
    db.delete(bmi_classification)
    db.commit()
    
    return {"message": "BMI classification deleted successfully"}
