from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.core.auth_dependencies import get_current_user
from app.models.workout import Workout
from app.models.user import User
from app.schemas.workout import WorkoutCreate, WorkoutResponse, WorkoutListResponse
from app.services.workout_media_service import WorkoutMediaService

router = APIRouter()

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
        "workout_video_url": ""   # Temporary placeholder
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

        return db_workout

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


def get_workouts_for_user(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):

    # Validate user has required fields
    if not all([current_user.weight, current_user.weight_goal, current_user.activity_level]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User profile incomplete. Missing weight, weight_goal, or activity_level"
        )   

    # Validate user activity_level
    if current_user.activity_level not in ["beginner", "intermediate", "advanced"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user activity_level"
        )

    # Determine workout category based on weight vs weight_goal
    if current_user.weight < current_user.weight_goal:
        workout_category = "gain"
    elif current_user.weight > current_user.weight_goal:
        workout_category = "loose"
    else:
        workout_category = "maintain"

    # Query workouts based on user's activity_level and calculated category
    # query = db.query(Workout).filter(Workout.activity_level == user.activity_level)
    query = db.query(Workout)

    if workout_category:
        query = query.filter(Workout.workout_category == workout_category)

    workouts = query.all()

    # Convert file paths to accessible URLs
    for workout in workouts:
        if workout.workout_image_url:
            workout.workout_image_url = workout.workout_image_url.replace("app/", "/", 1)
        if workout.workout_video_url:
            workout.workout_video_url = workout.workout_video_url.replace("app/", "/", 1)

    return WorkoutListResponse(workouts=workouts)
