from pydantic import BaseModel, EmailStr

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
