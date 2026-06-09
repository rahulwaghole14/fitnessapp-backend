from pydantic import BaseModel, EmailStr
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
    # email:str
    gender:str
    age:str
    height:float
    weight:float
    bmi:float
    weight_goal:float
    activity_level:str
    timezone: Optional[str] = "Asia/Kolkata"
    sleep_goal: Optional[int] = 480

class ChangePasswordSchema(BaseModel):
    old_password: str
    new_password: str
    confirm_password: str