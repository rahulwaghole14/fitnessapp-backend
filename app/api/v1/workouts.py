from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth_dependencies import get_current_user
from app.models.workout import Workout
from app.models.user import User
from app.schemas.workout import WorkoutListResponse, WorkoutResponse

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

    print(f"User: {current_user.id}, weight: {current_user.weight}, goal: {current_user.weight_goal}")
    print(f"User activity_level: {current_user.activity_level}")
    print(f"Calculated workout_category: {workout_category}")

    # Query workouts based on user's activity_level and calculated category
    query = db.query(Workout)
    
    # Filter by activity level and category
    query = query.filter(Workout.activity_level == current_user.activity_level)
    
    if workout_category:
        query = query.filter(Workout.workout_category == workout_category)

    print(f"Final query: {query}")
    workouts = query.all()
    print(f"Found {len(workouts)} workouts")
    
    # Print workout details for debugging
    for w in workouts:
        print(f"Workout: {w.id}, {w.title}, level: {w.activity_level}, category: {w.workout_category}")

    # Convert to response objects with proper URL handling
    workout_responses = []
    for workout in workouts:
        workout_response = WorkoutResponse(
            id=workout.id,
            title=workout.title,
            description=workout.description,
            workout_image_url=workout.workout_image_url.replace("app/", "/", 1) if workout.workout_image_url and workout.workout_image_url.startswith("app/") else workout.workout_image_url,
            workout_video_url=workout.workout_video_url.replace("app/", "/", 1) if workout.workout_video_url and workout.workout_video_url.startswith("app/") else workout.workout_video_url,
            duration=workout.duration,
            calorie_burn=workout.calorie_burn,
            activity_level=workout.activity_level,
            workout_category=workout.workout_category,
            created_at=workout.created_at,
            updated_at=workout.updated_at
        )
        workout_responses.append(workout_response)

    return WorkoutListResponse(workouts=workout_responses)
