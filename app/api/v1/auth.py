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
    ProfileSetupSchema, ChangePasswordSchema)

from app.utils.emailjs_utils import send_otp_email
from app.utils.activity_logger import log_activity

from app.services.image_service import ImageService

image_service = ImageService()


def hash_password(password: str) -> str:
    # Convert password to bytes and truncate to 72 bytes
    password_bytes = password.encode('utf-8')[:72]
    # Generate salt and hash
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        # Convert password to bytes and truncate to 72 bytes
        password_bytes = plain_password.encode('utf-8')[:72]
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except:
        # Fallback to plain text comparison for backward compatibility
        return plain_password == hashed_password


# RESEND OTP
def resend_otp(data: ResendOTPSchema, db: Session = Depends(get_db)):

    user = db.query(User).filter(User.email == data.email).first()

    if not user:
        raise HTTPException(status_code=404, detail="Email not found. Please register first.")

    # Generate new OTP
    new_otp = str(random.randint(100000, 999999))

    # Update existing user record with new OTP and fresh timestamp
    user.otp = new_otp
    user.otp_created_at = datetime.utcnow()  # Reset expiration timer
    db.commit()

    # Define user-specific resend OTP message
    user_message = """We received a request to resend the OTP verification code for your Fitness App account.

    To complete your verification of your email address, please use the One-Time Password (OTP) provided below.

    For security reasons, this OTP is valid for 5 minutes only."""

    # Send new OTP via email using existing EmailJS function with role-specific message
    try:
        send_otp_email(data.email, new_otp, user_message)
    except Exception as e:
        print(f"Email sending failed: {e}")
        # Don't fail the operation if email fails, user can still verify with printed OTP

    return {"message": "New OTP sent to your email"}


# REGISTER
def register(user: RegisterSchema, db: Session = Depends(get_db)):

    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        username=user.username,
        email=user.email,
        password=hash_password(user.password)
    )

    db.add(new_user)
    db.commit()

    # Log user registration activity
    log_activity(db, new_user.id, new_user.username, "signup", f"{new_user.username} signed up")

    # Generate JWT tokens for immediate login
    access_token = create_access_token(new_user.id)
    refresh_token, refresh_token_hash = create_refresh_token(new_user.id)
    
    # Extract JTI from the refresh token
    from app.core.jwt_utils import decode_refresh_token
    payload = decode_refresh_token(refresh_token)
    jti = payload.get("jti")
    
    # Store hashed refresh token in database with JTI
    db_refresh_token = RefreshToken(
        user_id=new_user.id,
        token_hash=refresh_token_hash,
        jti=jti,  # Store JWT ID for tracking
        expires_at=datetime.utcnow() + timedelta(days=7),
        last_used_at=datetime.utcnow()
    )
    db.add(db_refresh_token)
    db.commit()

    return {
        "message": "Registration successful",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "user_id": new_user.id,
            "username": new_user.username,
            "email": new_user.email,
        }
    }


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
 
    # Define user-specific message
    user_message = """We received a request to reset the password for your Fitness App account.

To proceed with resetting your password, please use the One-Time Password (OTP) provided below.

For security reasons, this OTP is valid for 5 minutes only."""

    # Send new OTP via email using existing EmailJS function with role-specific message
    try:
        send_otp_email(user.email, new_otp, user_message)
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

    # Revoke all existing refresh tokens for this user (logout from all devices)
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user.id,
        RefreshToken.is_revoked == False
    ).update({"is_revoked": True})

    # Clear OTP and timestamp after successful password reset
    user.otp = None
    user.otp_created_at = None

    db.commit()

    return {"message": "Password reset successfully. All sessions have been logged out. Please login again."}


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
  
    # Clean up any revoked refresh tokens for this admin before login
    db.query(RefreshToken).filter(
        RefreshToken.user_id == db_user.id,
        RefreshToken.is_revoked == True
    ).delete()
    db.commit()

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

    # Log profile update activity
    log_activity(db, current_user.id, current_user.username, "profile_update", f"{current_user.username} updated profile")

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


    # Get current user
    user = db.query(User).filter(User.id == current_user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Store old image path for cleanup
    old_image_path = user.profile_image

    try:
        # Save new profile image FIRST
        new_image_path = await image_service.save_profile_image(profile_image, current_user_id)

        # Delete old image only AFTER successful upload
        if old_image_path:
            image_service.delete_old_profile_image(old_image_path)

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


    # Return profile image path if exists
    profile_image_path: Optional[str] = None
    if current_user.profile_image:
        # Only convert local paths, not Cloudinary URLs
        if current_user.profile_image.startswith("app/"):
            profile_image_path = current_user.profile_image.replace("app/", "/", 1)
        else:
            # For Cloudinary URLs, return as-is
            profile_image_path = current_user.profile_image

    return {
        "success": True,
        "data": {
            "id": current_user.id,
            "name": current_user.email.split("@")[0] if current_user.email else None,  # Extract name from email
            "email": current_user.email,
            "profile_image": profile_image_path
        }
    }


def change_password(
    data: ChangePasswordSchema,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Change password for authenticated user.
    
    Args:
        data: ChangePasswordSchema containing old_password, new_password, confirm_password
        current_user: Current authenticated user from JWT token
        db: Database session
    
    Returns:
        Success or error response
    """
    # Validate that new password and confirm password match
    if data.new_password != data.confirm_password:
        raise HTTPException(status_code=400, detail="New password and confirm password do not match")
    
    # Verify old password
    if not verify_password(data.old_password, current_user.password):
        raise HTTPException(status_code=400, detail="Old password is incorrect")
    
    # Check if new password is same as old password
    if verify_password(data.new_password, current_user.password):
        raise HTTPException(status_code=400, detail="New password cannot be the same as old password")
    
    try:
        # Hash and update the new password
        current_user.password = hash_password(data.new_password)
        db.commit()
        
        # Log password change activity
        log_activity(db, current_user.id, current_user.username, "password_change", f"{current_user.username} changed password")
        
        return {
            "message": "Password changed successfully"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to change password: {str(e)}")
