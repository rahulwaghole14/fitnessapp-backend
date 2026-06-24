import uuid
from datetime import datetime, date
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.sleep import SleepSession
from app.schemas.sleep import SleepSessionCreate, SleepSessionUpdate
from app.services.sleep_aggregation_service import SleepAggregationService, get_wake_date


class SleepService:

    @staticmethod
    def calculate_sleep_score(duration_minutes: int, deep_minutes: int = 0, rem_minutes: int = 0, awake_minutes: int = 0) -> int:
        """Calculate a robust sleep score from 10 to 100 based on total duration and sleep phase metrics."""
        # 1. Base Score based on total sleep duration (ideal is 8 hours / 480 minutes)
        if duration_minutes <= 0:
            return 10
            
        if duration_minutes <= 480:
            # Linear scaling up to 75 points for duration
            base_score = (duration_minutes / 480.0) * 75
        else:
            # Oversleeping slowly reduces duration efficiency (down to 60 minimum)
            base_score = max(60, 75 - (duration_minutes - 480) * 0.1)

        # 2. Adjustments based on Sleep Phases (Deep sleep, REM sleep, Awake times)
        phase_adjustment = 0
        total_phases = deep_minutes + rem_minutes + (duration_minutes - awake_minutes - deep_minutes - rem_minutes)
        
        if total_phases > 0 and (deep_minutes > 0 or rem_minutes > 0):
            # Deep sleep percentage (ideal is 15-25% of total sleep time)
            deep_pct = (deep_minutes / total_phases) * 100
            if 15 <= deep_pct <= 25:
                phase_adjustment += 10
            elif deep_pct < 10:
                phase_adjustment -= 10

            # REM sleep percentage (ideal is 20-25% of total sleep time)
            rem_pct = (rem_minutes / total_phases) * 100
            if 20 <= rem_pct <= 25:
                phase_adjustment += 10
            elif rem_pct < 10:
                phase_adjustment -= 10

        # Awake time penalty (ideal awake is < 10% of total time in bed)
        if awake_minutes > 0:
            awake_pct = (awake_minutes / (duration_minutes + awake_minutes)) * 100
            if awake_pct > 15:
                phase_adjustment -= min(15, int((awake_pct - 15) * 1.5))

        final_score = int(base_score + phase_adjustment)
        return max(10, min(100, final_score))

    @staticmethod
    def calculate_sleep_quality(score: int) -> str:
        """Map score ranges to quality descriptors."""
        if score >= 90:
            return "Excellent"
        elif score >= 80:
            return "Good"
        elif score >= 70:
            return "Fair"
        elif score >= 50:
            return "Poor"
        else:
            return "Worst"

    @staticmethod
    def create_sleep_session(db: Session, user_id: int, payload: SleepSessionCreate) -> SleepSession:
        """Validate, calculate parameters, save a new sleep session, and cascade aggregate."""
        # Calculate duration in minutes
        time_diff = payload.endTime - payload.startTime
        duration_minutes = int(time_diff.total_seconds() / 60)

        if duration_minutes <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="End time must be after start time"
            )

        # Compute sleep score and sleep quality
        deep_minutes = 0
        light_minutes = 0
        rem_minutes = 0
        awake_minutes = 0

        if payload.stages:
            deep_minutes = payload.stages.deepMinutes or 0
            light_minutes = payload.stages.lightMinutes or 0
            rem_minutes = payload.stages.remMinutes or 0
            awake_minutes = payload.stages.awakeMinutes or 0
        else:
            deep_minutes = payload.deepSleepMinutes or 0
            light_minutes = payload.lightSleepMinutes or 0
            rem_minutes = payload.remSleepMinutes or 0
            awake_minutes = payload.awakeMinutes or 0

        score = SleepService.calculate_sleep_score(
            duration_minutes=duration_minutes,
            deep_minutes=deep_minutes,
            rem_minutes=rem_minutes,
            awake_minutes=awake_minutes
        )
        quality = SleepService.calculate_sleep_quality(score)

        # Save session
        session = SleepSession(
            id=uuid.UUID(payload.id),
            user_id=user_id,
            start_time=payload.startTime,
            end_time=payload.endTime,
            duration_minutes=duration_minutes,
            sleep_score=score,
            sleep_quality=quality,
            is_nap=payload.isNap,
            session_source=payload.source,
            timezone=payload.timezone,
            deep_sleep_minutes=deep_minutes,
            light_sleep_minutes=light_minutes,
            rem_sleep_minutes=rem_minutes,
            awake_minutes=awake_minutes,
            synced_at=datetime.utcnow()
        )

        db.add(session)
        db.commit()
        db.refresh(session)

        # Reschedule inactivity reminder
        from app.services.notification_job_generator import reschedule_inactivity_reminder
        reschedule_inactivity_reminder(db, user_id)

        # Trigger Cascade Aggregation Updates
        wake_date = get_wake_date(session.end_time, session.timezone)
        SleepAggregationService.update_daily_sleep_aggregation(db, user_id, wake_date)
        SleepAggregationService.update_monthly_sleep_aggregation(db, user_id, wake_date.year, wake_date.month)
        SleepAggregationService.update_yearly_sleep_aggregation(db, user_id, wake_date.year)

        # Trigger central User Notification
        try:
            from app.services.notification_service import notification_service
            notification_service.create_notification_sync(
                db=db,
                user_id=user_id,
                title="Sleep Analysis Completed",
                message=f"Your sleep session on {wake_date} has been analyzed. You got a sleep score of {session.sleep_score} ({session.sleep_quality})!",
                notification_type="SLEEP_ANALYSIS",
                priority="normal",
                metadata={
                    "sleep_session_id": str(session.id),
                    "sleep_score": session.sleep_score,
                    "sleep_quality": session.sleep_quality,
                    "wake_date": str(wake_date)
                }
            )
            # Trigger sleep goal / quality achievements
            notification_service.check_and_trigger_sleep_notifications(db, user_id, session)
        except Exception as e:
            print(f"Failed to log sleep analysis user notification: {e}")

        return session

    @staticmethod
    def update_sleep_session(db: Session, user_id: int, session_id: uuid.UUID, payload: SleepSessionUpdate) -> SleepSession:
        """Verify session ownership, perform updates, and cascade aggregate across old and new dates."""
        session = db.query(SleepSession).filter(
            SleepSession.id == session_id,
            SleepSession.deleted_at.is_(None)
        ).first()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sleep session not found"
            )

        if session.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to edit this sleep session"
            )

        # 1. Capture old wake date to clear if it changes
        old_wake_date = get_wake_date(session.end_time, session.timezone)

        # 2. Update fields
        if payload.startTime is not None:
            session.start_time = payload.startTime
        if payload.endTime is not None:
            session.end_time = payload.endTime
        if payload.isNap is not None:
            session.is_nap = payload.isNap
        if payload.timezone is not None:
            session.timezone = payload.timezone
        if payload.source is not None:
            session.session_source = payload.source

        # Update sleep stage minutes (handling nested stages object and flat fallback)
        if payload.stages is not None:
            if payload.stages.deepMinutes is not None:
                session.deep_sleep_minutes = payload.stages.deepMinutes
            if payload.stages.lightMinutes is not None:
                session.light_sleep_minutes = payload.stages.lightMinutes
            if payload.stages.remMinutes is not None:
                session.rem_sleep_minutes = payload.stages.remMinutes
            if payload.stages.awakeMinutes is not None:
                session.awake_minutes = payload.stages.awakeMinutes
        else:
            if payload.deepSleepMinutes is not None:
                session.deep_sleep_minutes = payload.deepSleepMinutes
            if payload.lightSleepMinutes is not None:
                session.light_sleep_minutes = payload.lightSleepMinutes
            if payload.remSleepMinutes is not None:
                session.rem_sleep_minutes = payload.remSleepMinutes
            if payload.awakeMinutes is not None:
                session.awake_minutes = payload.awakeMinutes

        # 3. Recalculate parameters
        time_diff = session.end_time - session.start_time
        session.duration_minutes = int(time_diff.total_seconds() / 60)

        if session.duration_minutes <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="End time must be after start time"
            )

        session.sleep_score = SleepService.calculate_sleep_score(
            duration_minutes=session.duration_minutes,
            deep_minutes=session.deep_sleep_minutes,
            rem_minutes=session.rem_sleep_minutes,
            awake_minutes=session.awake_minutes
        )
        session.sleep_quality = SleepService.calculate_sleep_quality(session.sleep_score)
        session.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(session)

        # Reschedule inactivity reminder
        from app.services.notification_job_generator import reschedule_inactivity_reminder
        reschedule_inactivity_reminder(db, user_id)

        # 4. Trigger Cascade Aggregation Updates for both old and new wake dates
        new_wake_date = get_wake_date(session.end_time, session.timezone)
        
        # Trigger new date
        SleepAggregationService.update_daily_sleep_aggregation(db, user_id, new_wake_date)
        SleepAggregationService.update_monthly_sleep_aggregation(db, user_id, new_wake_date.year, new_wake_date.month)
        SleepAggregationService.update_yearly_sleep_aggregation(db, user_id, new_wake_date.year)

        # Trigger old date if it changed
        if old_wake_date != new_wake_date:
            SleepAggregationService.update_daily_sleep_aggregation(db, user_id, old_wake_date)
            SleepAggregationService.update_monthly_sleep_aggregation(db, user_id, old_wake_date.year, old_wake_date.month)
            SleepAggregationService.update_yearly_sleep_aggregation(db, user_id, old_wake_date.year)

        # Trigger central User Notification
        try:
            from app.services.notification_service import notification_service
            notification_service.create_notification_sync(
                db=db,
                user_id=user_id,
                title="Sleep Analysis Updated",
                message=f"Your sleep session on {new_wake_date} has been updated. You got a sleep score of {session.sleep_score} ({session.sleep_quality})!",
                notification_type="SLEEP_ANALYSIS",
                priority="normal",
                metadata={
                    "sleep_session_id": str(session.id),
                    "sleep_score": session.sleep_score,
                    "sleep_quality": session.sleep_quality,
                    "wake_date": str(new_wake_date)
                }
            )
            # Trigger sleep goal / quality achievements
            notification_service.check_and_trigger_sleep_notifications(db, user_id, session)
        except Exception as e:
            print(f"Failed to log sleep analysis user update notification: {e}")

        return session

    @staticmethod
    def delete_sleep_session(db: Session, user_id: int, session_id: uuid.UUID) -> dict:
        """Soft delete a sleep session and cascade aggregate updates."""
        session = db.query(SleepSession).filter(
            SleepSession.id == session_id,
            SleepSession.deleted_at.is_(None)
        ).first()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sleep session not found"
            )

        if session.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this sleep session"
            )

        # Soft delete
        session.deleted_at = datetime.utcnow()
        db.commit()

        # Trigger Cascade Aggregation Updates
        wake_date = get_wake_date(session.end_time, session.timezone)
        SleepAggregationService.update_daily_sleep_aggregation(db, user_id, wake_date)
        SleepAggregationService.update_monthly_sleep_aggregation(db, user_id, wake_date.year, wake_date.month)
        SleepAggregationService.update_yearly_sleep_aggregation(db, user_id, wake_date.year)

        return {"success": True, "message": "Sleep session soft-deleted successfully"}
