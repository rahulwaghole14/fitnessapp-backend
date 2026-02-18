from fastapi import Depends, Query, UploadFile, File, Form, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, List
from math import ceil
from datetime import datetime
import os

from app.models.workout import Workout
from app.models.admin import Admin
from app.core.database import get_db
from app.services.workout_media_service import WorkoutMediaService
from .dependencies import get_current_admin
from .schemas import (
    WorkoutResponse, WorkoutCreate, WorkoutUpdate, PaginatedResponse, PaginationInfo
)

# Initialize media service
media_service = WorkoutMediaService()

async def create_workout(
        title: str = Form(...),
        description: str = Form(...),
        duration: int = Form(...),
        calorie_burn: int = Form(...),
        activity_level: str = Form(...),
        workout_category: str = Form(...),
        workout_image: Optional[UploadFile] = File(None),
        workout_video: Optional[UploadFile] = File(None),
        db: Session = Depends(get_db)
):

    # Validate activity_level
    if activity_level not in ["beginner", "intermediate", "advanced"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="activity_level must be one of: beginner, intermediate, advanced"
        )

    # Validate workout_category
    if workout_category not in ["gain", "loose", "maintain"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="workout_category must be one of: gain, loose, maintain"
        )

    # Create workout record first without media URLs
    workout_data = {
        "title": title,
        "description": description,
        "duration": duration,
        "calorie_burn": calorie_burn,
        "activity_level": activity_level,
        "workout_category": workout_category,
        "workout_image_url": "",  # Temporary placeholder
        "workout_video_url": ""  # Temporary placeholder
    }

    db_workout = Workout(**workout_data)
    db.add(db_workout)
    db.commit()
    db.refresh(db_workout)

    try:
        # Save media files using the generated workout ID
        image_path, video_path = await media_service.save_workout_media(
            image_file=workout_image,
            video_file=workout_video,
            workout_id=db_workout.id,
            workout_title=title
        )

        # Update workout record with file paths
        db_workout.workout_image_url = image_path or ""
        db_workout.workout_video_url = video_path or ""
        db.commit()
        db.refresh(db_workout)

        return WorkoutResponse(
            id=db_workout.id,
            name=db_workout.title,
            description=db_workout.description,
            duration_minutes=db_workout.duration,
            calories_burned=db_workout.calorie_burn,
            difficulty_level=db_workout.activity_level,
            category=db_workout.workout_category,
            workout_image_url=db_workout.workout_image_url.replace("app/", "/") if db_workout.workout_image_url else None,
            workout_video_url=db_workout.workout_video_url.replace("app/", "/") if db_workout.workout_video_url else None,
            created_at=db_workout.created_at or datetime.utcnow()
        )

    except Exception as e:
        # Rollback on error
        db.rollback()
        # Clean up any created media files
        if image_path:
            media_service.delete_old_workout_media(image_path, None)
        if video_path:
            media_service.delete_old_workout_media(None, video_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save workout media: {str(e)}"
        )


async def get_workouts_paginated(
        search: Optional[str] = Query(None, description="Search term for title or description"),
        category: Optional[str] = Query(None, description="Filter by workout category"),
        difficulty_level: Optional[str] = Query(None, description="Filter by difficulty level"),
        db: Session = Depends(get_db),
        current_admin: Admin = Depends(get_current_admin)
) -> List[WorkoutResponse]:

    # Build query
    query = db.query(Workout)

    # Apply filters
    if search:
        query = query.filter(
            or_(
                Workout.title.ilike(f"%{search}%"),
                Workout.description.ilike(f"%{search}%")
            )
        )

    if category:
        query = query.filter(Workout.workout_category == category)

    if difficulty_level:
        query = query.filter(Workout.activity_level == difficulty_level)

    # Get all results (no pagination)
    workouts = query.all()

    # Convert workouts to response format
    workout_responses = []
    for workout in workouts:
        workout_response = WorkoutResponse(
            id=workout.id,
            name=workout.title,
            description=workout.description,
            duration_minutes=workout.duration,
            calories_burned=workout.calorie_burn,
            difficulty_level=workout.activity_level,
            category=workout.workout_category,
            workout_image_url=workout.workout_image_url.replace("app/", "/") if workout.workout_image_url else None,
            workout_video_url=workout.workout_video_url.replace("app/", "/") if workout.workout_video_url else None,
            created_at=workout.created_at or datetime.utcnow()
        )
        workout_responses.append(workout_response)

    return workout_responses


async def get_workout_by_id(
        workout_id: int,
        db: Session = Depends(get_db),
        current_admin: Admin = Depends(get_current_admin)
) -> Optional[WorkoutResponse]:

    workout = db.query(Workout).filter(Workout.id == workout_id).first()

    if not workout:
        return None

    return WorkoutResponse(
        id=workout.id,
        name=workout.title,
        description=workout.description,
        duration_minutes=workout.duration,
        calories_burned=workout.calorie_burn,
        difficulty_level=workout.activity_level,
        category=workout.workout_category,
        workout_image_url=workout.workout_image_url.replace("app/", "/") if workout.workout_image_url else None,
        workout_video_url=workout.workout_video_url.replace("app/", "/") if workout.workout_video_url else None,
        created_at=workout.created_at or datetime.utcnow()
    )


async def update_workout(
        workout_id: int,
        title: Optional[str] = Form(None),
        description: Optional[str] = Form(None),
        duration: Optional[int] = Form(None),
        calorie_burn: Optional[int] = Form(None),
        activity_level: Optional[str] = Form(None),
        workout_category: Optional[str] = Form(None),
        workout_image: Optional[UploadFile] = File(None),
        workout_video: Optional[UploadFile] = File(None),
        db: Session = Depends(get_db),
        current_admin: Admin = Depends(get_current_admin)
) -> Optional[WorkoutResponse]:

    workout = db.query(Workout).filter(Workout.id == workout_id).first()

    if not workout:
        return None

    # Store old media paths for cleanup
    old_image_path = workout.workout_image_url
    old_video_path = workout.workout_video_url

    # Update text fields if provided
    if title is not None:
        workout.title = title
    if description is not None:
        workout.description = description
    if duration is not None:
        workout.duration = duration
    if calorie_burn is not None:
        workout.calorie_burn = calorie_burn
    if activity_level is not None:
        if activity_level not in ["beginner", "intermediate", "advanced"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="activity_level must be one of: beginner, intermediate, advanced"
            )
        workout.activity_level = activity_level
    if workout_category is not None:
        if workout_category not in ["gain", "loose", "maintain"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="workout_category must be one of: gain, loose, maintain"
            )
        workout.workout_category = workout_category

    try:
        # Handle media file updates if provided
        if workout_image or workout_video:
            new_image_path, new_video_path = await media_service.save_workout_media(
                image_file=workout_image,
                video_file=workout_video,
                workout_id=workout.id,
                workout_title=workout.title
            )

            # Update workout with new media paths
            if new_image_path is not None:
                workout.workout_image_url = new_image_path
            if new_video_path is not None:
                workout.workout_video_url = new_video_path

            # Clean up old media files
            if old_image_path and new_image_path:
                media_service.delete_old_workout_media(old_image_path, None)
            if old_video_path and new_video_path:
                media_service.delete_old_workout_media(None, old_video_path)

        db.commit()
        db.refresh(workout)

        return WorkoutResponse(
            id=workout.id,
            name=workout.title,
            description=workout.description,
            duration_minutes=workout.duration,
            calories_burned=workout.calorie_burn,
            difficulty_level=workout.activity_level,
            category=workout.workout_category,
            workout_image_url=workout.workout_image_url.replace("app/", "/") if workout.workout_image_url else None,
            workout_video_url=workout.workout_video_url.replace("app/", "/") if workout.workout_video_url else None,
            created_at=workout.created_at or datetime.utcnow()
        )

    except Exception as e:
        # Rollback on error
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update workout: {str(e)}"
        )


async def delete_workout(
        workout_id: int,
        db: Session = Depends(get_db),
        current_admin: Admin = Depends(get_current_admin)
) -> dict:

    workout = db.query(Workout).filter(Workout.id == workout_id).first()

    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout not found"
        )

    # Store media paths for cleanup
    image_path = workout.workout_image_url
    video_path = workout.workout_video_url

    # Delete workout from database
    db.delete(workout)
    db.commit()

    # Clean up media files
    try:
        if image_path:
            media_service.delete_old_workout_media(image_path, None)
        if video_path:
            media_service.delete_old_workout_media(None, video_path)
    except Exception as e:
        # Log error but don't fail the deletion
        print(f"Warning: Failed to cleanup media files: {e}")

    return {"message": f"Workout with ID {workout_id} deleted successfully"}
