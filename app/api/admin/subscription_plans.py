from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.admin import Admin
from app.models.subscription_plans import Plan as PlanModel
from .dependencies import get_current_admin
from .schemas import Plan, PlanCreate, PlanUpdate
from .dependencies import get_current_admin
from app.utils.subscription_features_utils import convert_features_to_json


def create_plan(plan: PlanCreate, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    # Check if plan name already exists
    existing_plan = db.query(PlanModel).filter(PlanModel.name == plan.name).first()
    if existing_plan:
        raise HTTPException(status_code=400, detail="Plan with this name already exists")

    # Convert features list to JSON string for database storage
    features_json = convert_features_to_json(plan.features)

    db_plan = PlanModel(
        name=plan.name,
        description=plan.description,
        price=plan.price,
        duration_days=plan.duration_days,
        features=features_json,  # Store as JSON string
        is_active=plan.is_active
    )

    db.add(db_plan)
    db.commit()
    db.refresh(db_plan)
    return db_plan


def get_plans(db: Session = Depends(get_db), current_user = Depends(get_current_admin)):
    plans = db.query(PlanModel).all()
    return plans


def get_plan_by_id(plan_id: int, db: Session = Depends(get_db),current_user = Depends(get_current_admin)):
    plan = db.query(PlanModel).filter(PlanModel.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


def update_plan(plan_id: int, plan_update: PlanUpdate, db: Session = Depends(get_db),
                current_user=Depends(get_current_admin)):
    db_plan = db.query(PlanModel).filter(PlanModel.id == plan_id).first()
    if not db_plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    update_data = plan_update.dict(exclude_unset=True)

    # Handle features conversion if provided
    if "features" in update_data and update_data["features"] is not None:
        update_data["features"] = convert_features_to_json(update_data["features"])

    for key, value in update_data.items():
        setattr(db_plan, key, value)

    db.commit()
    db.refresh(db_plan)
    return db_plan


def delete_plan(plan_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_admin)):
    """Delete/deactivate subscription plan (admin only)"""
    db_plan = db.query(PlanModel).filter(PlanModel.id == plan_id).first()
    if not db_plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    db_plan.is_active = False
    db.commit()
    return {"message": "Plan deactivated successfully"}
