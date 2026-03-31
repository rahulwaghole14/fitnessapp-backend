from pydantic import BaseModel, EmailStr, ConfigDict, field_validator
from typing import Optional, List, Generic, TypeVar
from datetime import datetime
import json

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
    email:EmailStr
    password: str

# Admin Forgot Password Schemas
class AdminForgotPasswordEmailSchema(BaseModel):
    email: EmailStr

class AdminForgotPasswordVerifySchema(BaseModel):
    email: EmailStr
    otp: str

class AdminForgotPasswordResetSchema(BaseModel):
    email: EmailStr
    otp: str
    new_password: str

# Admin Change Password Schema
class AdminChangePasswordSchema(BaseModel):
    old_password: str
    new_password: str

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
    username: str
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


class BMIClassificationUpdate(BaseModel):
    category_name: Optional[str] = None
    min_bmi: Optional[float] = None
    max_bmi: Optional[float] = None


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


#Subscription Plan Schemas
class PlanBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    duration_days: int  # Changed from duration_months
    features: Optional[List[str]] = None  # Changed from str to List[str]
    is_active: bool = True

class PlanCreate(PlanBase):
    pass

class PlanUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    duration_days: Optional[int] = None  # Changed from duration_months
    features: Optional[List[str]] = None  # Changed from str to List[str]
    is_active: Optional[bool] = None

class Plan(PlanBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    @field_validator('features', mode='before')
    @classmethod
    def parse_features(cls, v):
        """Parse features from database JSON string to list"""
        if v is None:
            return None
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
                elif isinstance(parsed, dict):
                    # Convert dict values to list of strings
                    return [f"{k}:{v}" for k, v_item in parsed.items()]
                return [str(parsed)]
            except (json.JSONDecodeError, TypeError):
                return [str(v)]
        return [str(v)]

#Dashboard Schemas
class OverviewResponse(BaseModel):
    total_users: int
    total_workouts: int
    total_meals: int
    active_subscriptions: int

class UserResponsedash(BaseModel):
    id: int
    username: str
    email: str
    activity_level: Optional[str] = None
    gender: Optional[str] = None
