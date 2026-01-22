from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import random

from app.core.database import get_db
from app.models.user import User

from app.schemas.auth import (
    RegisterSchema, VerifyOTPSchema, LoginSchema, ResendOTPSchema,
    ForgotPasswordEmailSchema, ForgotPasswordVerifySchema, ForgotPasswordResetSchema,
    ProfileSetupSchema)

from app.utils.emailjs_utils import send_otp_email



def register(user: RegisterSchema,
            db: Session = Depends(get_db)
            ):

    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        username=user.username,
        email=user.email,
        password=user.password  # plain text for now
    )

    db.add(new_user)
    db.commit()

    return {"message": "Registration successful"}

# FORGOT PASSWORD - SEND OTP
def forgot_password_send_otp(user: ForgotPasswordEmailSchema, db: Session = Depends(get_db)):

    user = db.query(User).filter(User.email == user.email).first()

    if not user:
        raise HTTPException(status_code=404, detail="Email not found. Please check your email or register.")

    # Generate new OTP for password reset
    new_otp = str(random.randint(100000, 999999))

    # Update existing user record with new OTP and fresh timestamp
    user.otp = new_otp
    user.otp_created_at = datetime.utcnow()  # Reset expiration timer for password reset
    db.commit()

    print(f"Forgot Password OTP for {user.email}: {new_otp}")

    # Send new OTP via email using existing EmailJS function
    try:
        send_otp_email(user.email, new_otp)
    except Exception as e:
        print(f"Email sending failed: {e}")

    return {"message": "Password reset OTP sent to your email"}


# FORGOT PASSWORD - VERIFY OTP
def forgot_password_verify_otp(data: ForgotPasswordVerifySchema, db: Session = Depends(get_db)):

    user = db.query(User).filter(User.email == data.email).first()

    if not user or user.otp != data.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    # Check OTP expiration (300 seconds validity) - reuse existing logic
    if user.otp_created_at:
        time_elapsed = datetime.utcnow() - user.otp_created_at
        if time_elapsed.total_seconds() > 300:  # OTP expires after 60 seconds
            raise HTTPException(
                status_code=400,
                detail="OTP expired. Please request a new OTP."
            )
    # OTP is valid - allow password reset
    return {"message": "OTP verified successfully. You can now reset your password."}


# FORGOT PASSWORD - RESET PASSWORD
def forgot_password_reset_password(data: ForgotPasswordResetSchema, db: Session = Depends(get_db)):

    user = db.query(User).filter(User.email == data.email).first()

    if not user or user.otp != data.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    # Re-check OTP expiration (300 seconds validity) for security
    if user.otp_created_at:
        time_elapsed = datetime.utcnow() - user.otp_created_at
        if time_elapsed.total_seconds() > 300:  # OTP expires after 60 seconds
            raise HTTPException(
                status_code=400,
                detail="OTP expired. Please request a new OTP."
            )

    user.password = data.new_password

    # Clear OTP and timestamp after successful password reset
    user.otp = None
    user.otp_created_at = None

    db.commit()

    return {"message": "Password reset successfully. You can now login with your new password."}


# LOGIN
def login(user: LoginSchema,
          db: Session = Depends(get_db)
          ):
    # db: Session = get_db()

    db_user = db.query(User).filter(
        User.email == user.email,
        User.password == user.password

    ).first()

    if not db_user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return {"message": "Login successful", "username": {
            "user_id": db_user.id,
            "username": db_user.username,
            "email": db_user.email,
                }
            }

#Setup User Profile
def update_profile(data: ProfileSetupSchema, db: Session = Depends(get_db)):

    user = db.query(User).filter(User.email == data.email).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    #Update fields
    user.gender = data.gender
    user.age = data.age
    user.height = data.height
    user.weight = data.weight
    user.bmi = data.bmi
    user.weight_goal = data.weight_goal
    user.activity_level = data.activity_level

    db.commit()
    db.refresh(user)

    return {
        "message": "Profile updated successfully",
        "email": user.email,
        "gender": user.gender,
        "age": user.age,
        "weight": user.weight,
        "height": user.height,
        "bmi": user.bmi,
        "weight_goal": user.weight_goal,
        "activity_level": user.activity_level,
    }

#Get User Profile
def get_profile(email: str, db: Session = Depends(get_db)):

    user = db.query(User).filter(User.email == email).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "message":"profile Get successfully",
        "email": user.email,
        "gender": user.gender,
        "age": user.age,
        "height": user.height,
        "weight": user.weight,
        "bmi": user.bmi,
        "weight_goal": user.weight_goal,
        "activity_level": user.activity_level
    }
