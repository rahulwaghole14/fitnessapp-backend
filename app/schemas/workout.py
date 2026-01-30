from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class WorkoutCreate(BaseModel):
    title: str
    description: str
    workout_image_url: str
    workout_video_url: str
    duration: int
    calorie_burn: int
    activity_level: str
    workout_category: str

class WorkoutResponse(BaseModel):
    id: int
    title: str
    description: str
    workout_image_url: str
    workout_video_url: str
    duration: int
    calorie_burn: int
    activity_level: str
    workout_category: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class WorkoutListResponse(BaseModel):
    workouts: list[WorkoutResponse]
