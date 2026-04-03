from fastapi import HTTPException, Depends, Query, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import Optional, List
from math import ceil
import bcrypt
from datetime import datetime
from pydantic import BaseModel

from app.models.user import User
from app.models.admin import Admin
from app.models.subscription import Subscription
from app.models.subscription_plans import Plan
from app.core.database import get_db
from app.services.image_service import ImageService

from .dependencies import get_current_admin
from .schemas import (
    UserRegisterResponse, UserResponse, UserUpdate, UserBlockResponse, PaginatedResponse, PaginationInfo,
    UserRegisterSchema, UserSubscriptionResponse, UserSubscriptionUpdate
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
        skip: int = Query(0, ge=0, description="Number of records to skip"),
        limit: int = Query(10, ge=1, le=1000, description="Maximum records to return"),
        search: Optional[str] = Query(None, description="Search term for email or name"),
        is_verified: Optional[bool] = Query(None, description="Filter by verification status"),
        is_blocked: Optional[bool] = Query(None, description="Filter by blocked status"),
        db: Session = Depends(get_db),
        current_admin: Admin = Depends(get_current_admin)
) -> dict:

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

    # Get total count for pagination metadata
    total_count = query.count()

    # Apply pagination
    users = query.offset(skip).limit(limit).all()

    # Convert users to response format
    user_responses = []
    for user in users:
        user_response = UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            gender=user.gender,
            age=user.age,
            weight=user.weight,
            height=user.height,
            bmi=user.bmi,
            weight_goal=user.weight_goal,
            activity_level=user.activity_level,
            # profile_image=user.profile_image.replace("app/", "/",1) if user.profile_image else None,
            profile_image=user.profile_image if user.profile_image else None,
            is_verified=user.is_verified,
            created_at=datetime.utcnow(),  # Use current time since User model doesn't have created_at
            is_blocked=False
        )
        user_responses.append(user_response)

    # Calculate pagination metadata
    total_pages = ceil(total_count / limit)
    current_page = skip // limit + 1

    return {
        "users": user_responses,
        "pagination": {
            "current_page": current_page,
            "page_size": limit,
            "total_items": total_count,
            "total_pages": total_pages,
            "has_next": current_page < total_pages,
            "has_prev": current_page > 1,
            "next_skip": skip + limit if current_page < total_pages else None,
            "prev_skip": skip - limit if current_page > 1 else None
        }
    }


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
        username=user.username,  # Add missing username field
        email=user.email,
        gender=user.gender,
        age=user.age,
        weight=user.weight,
        height=user.height,
        bmi=user.bmi,
        weight_goal=user.weight_goal,
        activity_level=user.activity_level,
        # profile_image=user.profile_image.replace("app/", "/",1) if user.profile_image else None,
        profile_image=user.profile_image if user.profile_image else None,
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
            username=user.username,  # Add missing username field
            email=user.email,
            gender=user.gender,
            age=user.age,
            weight=user.weight,
            height=user.height,
            bmi=user.bmi,
            weight_goal=user.weight_goal,
            activity_level=user.activity_level,
            profile_image=user.profile_image,  # Cloudinary URL is already public
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
) -> dict:

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if user has active subscription plan
    # Note: You'll need to import your subscription model
    from app.models.subscription import Subscription  # Adjust based on your actual model
    
    active_subscription = db.query(Subscription).filter(
        Subscription.user_id == user_id,
        Subscription.status == "active",
        Subscription.end_date >= datetime.utcnow()
    ).first()
    
    if active_subscription:
        raise HTTPException(
            status_code=400, 
            detail="User has an active subscription plan currently, can't delete user"
        )

    # Delete user profile image from Cloudinary if exists
    if user.profile_image:
        try:
            import cloudinary
            import cloudinary.uploader
            import re
            
            # Extract public_id from Cloudinary URL
            # Cloudinary URL format: https://res.cloudinary.com/your_cloud_name/image/upload/v1234567890/public_id.jpg
            url_pattern = r'/upload/v\d+/(.+?)\.'
            match = re.search(url_pattern, user.profile_image)
            
            if match:
                public_id = match.group(1)
                # Delete image from Cloudinary
                cloudinary.uploader.destroy(public_id)
                print(f"Successfully deleted profile image: {public_id}")
            else:
                print(f"Could not extract public_id from URL: {user.profile_image}")
                
        except Exception as e:
            print(f"Failed to delete profile image from Cloudinary: {str(e)}")
            # Continue with user deletion even if image deletion fails

    # Delete user (this will cascade delete related records if properly configured)
    db.delete(user)
    db.commit()

    return {"message": f"User {user_id} deleted successfully"}


async def get_user_subscriptions_paginated(
        skip: int = Query(0, ge=0, description="Number of records to skip"),
        limit: int = Query(10, ge=1, le=1000, description="Maximum records to return"),
        search: Optional[str] = Query(None, description="Search term for username or plan name"),
        status: Optional[str] = Query(None, description="Filter by subscription status"),
        db: Session = Depends(get_db),
        current_admin: Admin = Depends(get_current_admin)
) -> dict:

    # Build query with joins
    query = db.query(
        Subscription.id,
        Subscription.user_id,
        User.username.label('username'),
        Subscription.plan_id,
        Plan.name.label('plan_name'),
        Subscription.start_date,
        Subscription.end_date,
        Subscription.status,
        Subscription.auto_renew,
        Subscription.created_at,
        Subscription.updated_at
    ).join(
        User, Subscription.user_id == User.id
    ).join(
        Plan, Subscription.plan_id == Plan.id
    )

    # Apply filters
    if search:
        query = query.filter(
            and_(
                User.username.ilike(f"%{search}%"),
                Plan.name.ilike(f"%{search}%")
            )
        )

    if status:
        query = query.filter(Subscription.status == status)

    # Get total count for pagination metadata
    total_count = query.count()

    # Apply pagination
    subscriptions = query.offset(skip).limit(limit).all()

    # Convert to response format
    subscription_responses = []
    for sub in subscriptions:
        subscription_response = UserSubscriptionResponse(
            id=sub.id,
            user_id=sub.user_id,
            username=sub.username,
            # plan_id=sub.plan_id,
            plan_name=sub.plan_name,
            start_date=sub.start_date,
            end_date=sub.end_date,
            status=sub.status,
            auto_renew=sub.auto_renew,
            created_at=sub.created_at,
            # updated_at=sub.updated_at
        )
        subscription_responses.append(subscription_response)

    # Calculate pagination metadata
    total_pages = ceil(total_count / limit)
    current_page = skip // limit + 1

    return {
        "subscriptions": subscription_responses,
        "pagination": {
            "current_page": current_page,
            "page_size": limit,
            "total_items": total_count,
            "total_pages": total_pages,
            "has_next": current_page < total_pages,
            "has_prev": current_page > 1,
            "next_skip": skip + limit if current_page < total_pages else None,
            "prev_skip": skip - limit if current_page > 1 else None
        }
    }


async def get_user_subscription_by_id(
        subscription_id: int,
        db: Session = Depends(get_db),
        current_admin: Admin = Depends(get_current_admin)
) -> UserSubscriptionResponse:

    # Query with joins
    subscription = db.query(
        Subscription.id,
        Subscription.user_id,
        User.username.label('username'),
        Subscription.plan_id,
        Plan.name.label('plan_name'),
        Subscription.start_date,
        Subscription.end_date,
        Subscription.status,
        Subscription.auto_renew,
        Subscription.created_at,
        Subscription.updated_at
    ).join(
        User, Subscription.user_id == User.id
    ).join(
        Plan, Subscription.plan_id == Plan.id
    ).filter(
        Subscription.id == subscription_id
    ).first()

    if not subscription:
        raise HTTPException(status_code=404, detail="User subscription not found")

    return UserSubscriptionResponse(
        id=subscription.id,
        user_id=subscription.user_id,
        username=subscription.username,
        # plan_id=subscription.plan_id,
        plan_name=subscription.plan_name,
        start_date=subscription.start_date,
        end_date=subscription.end_date,
        status=subscription.status,
        auto_renew=subscription.auto_renew,
        created_at=subscription.created_at,
        # updated_at=subscription.updated_at
    )


async def update_user_subscription(
        subscription_id: int,
        subscription_update: UserSubscriptionUpdate,
        db: Session = Depends(get_db),
        current_admin: Admin = Depends(get_current_admin)
) -> UserSubscriptionResponse:

    # Get existing subscription
    subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    
    if not subscription:
        raise HTTPException(status_code=404, detail="User subscription not found")

    # Update status
    subscription.status = subscription_update.status

    # Update the updated_at timestamp
    subscription.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(subscription)

    # Get updated data with joins for response
    updated_subscription = db.query(
        Subscription.id,
        Subscription.user_id,
        User.username.label('username'),
        Subscription.plan_id,
        Plan.name.label('plan_name'),
        Subscription.start_date,
        Subscription.end_date,
        Subscription.status,
        Subscription.auto_renew,
        Subscription.created_at,
        Subscription.updated_at
    ).join(
        User, Subscription.user_id == User.id
    ).join(
        Plan, Subscription.plan_id == Plan.id
    ).filter(
        Subscription.id == subscription_id
    ).first()

    return UserSubscriptionResponse(
        id=updated_subscription.id,
        user_id=updated_subscription.user_id,
        username=updated_subscription.username,
        # plan_id=updated_subscription.plan_id,
        plan_name=updated_subscription.plan_name,
        start_date=updated_subscription.start_date,
        end_date=updated_subscription.end_date,
        status=updated_subscription.status,
        auto_renew=updated_subscription.auto_renew,
        created_at=updated_subscription.created_at,
        # updated_at=updated_subscription.updated_at
    )
