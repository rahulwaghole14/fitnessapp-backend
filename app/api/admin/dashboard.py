from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.api.admin.schemas import (
    OverviewResponse
)
from app.api.admin.dependencies import get_current_admin
from app.models.user import User
from app.models.workout import Workout
from app.models.meal import Meal
from app.models.subscription import Subscription

async def get_overview(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin)
):
     # Total Users
    total_users = db.query(func.count(User.id)).scalar()
    # Active Users
    # active_users = db.query(func.count(User.id)).filter(User.is_active == True).scalar()
        
    # Total Workouts
    total_workouts = db.query(func.count(Workout.id)).scalar()
        
    # Total Meals
    total_meals = db.query(func.count(Meal.id)).scalar()
        
    # Active Subscriptions
    active_subscriptions = db.query(func.count(Subscription.id)).filter(
            Subscription.status == 'active'
    ).scalar()
        
    # Monthly Revenue (current month)
    # current_month = datetime.now().month
    # current_year = datetime.now().year
    # monthly_revenue = db.query(func.sum(Subscription.amount)).filter(
    #     extract('month', Subscription.created_at) == current_month,
    #     extract('year', Subscription.created_at) == current_year
    # ).scalar() or 0
        
    return {
        "total_users": total_users,
        # "active_users": active_users,
        "total_workouts": total_workouts,
        "total_meals": total_meals,
        "active_subscriptions": active_subscriptions,
        # "monthly_revenue": float(monthly_revenue)
    }


async def get_all_users(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_admin)
):
    """Get 10 newest users in descending order by ID."""
    users = db.query(User).order_by(User.id.desc()).limit(6).all()
    
    return [
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "activity_level": user.activity_level,
            "gender": user.gender
        }
        for user in users
    ]
