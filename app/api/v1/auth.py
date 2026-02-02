from fastapi import Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from datetime import datetime
import random
from typing import Optional


from app.core.database import get_db
from app.models.user import User

from app.schemas.auth import (
    RegisterSchema, VerifyOTPSchema, LoginSchema, ResendOTPSchema,
    ForgotPasswordEmailSchema, ForgotPasswordVerifySchema, ForgotPasswordResetSchema,
    ProfileSetupSchema)

from app.utils.emailjs_utils import send_otp_email

from app.services.image_service import ImageService

image_service = ImageService()



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


async def upload_profile_image(
        profile_image: UploadFile = File(...),
        user_id: int = Form(...),
        db: Session = Depends(get_db)
):
    """
    Upload or update user's profile image

    Args:
        profile_image: Image file (jpg, jpeg, png, max 5MB)
        user_id: User ID
        db: Database session

    Returns:
        Success response with image path
    """

    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Store old image path for cleanup
    old_image_path = user.profile_image

    try:
        # Delete old image first if it exists (to handle different extensions)
        if old_image_path:
            image_service.delete_old_profile_image(old_image_path)

        # Save new profile image
        new_image_path = await image_service.save_profile_image(profile_image, user_id)

        # Update user's profile image in database
        user.profile_image = new_image_path
        db.commit()
        db.refresh(user)

        return {
            "success": True,
            "message": "Profile image updated successfully",
            "profile_image": new_image_path
        }

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Rollback database changes on error
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update profile image: {str(e)}")


async def get_user_profile(
        user_id: int,
        db: Session = Depends(get_db)
):
    """
    Get user profile data including profile image path

    Args:
        user_id: User ID
        db: Database session

    Returns:
        User profile data with relative profile image path
    """

    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {
            "success": False,
            "message": "User not found"
        }

    # Return relative profile image path if exists
    profile_image_path: Optional[str] = None
    if user.profile_image:
        # Convert stored path to public relative path
        profile_image_path = user.profile_image.replace("app/", "/")

    return {
        "success": True,
        "data": {
            "id": user.id,
            "name": user.email.split("@")[0] if user.email else None,  # Extract name from email
            "email": user.email,
            "profile_image": profile_image_path
        }
    }
