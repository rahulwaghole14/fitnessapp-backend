from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth_dependencies import get_current_user
from app.models.user import User
from app.schemas.subscription import Plan, PlanBase
from app.models.subscription_plans import Plan as PlanModel



def get_all_plans(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Get all active subscription plans (user authenticated)"""
    plans = db.query(PlanModel).filter(PlanModel.is_active == True).all()
    return plans

def get_plan_id(plan_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Get specific active plan details (user authenticated)"""
    plan = db.query(PlanModel).filter(
    PlanModel.id == plan_id,
    PlanModel.is_active == True
    ).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan