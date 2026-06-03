import pytz
from datetime import datetime, date, time, timedelta
from typing import List, Optional, Tuple
from sqlalchemy import text, and_, extract
from sqlalchemy.orm import Session
from app.models.sleep import SleepSession, UserDailySleep, UserMonthlySleep, UserYearlySleep


def get_wake_date(end_time: datetime, timezone_str: str) -> date:
    """Convert a UTC/timezone-aware end_time to the target timezone and extract the date."""
    try:
        tz = pytz.timezone(timezone_str)
    except Exception:
        tz = pytz.UTC

    if end_time.tzinfo is None:
        localized_dt = pytz.UTC.localize(end_time).astimezone(tz)
    else:
        localized_dt = end_time.astimezone(tz)

    return localized_dt.date()


def average_times(times_list: List[time]) -> Optional[time]:
    """Calculate the circular average of a list of time objects, shifted relative to 12:00 PM (noon)."""
    if not times_list:
        return None

    total_minutes_shifted = 0
    for t in times_list:
        mins = t.hour * 60 + t.minute
        # Shift relative to 12:00 PM (720 minutes from midnight)
        shifted = mins - 720
        if shifted < 0:
            shifted += 1440
        total_minutes_shifted += shifted

    avg_shifted = total_minutes_shifted / len(times_list)
    avg_mins = (avg_shifted + 720) % 1440

    hour = int(avg_mins // 60)
    minute = int(avg_mins % 60)
    return time(hour=hour, minute=minute)


class SleepAggregationService:

    @staticmethod
    def update_daily_sleep_aggregation(db: Session, user_id: int, wake_date: date) -> Optional[UserDailySleep]:
        """Aggregate SleepSessions for a specific wake_date and upsert into UserDailySleep."""
        # Query raw sessions in a window around the wake date for efficiency
        start_search = datetime.combine(wake_date - timedelta(days=2), datetime.min.time())
        end_search = datetime.combine(wake_date + timedelta(days=2), datetime.max.time())

        sessions = db.query(SleepSession).filter(
            SleepSession.user_id == user_id,
            SleepSession.deleted_at.is_(None),
            SleepSession.end_time >= start_search,
            SleepSession.end_time <= end_search
        ).all()

        # Filter by localized wake date
        day_sessions = [
            s for s in sessions if get_wake_date(s.end_time, s.timezone) == wake_date
        ]

        # Find existing daily record
        daily_record = db.query(UserDailySleep).filter(
            UserDailySleep.user_id == user_id,
            UserDailySleep.sleep_date == wake_date
        ).first()

        if not day_sessions:
            # If no active sessions exist for this date, delete the daily record
            if daily_record:
                db.delete(daily_record)
                db.commit()
            return None

        # Compute aggregation metrics
        total_sleep_minutes = sum(s.duration_minutes for s in day_sessions)
        total_sessions = len(day_sessions)
        avg_sleep_score = sum(s.sleep_score for s in day_sessions) / total_sessions
        total_deep_sleep = sum(s.deep_sleep_minutes for s in day_sessions)
        total_rem_sleep = sum(s.rem_sleep_minutes for s in day_sessions)
        total_light_sleep = sum(s.light_sleep_minutes for s in day_sessions)

        # Average bedtime and wake times
        bed_times = []
        wake_times = []
        for s in day_sessions:
            try:
                tz = pytz.timezone(s.timezone)
            except Exception:
                tz = pytz.UTC

            local_start = s.start_time.astimezone(tz) if s.start_time.tzinfo else pytz.UTC.localize(s.start_time).astimezone(tz)
            local_end = s.end_time.astimezone(tz) if s.end_time.tzinfo else pytz.UTC.localize(s.end_time).astimezone(tz)
            bed_times.append(local_start.time())
            wake_times.append(local_end.time())

        bed_time_avg = average_times(bed_times)
        wake_time_avg = average_times(wake_times)

        # Calculate a consistency score (e.g. baseline 100, deduct points if sleep duration fluctuates highly from ideal 8 hours)
        # or if multiple sleep sessions are irregular
        duration_diff = abs(total_sleep_minutes - 480)  # 8 hours is target
        consistency = max(50, 100 - int(duration_diff * 0.1))

        if daily_record:
            # Update existing record
            daily_record.total_sleep_minutes = total_sleep_minutes
            daily_record.total_sessions = total_sessions
            daily_record.avg_sleep_score = avg_sleep_score
            daily_record.total_deep_sleep = total_deep_sleep
            daily_record.total_rem_sleep = total_rem_sleep
            daily_record.total_light_sleep = total_light_sleep
            daily_record.sleep_consistency_score = consistency
            daily_record.bed_time_avg = bed_time_avg
            daily_record.wake_time_avg = wake_time_avg
            daily_record.updated_at = datetime.utcnow()
        else:
            # Create new record
            daily_record = UserDailySleep(
                user_id=user_id,
                sleep_date=wake_date,
                total_sleep_minutes=total_sleep_minutes,
                total_sessions=total_sessions,
                avg_sleep_score=avg_sleep_score,
                total_deep_sleep=total_deep_sleep,
                total_rem_sleep=total_rem_sleep,
                total_light_sleep=total_light_sleep,
                sleep_consistency_score=consistency,
                bed_time_avg=bed_time_avg,
                wake_time_avg=wake_time_avg,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(daily_record)

        db.commit()
        db.refresh(daily_record)
        return daily_record

    @staticmethod
    def update_monthly_sleep_aggregation(db: Session, user_id: int, year: int, month: int) -> Optional[UserMonthlySleep]:
        """Aggregate UserDailySleep records for a specific year & month and upsert into UserMonthlySleep."""
        # Fetch daily records for this user, year, and month
        daily_records = db.query(UserDailySleep).filter(
            UserDailySleep.user_id == user_id,
            extract('year', UserDailySleep.sleep_date) == year,
            extract('month', UserDailySleep.sleep_date) == month
        ).all()

        monthly_record = db.query(UserMonthlySleep).filter(
            UserMonthlySleep.user_id == user_id,
            UserMonthlySleep.year == year,
            UserMonthlySleep.month == month
        ).first()

        if not daily_records:
            if monthly_record:
                db.delete(monthly_record)
                db.commit()
            return None

        # Compute monthly metrics
        total_sleep_minutes = sum(d.total_sleep_minutes for d in daily_records)
        total_sessions = sum(d.total_sessions for d in daily_records)
        days_tracked = len(daily_records)
        avg_sleep_minutes = total_sleep_minutes / days_tracked
        avg_sleep_score = sum(d.avg_sleep_score for d in daily_records) / days_tracked
        best_sleep_score = int(max(d.avg_sleep_score for d in daily_records))
        worst_sleep_score = int(min(d.avg_sleep_score for d in daily_records))
        avg_deep_sleep = sum(d.total_deep_sleep for d in daily_records) / days_tracked
        avg_rem_sleep = sum(d.total_rem_sleep for d in daily_records) / days_tracked
        sleep_consistency_score = sum(d.sleep_consistency_score for d in daily_records) / days_tracked

        if monthly_record:
            monthly_record.total_sleep_minutes = total_sleep_minutes
            monthly_record.avg_sleep_minutes = avg_sleep_minutes
            monthly_record.avg_sleep_score = avg_sleep_score
            monthly_record.total_sessions = total_sessions
            monthly_record.best_sleep_score = best_sleep_score
            monthly_record.worst_sleep_score = worst_sleep_score
            monthly_record.avg_deep_sleep = avg_deep_sleep
            monthly_record.avg_rem_sleep = avg_rem_sleep
            monthly_record.sleep_consistency_score = sleep_consistency_score
            monthly_record.days_tracked = days_tracked
            monthly_record.updated_at = datetime.utcnow()
        else:
            monthly_record = UserMonthlySleep(
                user_id=user_id,
                year=year,
                month=month,
                total_sleep_minutes=total_sleep_minutes,
                avg_sleep_minutes=avg_sleep_minutes,
                avg_sleep_score=avg_sleep_score,
                total_sessions=total_sessions,
                best_sleep_score=best_sleep_score,
                worst_sleep_score=worst_sleep_score,
                avg_deep_sleep=avg_deep_sleep,
                avg_rem_sleep=avg_rem_sleep,
                sleep_consistency_score=sleep_consistency_score,
                days_tracked=days_tracked,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(monthly_record)

        db.commit()
        db.refresh(monthly_record)
        return monthly_record

    @staticmethod
    def update_yearly_sleep_aggregation(db: Session, user_id: int, year: int) -> Optional[UserYearlySleep]:
        """Aggregate UserMonthlySleep records for a specific year and upsert into UserYearlySleep."""
        monthly_records = db.query(UserMonthlySleep).filter(
            UserMonthlySleep.user_id == user_id,
            UserMonthlySleep.year == year
        ).all()

        yearly_record = db.query(UserYearlySleep).filter(
            UserYearlySleep.user_id == user_id,
            UserYearlySleep.year == year
        ).first()

        if not monthly_records:
            if yearly_record:
                db.delete(yearly_record)
                db.commit()
            return None

        # Compute yearly metrics
        total_sleep_minutes = sum(m.total_sleep_minutes for m in monthly_records)
        total_sessions = sum(m.total_sessions for m in monthly_records)
        days_tracked = sum(m.days_tracked for m in monthly_records)
        months_count = len(monthly_records)
        avg_sleep_minutes = total_sleep_minutes / max(1, days_tracked)
        avg_sleep_score = sum(m.avg_sleep_score for m in monthly_records) / months_count
        best_month_score = max(m.avg_sleep_score for m in monthly_records)
        worst_month_score = min(m.avg_sleep_score for m in monthly_records)
        sleep_consistency_score = sum(m.sleep_consistency_score for m in monthly_records) / months_count

        if yearly_record:
            yearly_record.total_sleep_minutes = total_sleep_minutes
            yearly_record.avg_sleep_minutes = avg_sleep_minutes
            yearly_record.avg_sleep_score = avg_sleep_score
            yearly_record.total_sessions = total_sessions
            yearly_record.days_tracked = days_tracked
            yearly_record.best_month_score = best_month_score
            yearly_record.worst_month_score = worst_month_score
            yearly_record.sleep_consistency_score = sleep_consistency_score
            yearly_record.updated_at = datetime.utcnow()
        else:
            yearly_record = UserYearlySleep(
                user_id=user_id,
                year=year,
                total_sleep_minutes=total_sleep_minutes,
                avg_sleep_minutes=avg_sleep_minutes,
                avg_sleep_score=avg_sleep_score,
                total_sessions=total_sessions,
                days_tracked=days_tracked,
                best_month_score=best_month_score,
                worst_month_score=worst_month_score,
                sleep_consistency_score=sleep_consistency_score,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(yearly_record)

        db.commit()
        db.refresh(yearly_record)
        return yearly_record

    @staticmethod
    def rebuild_sleep_aggregations(db: Session, user_id: int):
        """Completely rebuild user aggregates (daily, monthly, yearly) from raw sleep sessions."""
        # 1. Clear all old summaries for the user
        db.query(UserYearlySleep).filter(UserYearlySleep.user_id == user_id).delete()
        db.query(UserMonthlySleep).filter(UserMonthlySleep.user_id == user_id).delete()
        db.query(UserDailySleep).filter(UserDailySleep.user_id == user_id).delete()
        db.commit()

        # 2. Get all active sessions
        sessions = db.query(SleepSession).filter(
            SleepSession.user_id == user_id,
            SleepSession.deleted_at.is_(None)
        ).all()

        if not sessions:
            return

        # 3. Rebuild Daily Summaries
        wake_dates = set()
        for s in sessions:
            wake_date = get_wake_date(s.end_time, s.timezone)
            wake_dates.add(wake_date)

        for w_date in sorted(wake_dates):
            SleepAggregationService.update_daily_sleep_aggregation(db, user_id, w_date)

        # 4. Rebuild Monthly Summaries
        months = set()
        for w_date in wake_dates:
            months.add((w_date.year, w_date.month))

        for yr, mth in sorted(months):
            SleepAggregationService.update_monthly_sleep_aggregation(db, user_id, yr, mth)

        # 5. Rebuild Yearly Summaries
        years = set(yr for yr, _ in months)
        for yr in sorted(years):
            SleepAggregationService.update_yearly_sleep_aggregation(db, user_id, yr)
