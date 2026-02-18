from fastapi import HTTPException, Depends, Query, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import Optional, List
from math import ceil
import bcrypt
from datetime import datetime

from app.models.user import User
from app.models.admin import Admin
from app.core.database import get_db
from app.services.image_service import ImageService

from .dependencies import get_current_admin
from .schemas import (
    UserRegisterResponse, UserResponse, UserUpdate, UserBlockResponse, PaginatedResponse, PaginationInfo,
    UserRegisterSchema
)

# Initialize image service
image_service = ImageService()


def hash_password(password: str) -> str:

    # Convert password to bytes and truncate to 72 bytes
    password_bytes = password.encode('utf-8')[:72]
    # Generate salt and hash
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')

async def register_user(user: UserRegisterSchema,
            db: Session = Depends(get_db),
            current_admin: Admin = Depends(get_current_admin)
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
    db.refresh(new_user)

    return UserRegisterResponse(
        username=new_user.username,
        email=new_user.email,
        password=user.password  # Return the original password from request
    )


async def get_users_paginated(
        search: Optional[str] = Query(None, description="Search term for email or name"),
        is_verified: Optional[bool] = Query(None, description="Filter by verification status"),
        is_blocked: Optional[bool] = Query(None, description="Filter by blocked status"),
        db: Session = Depends(get_db),
        current_admin: Admin = Depends(get_current_admin)
) -> List[UserResponse]:

    # Build query
    query = db.query(User)

    # Apply filters
    if search:
        query = query.filter(
            or_(
                User.email.ilike(f"%{search}%"),
                User.gender.ilike(f"%{search}%")
            )
        )

    if is_verified is not None:
        query = query.filter(User.is_verified == is_verified)

    if is_blocked is not None:
        pass

    # Get all results (no pagination)
    users = query.all()

    # Convert users to response format
    user_responses = []
    for user in users:
        user_response = UserResponse(
            id=user.id,
            email=user.email,
            gender=user.gender,
            age=user.age,
            weight=user.weight,
            height=user.height,
            bmi=user.bmi,
            weight_goal=user.weight_goal,
            activity_level=user.activity_level,
            profile_image=user.profile_image.replace("app/", "/") if user.profile_image else None,
            is_verified=user.is_verified,
            created_at=datetime.utcnow(),  # Use current time since User model doesn't have created_at
            is_blocked=False
        )
        user_responses.append(user_response)

    return user_responses


async def get_user_by_id(
        user_id: int,
        db: Session = Depends(get_db),
        current_admin: Admin = Depends(get_current_admin)
) -> Optional[UserResponse]:

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse(
        id=user.id,
        email=user.email,
        gender=user.gender,
        age=user.age,
        weight=user.weight,
        height=user.height,
        bmi=user.bmi,
        weight_goal=user.weight_goal,
        activity_level=user.activity_level,
        profile_image=user.profile_image.replace("app/", "/") if user.profile_image else None,
        is_verified=user.is_verified,
        created_at=datetime.utcnow(),  # Use current time since User model doesn't have created_at
        is_blocked=False
    )


async def update_user(
        user_id: int,
        email: Optional[str] = Form(None),
        gender: Optional[str] = Form(None),
        age: Optional[int] = Form(None),
        weight: Optional[float] = Form(None),
        height: Optional[float] = Form(None),
        bmi: Optional[float] = Form(None),
        weight_goal: Optional[float] = Form(None),
        activity_level: Optional[str] = Form(None),
        profile_image: Optional[UploadFile] = File(None),
        db: Session = Depends(get_db),
        current_admin: Admin = Depends(get_current_admin)
) -> Optional[UserResponse]:

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        # Handle profile image upload if provided
        if profile_image:
            # Store old image path for cleanup
            old_image_path = user.profile_image

            # Delete old image first if it exists
            if old_image_path:
                image_service.delete_old_profile_image(old_image_path)

            # Save new profile image
            new_image_path = await image_service.save_profile_image(profile_image, user_id)
            user.profile_image = new_image_path

        # Update other fields if they are provided (not None)
        if email is not None:
            # Check if email is being updated and if it's already taken
            existing_user = db.query(User).filter(
                and_(User.email == email, User.id != user_id)
            ).first()
            if existing_user:
                raise ValueError("Email already taken")
            user.email = email

        if gender is not None:
            user.gender = gender
        if age is not None:
            user.age = age
        if weight is not None:
            user.weight = weight
        if height is not None:
            user.height = height
        if bmi is not None:
            user.bmi = bmi
        if weight_goal is not None:
            user.weight_goal = weight_goal
        if activity_level is not None:
            user.activity_level = activity_level

        db.commit()
        db.refresh(user)

        return UserResponse(
            id=user.id,
            email=user.email,
            gender=user.gender,
            age=user.age,
            weight=user.weight,
            height=user.height,
            bmi=user.bmi,
            weight_goal=user.weight_goal,
            activity_level=user.activity_level,
            profile_image=user.profile_image.replace("app/", "/") if user.profile_image else None,
            is_verified=user.is_verified,
            created_at=datetime.utcnow(),  # Use current time since User model doesn't have created_at
            is_blocked=False
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Rollback database changes on error
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update user: {str(e)}")


async def delete_user(
        user_id: int,
        db: Session = Depends(get_db),
        current_admin: Admin = Depends(get_current_admin)
) -> bool:

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Delete the user (this will cascade delete related records if properly configured)
    db.delete(user)
    db.commit()

    return True
