"""
User related schemas for admin API
"""
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UserRegisterSchema(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserRegisterResponse(BaseModel):
    username: str
    email: EmailStr
    created_at: datetime
    
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

class UserResponsedash(BaseModel):
    id: int
    username: str
    email: str
    activity_level: Optional[str] = None
    gender: Optional[str] = None

class UserAnalyticsResponse(BaseModel):
    id: int
    username: str
    gender: Optional[str] = None
    activity_level: Optional[str] = None
    created_at: datetime
