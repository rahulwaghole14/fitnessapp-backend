import uuid
from datetime import date
from typing import Optional
from fastapi import Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth_dependencies import get_current_user_id
from app.models.sleep import SleepSession, UserDailySleep, UserMonthlySleep, UserYearlySleep
from app.schemas.sleep import (
    SleepSessionCreate, SleepSessionUpdate, SleepSessionResponse,
    SleepAnalyticsResponse, SleepHistoryResponse, UserDailySleepResponse,
    UserMonthlySleepResponse, UserYearlySleepResponse
)
from app.services.sleep_service import SleepService
from app.services.sleep_analytics_service import SleepAnalyticsService


def create_session(
    payload: SleepSessionCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Create a new raw sleep session. Triggers automated cascade aggregation."""
    return SleepService.create_sleep_session(db, user_id, payload)


def update_session(
    id: uuid.UUID,
    payload: SleepSessionUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Update an existing sleep session. Re-calculates and re-aggregates both old and new dates."""
    return SleepService.update_sleep_session(db, user_id, id, payload)


def delete_session(
    id: uuid.UUID,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Soft delete a sleep session. Recalculates aggregates with the session excluded."""
    return SleepService.delete_sleep_session(db, user_id, id)


def get_session(
    id: uuid.UUID,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Fetch details of a single active sleep session."""
    session = db.query(SleepSession).filter(
        SleepSession.id == id,
        SleepSession.user_id == user_id,
        SleepSession.deleted_at.is_(None)
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sleep session not found"
        )
    return session


def get_history(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Fetch a paginated history of active sleep sessions for the authenticated user."""
    offset = (page - 1) * limit
    query = db.query(SleepSession).filter(
        SleepSession.user_id == user_id,
        SleepSession.deleted_at.is_(None)
    )
    
    total = query.count()
    sessions = query.order_by(SleepSession.start_time.desc()).offset(offset).limit(limit).all()
    
    return SleepHistoryResponse(
        sessions=sessions,
        total=total,
        page=page,
        limit=limit
    )


def get_daily(
    sleep_date: Optional[date] = Query(None, description="The wake date in YYYY-MM-DD format"),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Fetch aggregated sleep metrics for a specific daily wake date (defaults to today)."""
    if not sleep_date:
        sleep_date = date.today()
        
    record = db.query(UserDailySleep).filter(
        UserDailySleep.user_id == user_id,
        UserDailySleep.sleep_date == sleep_date
    ).first()
    
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No daily sleep record found for {sleep_date}"
        )
    return record


def get_monthly(
    year: int = Query(..., ge=2000, description="Year"),
    month: int = Query(..., ge=1, le=12, description="Month (1-12)"),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Fetch monthly aggregated sleep statistics."""
    record = db.query(UserMonthlySleep).filter(
        UserMonthlySleep.user_id == user_id,
        UserMonthlySleep.year == year,
        UserMonthlySleep.month == month
    ).first()
    
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No monthly sleep record found for {year}-{month:02d}"
        )
    return record


def get_yearly(
    year: int = Query(..., ge=2000, description="Year"),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Fetch yearly aggregated sleep statistics."""
    record = db.query(UserYearlySleep).filter(
        UserYearlySleep.user_id == user_id,
        UserYearlySleep.year == year
    ).first()
    
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No yearly sleep record found for {year}"
        )
    return record


def get_analytics(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Fetch user's comprehensive dashboard sleep analytics (rolling 7 days, streaks, etc.)."""
    return SleepAnalyticsService.get_dashboard_analytics(db, user_id)
