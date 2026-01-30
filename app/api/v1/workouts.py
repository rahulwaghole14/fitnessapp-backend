from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.models.workout import Workout
from app.models.user import User
from app.schemas.workout import WorkoutCreate, WorkoutResponse, WorkoutListResponse

router = APIRouter()

def create_workout(workout: WorkoutCreate, db: Session = Depends(get_db)):
    """
    Create a new workout with image and video URLs
    """
    # Validate activity_level
    if workout.activity_level not in ["beginner", "intermediate", "advanced"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="activity_level must be one of: beginner, intermediate, advanced"
        )

    # Validate workout_category
    if workout.workout_category not in ["gain", "loose", "maintain"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="workout_category must be one of: gain, loose, maintain"
        )

    # Create workout
    db_workout = Workout(**workout.dict())
    db.add(db_workout)
    db.commit()
    db.refresh(db_workout)

    return db_workout


def get_workouts_for_user(user_id: int, db: Session = Depends(get_db)):
    """
    Get workouts tailored for a specific user based on their profile
    """
    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Validate user has required fields
    if not all([user.weight, user.weight_goal, user.activity_level]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User profile incomplete. Missing weight, weight_goal, or activity_level"
        )

    # Validate user activity_level
    if user.activity_level not in ["beginner", "intermediate", "advanced"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user activity_level"
        )

    # Determine workout category based on weight vs weight_goal
    if user.weight < user.weight_goal:
        workout_category = "gain"
    elif user.weight > user.weight_goal:
        workout_category = "loose"
    else:
        workout_category = "maintain"

    # Query workouts based on user's activity_level and calculated category
    query = db.query(Workout).filter(Workout.activity_level == user.activity_level)

    if workout_category:
        query = query.filter(Workout.workout_category == workout_category)

    workouts = query.all()

    return WorkoutListResponse(workouts=workouts)
