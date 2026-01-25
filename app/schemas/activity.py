from pydantic import BaseModel, Field
from datetime import date
from typing import Optional

class DailyActivityRequest(BaseModel):
    user_id: int = Field(..., description="User ID")
    activity_date: date = Field(..., description="Activity date in YYYY-MM-DD format")
    steps: int = Field(..., ge=0, description="Number of steps")
    distance_km: float = Field(..., ge=0.0, description="Distance in kilometers")
    calories: float = Field(..., ge=0.0, description="Calories burned")
    active_minutes: float = Field(..., ge=0.0, description="Active minutes")


class DailyActivityResponse(BaseModel):
    id: int
    user_id: int
    activity_date: date
    steps: int
    distance_km: float
    calories: float
    active_minutes: float
    created_at: str

    class Config:
        from_attributes = True

class MonthlySummaryResponse(BaseModel):
    message: str
    daily_activity_stored: bool
    monthly_summary_created: bool
    daily_records_deleted: int
    old_monthly_records_deleted: int = 0
    monthly_data: Optional[dict] = None
    yearly_summary_created: bool = False
    yearly_data: Optional[dict] = None

class UserDailyActivityResponse(BaseModel):
    id: int
    user_id: int
    date: date
    steps: int
    distance_km: float
    calories: float
    active_minutes: float
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True

class WeeklyActivityData(BaseModel):
    week_number: int
    start_date: str
    end_date: str
    total_steps: int
    total_calories: float
    total_distance: float
    total_active_minutes: float

class WeeklyAnalyticsResponse(BaseModel):
    user_id: int
    year: int
    month: int
    weeks: list[WeeklyActivityData]

class MonthlyActivityResponse(BaseModel):
    """Response schema for monthly activity"""
    id: int
    user_id: int
    year: int
    month: int
    total_steps: int
    total_distance_km: float
    total_calories: float
    total_active_minutes: float
    created_at: str

    class Config:
        from_attributes = True
