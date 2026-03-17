from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth_dependencies import get_current_user
from app.models.workout import Workout
from app.models.user import User
from app.schemas.workout import WorkoutListResponse

router = APIRouter()

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
