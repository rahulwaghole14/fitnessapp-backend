from datetime import date, timedelta, datetime
from typing import List, Tuple, Dict, Any
from sqlalchemy.orm import Session
from app.models.sleep import UserDailySleep, UserMonthlySleep, UserYearlySleep, SleepSession
from app.schemas.sleep import WeeklySleepData, SleepAnalyticsResponse


class SleepAnalyticsService:

    @staticmethod
    def get_sleep_streaks(db: Session, user_id: int) -> Tuple[int, int]:
        """Calculate current active streak and longest tracked sleep streak for a user."""
        daily_records = db.query(UserDailySleep).filter(
            UserDailySleep.user_id == user_id
        ).order_by(UserDailySleep.sleep_date.desc()).all()

        if not daily_records:
            return 0, 0

        dates = [d.sleep_date for d in daily_records]
        
        # Check if current streak is active (logged either today or yesterday)
        today = date.today()
        yesterday = today - timedelta(days=1)
        has_recent = (dates[0] == today or dates[0] == yesterday)

        # 1. Compute Active Current Streak
        current_streak = 0
        if has_recent:
            current_streak = 1
            curr_check = dates[0]
            for d in dates[1:]:
                if d == curr_check - timedelta(days=1):
                    current_streak += 1
                    curr_check = d
                elif d == curr_check:
                    # Skip duplicate dates
                    pass
                else:
                    break

        # 2. Compute Longest Tracked Streak
        sorted_dates = sorted(list(set(dates)))
        longest_streak = 0
        current_run = 0
        prev_date = None

        for d in sorted_dates:
            if prev_date is None:
                current_run = 1
            elif d == prev_date + timedelta(days=1):
                current_run += 1
            else:
                if current_run > longest_streak:
                    longest_streak = current_run
                current_run = 1
            prev_date = d
            
        if current_run > longest_streak:
            longest_streak = current_run

        return current_streak, longest_streak

    @staticmethod
    def get_weekly_sleep_stats(db: Session, user_id: int) -> List[WeeklySleepData]:
        """Fetch daily sleep records for the last 7 wake days."""
        today = date.today()
        seven_days_ago = today - timedelta(days=7)

        records = db.query(UserDailySleep).filter(
            UserDailySleep.user_id == user_id,
            UserDailySleep.sleep_date >= seven_days_ago,
            UserDailySleep.sleep_date <= today
        ).order_by(UserDailySleep.sleep_date.asc()).all()

        weekly_data = []
        for r in records:
            weekly_data.append(WeeklySleepData(
                sleep_date=r.sleep_date,
                total_sleep_minutes=r.total_sleep_minutes,
                sessions_count=r.total_sessions,
                sleep_score=r.avg_sleep_score,
                deep_sleep_minutes=r.total_deep_sleep,
                rem_sleep_minutes=r.total_rem_sleep,
                light_sleep_minutes=r.total_light_sleep
            ))

        return weekly_data

    @staticmethod
    def get_dashboard_analytics(db: Session, user_id: int) -> SleepAnalyticsResponse:
        """Fetch general averages, weekly charts, and sleep streaks for user dashboard."""
        daily_records = db.query(UserDailySleep).filter(
            UserDailySleep.user_id == user_id
        ).all()

        total_sessions = sum(d.total_sessions for d in daily_records) if daily_records else 0
        days_tracked = len(daily_records)
        avg_minutes = sum(d.total_sleep_minutes for d in daily_records) / max(1, days_tracked)
        avg_score = sum(d.avg_sleep_score for d in daily_records) / max(1, days_tracked)

        current_streak, longest_streak = SleepAnalyticsService.get_sleep_streaks(db, user_id)
        weekly_history = SleepAnalyticsService.get_weekly_sleep_stats(db, user_id)

        return SleepAnalyticsResponse(
            average_sleep_minutes=avg_minutes,
            average_sleep_score=avg_score,
            total_sessions=total_sessions,
            days_tracked=days_tracked,
            sleep_streak_current=current_streak,
            sleep_streak_longest=longest_streak,
            weekly_history=weekly_history
        )
