import uuid
from datetime import datetime, timedelta, date, time
import pytz
from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine, Base
from app.models.user import User
from app.models.sleep import SleepSession, UserDailySleep, UserMonthlySleep, UserYearlySleep
from app.models.refresh_token import RefreshToken
from app.models.payment import Payment
from app.models.subscription import Subscription
from app.models.subscription_plans import Plan
from app.models.workout import Workout
from app.models.meal import Meal
from app.models.bmi_classification import BMIClassification
from app.models.explore_activity import ExploreActivity
from app.models.user_activity_log import UserActivityLog
from app.schemas.sleep import SleepSessionCreate, SleepSessionUpdate, SleepStages
from app.services.sleep_service import SleepService
from app.services.sleep_aggregation_service import SleepAggregationService, get_wake_date
from app.services.sleep_analytics_service import SleepAnalyticsService

# Ensure all tables are created
Base.metadata.create_all(bind=engine)


def run_tests():
    print("Starting Sleep Module Verification Tests...")
    db: Session = SessionLocal()

    try:
        # 1. Fetch or create a test user
        user = db.query(User).first()
        if not user:
            print("No user found in database. Creating a temporary test user...")
            user = User(
                username="test_sleeper",
                email="sleeper@example.com",
                password="hashed_secure_password",
                is_verified=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        user_id = user.id
        print(f"Using Test User ID: {user_id} (Username: {user.username})")

        # Clean slate for test user
        db.query(SleepSession).filter(SleepSession.user_id == user_id).delete()
        db.query(UserDailySleep).filter(UserDailySleep.user_id == user_id).delete()
        db.query(UserMonthlySleep).filter(UserMonthlySleep.user_id == user_id).delete()
        db.query(UserYearlySleep).filter(UserYearlySleep.user_id == user_id).delete()
        db.commit()

        # 2. Test Sleep Session Creation
        session_id = str(uuid.uuid4())
        # Overnight sleep session: relative to today's date to verify active streaks robustly
        tz_kolkata = pytz.timezone("Asia/Kolkata")
        
        today_date = date.today()
        yesterday_date = today_date - timedelta(days=1)
        
        start_dt = datetime.combine(yesterday_date, time(22, 30, 0)).replace(tzinfo=pytz.UTC)
        end_dt = datetime.combine(today_date, time(6, 0, 0)).replace(tzinfo=pytz.UTC)

        payload = SleepSessionCreate(
            id=session_id,
            startTime=start_dt,
            endTime=end_dt,
            isNap=False,
            timezone="Asia/Kolkata",
            source="wearable",
            stages=SleepStages(
                awakeMinutes=20,
                lightMinutes=280,
                deepMinutes=90,
                remMinutes=60
            ),
            durationMinutes=450,
            qualityScore=85,
            synced=False,
            updatedAt=datetime.combine(today_date, time(6, 1, 0)).replace(tzinfo=pytz.UTC)
        )

        print("Creating overnight sleep session...")
        session = SleepService.create_sleep_session(db, user_id, payload)
        
        # Assertions
        assert session.duration_minutes == 450, f"Expected 450 minutes duration, got {session.duration_minutes}"
        assert session.sleep_score > 0, "Sleep score should be calculated and greater than 0"
        assert session.sleep_quality in ["Excellent", "Good", "Fair", "Poor", "Worst"], f"Invalid sleep quality: {session.sleep_quality}"
        print(f"Sleep Session Created: Duration={session.duration_minutes}m, Score={session.sleep_score}, Quality={session.sleep_quality}")

        # 3. Test Sleep Date Rule (Wake Date as Statistical date)
        expected_wake_date = today_date
        actual_wake_date = get_wake_date(session.end_time, session.timezone)
        assert actual_wake_date == expected_wake_date, f"Expected wake date {expected_wake_date}, got {actual_wake_date}"
        print(f"Timezone-aware Wake Date conversion correct: Resolved to {actual_wake_date}")

        # 4. Test Automated Cascade Aggregation
        # Verify Daily Summary
        daily_record = db.query(UserDailySleep).filter(
            UserDailySleep.user_id == user_id,
            UserDailySleep.sleep_date == expected_wake_date
        ).first()
        
        assert daily_record is not None, "Daily aggregate should be automatically created"
        assert daily_record.total_sleep_minutes == 450, f"Expected 450 total minutes, got {daily_record.total_sleep_minutes}"
        assert daily_record.total_sessions == 1, f"Expected 1 session, got {daily_record.total_sessions}"
        assert daily_record.total_deep_sleep == 90, f"Expected 90 deep sleep minutes, got {daily_record.total_deep_sleep}"
        print(f"Daily Aggregation verified successfully for date {expected_wake_date}")

        # Verify Monthly Summary
        monthly_record = db.query(UserMonthlySleep).filter(
            UserMonthlySleep.user_id == user_id,
            UserMonthlySleep.year == expected_wake_date.year,
            UserMonthlySleep.month == expected_wake_date.month
        ).first()
        assert monthly_record is not None, "Monthly aggregate should be automatically created"
        assert monthly_record.total_sleep_minutes == 450, f"Expected 450 monthly total minutes, got {monthly_record.total_sleep_minutes}"
        assert monthly_record.days_tracked == 1, f"Expected 1 day tracked, got {monthly_record.days_tracked}"
        print(f"Monthly Aggregation verified successfully for {expected_wake_date.year}-{expected_wake_date.month:02d}")

        # Verify Yearly Summary
        yearly_record = db.query(UserYearlySleep).filter(
            UserYearlySleep.user_id == user_id,
            UserYearlySleep.year == expected_wake_date.year
        ).first()
        assert yearly_record is not None, "Yearly aggregate should be automatically created"
        assert yearly_record.total_sleep_minutes == 450, f"Expected 450 yearly total minutes, got {yearly_record.total_sleep_minutes}"
        print(f"Yearly Aggregation verified successfully for {expected_wake_date.year}")

        # 5. Test Update and Re-aggregation
        # Let's extend the sleep session end time by 1 hour (adds 60 minutes)
        print("Updating sleep session end time (+1 hour)...")
        update_payload = SleepSessionUpdate(
            endTime=end_dt + timedelta(hours=1),
            stages=SleepStages(
                deepMinutes=110,
                lightMinutes=280,
                remMinutes=60,
                awakeMinutes=20
            )
        )
        
        updated_session = SleepService.update_sleep_session(db, user_id, session.id, update_payload)
        
        # Verify Daily Summary updated
        db.refresh(daily_record)
        assert updated_session.duration_minutes == 510, f"Expected updated duration of 510m, got {updated_session.duration_minutes}"
        assert daily_record.total_sleep_minutes == 510, f"Expected updated daily aggregate 510m, got {daily_record.total_sleep_minutes}"
        assert daily_record.total_deep_sleep == 110, f"Expected updated daily deep sleep 110m, got {daily_record.total_deep_sleep}"
        print("Sleep Session Update and Re-aggregation verified successfully")

        # 6. Test Analytics & Streaks
        print("Testing Analytics & Streak calculations...")
        # Create another sleep session for the previous wake date (2026-05-25) to test streaks
        session_id_2 = str(uuid.uuid4())
        payload_2 = SleepSessionCreate(
            id=session_id_2,
            startTime=start_dt - timedelta(days=1),
            endTime=end_dt - timedelta(days=1),
            isNap=False,
            timezone="Asia/Kolkata",
            source="wearable",
            deepSleepMinutes=80,
            lightSleepMinutes=300,
            remSleepMinutes=60,
            awakeMinutes=10
        )
        SleepService.create_sleep_session(db, user_id, payload_2)

        # Get analytics
        analytics = SleepAnalyticsService.get_dashboard_analytics(db, user_id)
        assert analytics.days_tracked == 2, f"Expected 2 days tracked, got {analytics.days_tracked}"
        assert analytics.sleep_streak_current > 0, f"Expected active current streak, got {analytics.sleep_streak_current}"
        assert analytics.sleep_streak_longest >= analytics.sleep_streak_current
        print(f"Analytics verified: Current Streak={analytics.sleep_streak_current}, Longest Streak={analytics.sleep_streak_longest}")

        # 7. Test Soft Delete & Aggregation Cleanup
        print("Testing Soft Delete...")
        # Soft delete the second session
        SleepService.delete_sleep_session(db, user_id, uuid.UUID(session_id_2))
        
        # Ensure session is soft deleted
        deleted_session = db.query(SleepSession).filter(SleepSession.id == uuid.UUID(session_id_2)).first()
        assert deleted_session.deleted_at is not None, "Session should have deleted_at timestamp set"
        
        # Ensure daily record for previous day is deleted/cleared since no active sessions remain
        deleted_daily_record = db.query(UserDailySleep).filter(
            UserDailySleep.user_id == user_id,
            UserDailySleep.sleep_date == yesterday_date
        ).first()
        assert deleted_daily_record is None, "Daily aggregate should be deleted after soft deleting all sessions for that day"
        print("Soft Delete and Aggregation cleanup verified successfully")

        print("ALL TESTS PASSED SUCCESSFULLY! The Sleep Module is fully robust and consistent.")

    except AssertionError as ae:
        print(f"Assertion Failed: {ae}")
    except Exception as e:
        print(f"Unexpected Error during tests: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    run_tests()
