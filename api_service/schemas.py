from pydantic import BaseModel, EmailStr, Field
from datetime import date
from typing import Optional

class RegisterSchema(BaseModel):
    username : str
    email: EmailStr
    password: str

class VerifyOTPSchema(BaseModel):
    email: EmailStr
    otp: str

class ResendOTPSchema(BaseModel):
    email: EmailStr

# Forgot Password Schemas
class ForgotPasswordEmailSchema(BaseModel):
    email: EmailStr

class ForgotPasswordVerifySchema(BaseModel):
    email: EmailStr
    otp: str

class ForgotPasswordResetSchema(BaseModel):
    email: EmailStr
    otp: str
    new_password: str


class LoginSchema(BaseModel):
    email: EmailStr
    password: str

class ProfileSetupSchema(BaseModel):
    email:str
    gender:str
    age:str
    height:float
    weight:float
    bmi:float
    weight_goal:float
    activity_level:str

# Daily Activity Schemas
class DailyActivityRequest(BaseModel):
    """Request schema for daily activity using existing user_daily_activity table"""
    user_id: int = Field(..., description="User ID")
    activity_date: date = Field(..., description="Activity date in YYYY-MM-DD format")
    steps: int = Field(..., ge=0, description="Number of steps")
    distance_km: float = Field(..., ge=0.0, description="Distance in kilometers")
    calories: float = Field(..., ge=0.0, description="Calories burned")
    active_minutes: float = Field(..., ge=0.0, description="Active minutes")

class DailyActivityResponse(BaseModel):
    """Response schema for daily activity"""
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
    """Response schema for monthly summary operation"""
    message: str
    daily_activity_stored: bool
    monthly_summary_created: bool
    daily_records_deleted: int
    monthly_data: Optional[dict] = None
