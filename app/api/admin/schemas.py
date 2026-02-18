from pydantic import BaseModel, EmailStr
from typing import Optional, List, Generic, TypeVar
from datetime import datetime

# Generic Type for Paginated Response
T = TypeVar('T')

# Base Response Models
class BaseResponse(BaseModel):
    class Config:
        from_attributes = True

# Admin Schemas
class AdminBase(BaseModel):
    email: EmailStr

class AdminRegister(AdminBase):
    username: str
    email: EmailStr
    password: str

class AdminLogin(AdminBase):
    password: str

class AdminResponse(AdminBase):
    id: int
    is_active: bool
    created_at: datetime

# Token Schema
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 900  # 15 minutes in seconds

# Admin Token Management Schemas
class AdminRefreshTokenRequest(BaseModel):
    """Request schema for admin token refresh"""
    refresh_token: str

class AdminRefreshTokenResponse(BaseModel):
    """Response schema for admin token refresh"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class AdminLogoutRequest(BaseModel):
    """Request schema for admin logout"""
    refresh_token: str

# User Management Schemas
class UserRegisterSchema(BaseModel):
    username : str
    email: EmailStr
    password: str

class UserRegisterResponse(BaseModel):
    username : str
    email: EmailStr
    password: str

class UserBase(BaseModel):
    email: EmailStr
    gender: Optional[str] = None
    age: Optional[int] = None
    weight: Optional[float] = None
    height: Optional[float] = None
    bmi: Optional[float] = None
    weight_goal: Optional[float] = None
    activity_level: Optional[str] = None
    profile_image: Optional[str] = None

class UserResponse(UserBase):
    id: int
    is_verified: bool
    created_at: datetime
    is_blocked: Optional[bool] = False

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    gender: Optional[str] = None
    age: Optional[int] = None
    weight: Optional[float] = None
    height: Optional[float] = None
    weight_goal: Optional[float] = None
    activity_level: Optional[str] = None
    profile_image: Optional[str] = None

class UserBlockResponse(BaseModel):
    id: int
    email: EmailStr
    is_blocked: bool

# Workout Schemas
class WorkoutBase(BaseModel):
    name: str
    description: Optional[str] = None
    duration_minutes: int
    calories_burned: Optional[int] = None
    difficulty_level: Optional[str] = None
    category: Optional[str] = None
    workout_image_url: Optional[str] = None
    workout_video_url: Optional[str] = None

class WorkoutCreate(WorkoutBase):
    pass  # No user_id needed for admin workouts

class WorkoutUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    duration_minutes: Optional[int] = None
    calories_burned: Optional[int] = None
    difficulty_level: Optional[str] = None
    category: Optional[str] = None

class WorkoutResponse(WorkoutBase):
    id: int
    created_at: datetime

#BMI Classification schema

class BMIClassificationBase(BaseModel):
    category_name: str
    min_bmi: Optional[float] = None
    max_bmi: Optional[float] = None


class BMIClassificationCreate(BMIClassificationBase):
    pass


class BMIClassificationResponse(BMIClassificationBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Meal Schemas
class MealBase(BaseModel):
    bmi_category_id: int
    meal_type: str  # breakfast, lunch, dinner
    food_item: str
    calories: int

class MealCreate(MealBase):
    pass  # No user_id needed for admin meals

class MealUpdate(BaseModel):
    name: Optional[str] = None
    calories: Optional[int] = None
    meal_type: Optional[str] = None
    bmi_category_id: Optional[int] = None

class MealResponse(MealBase):
    id: int

# Pagination Schema
class PaginationInfo(BaseModel):
    page: int
    limit: int
    total_items: int
    total_pages: int
    has_next: bool
    has_prev: bool

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    pagination: PaginationInfo

# Error Response Schema
class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None

# Success Response Schema
class SuccessResponse(BaseModel):
    message: str
    data: Optional[dict] = None
