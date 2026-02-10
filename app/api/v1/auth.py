from fastapi import Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import random
from typing import Optional
import bcrypt


from app.core.database import get_db
from app.models.user import User
from app.models.refresh_token import RefreshToken
from app.core.jwt_utils import create_access_token, create_refresh_token
from app.core.auth_dependencies import get_current_user, get_current_user_id

from app.schemas.auth import (
    RegisterSchema, VerifyOTPSchema, LoginSchema, ResendOTPSchema,
    ForgotPasswordEmailSchema, ForgotPasswordVerifySchema, ForgotPasswordResetSchema,
    ProfileSetupSchema)

from app.utils.emailjs_utils import send_otp_email

from app.services.image_service import ImageService

image_service = ImageService()


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    # Convert password to bytes and truncate to 72 bytes
    password_bytes = password.encode('utf-8')[:72]
    # Generate salt and hash
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    try:
        # Convert password to bytes and truncate to 72 bytes
        password_bytes = plain_password.encode('utf-8')[:72]
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except:
        # Fallback to plain text comparison for backward compatibility
        return plain_password == hashed_password



def register(user: RegisterSchema,
            db: Session = Depends(get_db)
            ):

    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        username=user.username,
        email=user.email,
        password=hash_password(user.password)
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
        if time_elapsed.total_seconds() > 300:  # OTP expires after 300 seconds
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
        if time_elapsed.total_seconds() > 300:  # OTP expires after 300 seconds
            raise HTTPException(
                status_code=400,
                detail="OTP expired. Please request a new OTP."
            )

    user.password = hash_password(data.new_password)

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

    db_user = db.query(User).filter(User.email == user.email).first()

    if not db_user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Verify password using secure verification with backward compatibility
    if not verify_password(user.password, db_user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Generate JWT tokens
    access_token = create_access_token(db_user.id)
    refresh_token, refresh_token_hash = create_refresh_token(db_user.id)
    
    # Extract JTI from the refresh token
    from app.core.jwt_utils import decode_refresh_token
    payload = decode_refresh_token(refresh_token)
    jti = payload.get("jti")
    
    # Store hashed refresh token in database with JTI
    db_refresh_token = RefreshToken(
        user_id=db_user.id,
        token_hash=refresh_token_hash,
        jti=jti,  # Store JWT ID for tracking
        expires_at=datetime.utcnow() + timedelta(days=7),
        last_used_at=datetime.utcnow()
    )
    db.add(db_refresh_token)
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "user_id": db_user.id,
            "username": db_user.username,
            "email": db_user.email,
        }
    }

#Setup User Profile
def update_profile(data: ProfileSetupSchema, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):

    #Update fields for current user
    current_user.gender = data.gender
    current_user.age = data.age
    current_user.height = data.height
    current_user.weight = data.weight
    current_user.bmi = data.bmi
    current_user.weight_goal = data.weight_goal
    current_user.activity_level = data.activity_level

    db.commit()
    db.refresh(current_user)

    return {
        "message": "Profile updated successfully",
        "email": current_user.email,
        "gender": current_user.gender,
        "age": current_user.age,
        "weight": current_user.weight,
        "height": current_user.height,
        "bmi": current_user.bmi,
        "weight_goal": current_user.weight_goal,
        "activity_level": current_user.activity_level,
    }

#Get User Profile
def get_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):

    """
    Get profile for the authenticated user
    """
    return {
        "message":"profile Get successfully",
        # "email": current_user.email,
        "gender": current_user.gender,
        "age": current_user.age,
        "height": current_user.height,
        "weight": current_user.weight,
        "bmi": current_user.bmi,
        "weight_goal": current_user.weight_goal,
        "activity_level": current_user.activity_level
    }


async def upload_profile_image(
        profile_image: UploadFile = File(...),
        current_user_id: int = Depends(get_current_user_id),
        db: Session = Depends(get_db)
):
    """
    Upload or update authenticated user's profile image
    """

    # Get current user
    user = db.query(User).filter(User.id == current_user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Store old image path for cleanup
    old_image_path = user.profile_image

    try:
        # Delete old image first if it exists (to handle different extensions)
        if old_image_path:
            image_service.delete_old_profile_image(old_image_path)

        # Save new profile image
        new_image_path = await image_service.save_profile_image(profile_image, current_user_id)

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
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    Get authenticated user's profile data including profile image path
    """

    # Return relative profile image path if exists
    profile_image_path: Optional[str] = None
    if current_user.profile_image:
        # Convert stored path to public relative path
        profile_image_path = current_user.profile_image.replace("app/", "/")

    return {
        "success": True,
        "data": {
            "id": current_user.id,
            "name": current_user.email.split("@")[0] if current_user.email else None,  # Extract name from email
            "email": current_user.email,
            "profile_image": profile_image_path
        }
    }
