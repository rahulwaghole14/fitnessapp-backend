"""
Feedback Module Integration Tests

This script verifies the correctness and integrity of the Feedback Management Module.
Run this script:
python docs/test_feedback_module.py
"""

import sys
import os
import uuid
from datetime import datetime, timedelta
from pydantic import ValidationError

# Add parent directory to path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal, Base, engine
from app.models.user import User
from app.models.admin import Admin
from app.models.feedback import Feedback, FeedbackCategory, FeedbackStatus
from app.schemas.feedback import (
    FeedbackCreateRequest,
    FeedbackResponse
)
from app.api.admin.schemas import FeedbackStatusUpdate
from app.services.feedback_service import FeedbackService
from app.services.feedback_selector import FeedbackSelector
from app.services.feedback_admin_service import FeedbackAdminService
from app.services.feedback_admin_selector import FeedbackAdminSelector
from app.core.throttles import feedback_rate_limiter
from app.core.permissions import verify_feedback_ownership
from fastapi import HTTPException


def run_tests():
    print("Starting Feedback Module Integration Tests...")
    db = SessionLocal()

    try:
        # 1. Fetch or create a test user
        user = db.query(User).first()
        if not user:
            print("Creating test user...")
            user = User(
                username="test_feedbacker",
                email="feedbacker@example.com",
                password="hashed_secure_password",
                is_verified=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        user_id = user.id
        print(f"Using Test User ID: {user_id} (Username: {user.username})")

        # 2. Fetch or create a test admin
        admin = db.query(Admin).first()
        if not admin:
            print("Creating test admin...")
            admin = Admin(
                username="test_admin",
                email="admin@example.com",
                password_hash="hashed_secure_password",
                is_active=True
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)
        admin_id = admin.id
        print(f"Using Test Admin ID: {admin_id} (Username: {admin.username})")

        # Clean slate for test user
        db.query(Feedback).filter(Feedback.user_id == user_id).delete()
        db.commit()

        # ==========================================
        # TEST 1: Pydantic Validation & Input Sanitization
        # ==========================================
        print("\n--- Running Test 1: Pydantic Validation & Input Sanitization ---")
        
        # Valid Request
        valid_payload = {
            "rating": 5,
            "category": "WORKOUTS",
            "message": "This is a great workout plan with excellent exercises."
        }
        req = FeedbackCreateRequest(**valid_payload)
        assert req.rating == 5
        assert req.category == FeedbackCategory.WORKOUTS
        assert req.message == "This is a great workout plan with excellent exercises."
        print("  [OK] Valid request passes parsing successfully.")

        # Invalid Rating (Too high)
        try:
            FeedbackCreateRequest(rating=6, category="WORKOUTS", message="Short message.")
            raise AssertionError("Invalid rating of 6 should fail Pydantic validation")
        except ValidationError as ve:
            print("  [OK] Rating > 5 correctly failed validation.")

        # Invalid Message (Too short < 10 chars)
        try:
            FeedbackCreateRequest(rating=4, category="WORKOUTS", message="Short")
            raise AssertionError("Message under 10 characters should fail Pydantic validation")
        except ValidationError as ve:
            print("  [OK] Message < 10 chars correctly failed validation.")

        # Input Sanitization (Strips HTML tags & escapes)
        xss_message = "<script>alert(1)</script>This is a safe and clean feedback."
        req_xss = FeedbackCreateRequest(rating=5, category="WORKOUTS", message=xss_message)
        assert "<script>" not in req_xss.message, "HTML tags must be stripped"
        assert req_xss.message == "alert(1)This is a safe and clean feedback.", f"Expected stripped XSS, got: {req_xss.message}"
        print("  [OK] HTML/Script tags successfully stripped from input.")

        # ==========================================
        # TEST 2: Feedback Submission & Service Layer
        # ==========================================
        print("\n--- Running Test 2: Feedback Submission & Service Layer ---")
        
        payload_sub = FeedbackCreateRequest(
            rating=5,
            category=FeedbackCategory.WORKOUTS,
            message="Highly recommended fitness application!",
            device_info={"model": "iPhone 15", "ram": "8GB"},
            app_version="2.0.1",
            platform="iOS"
        )
        
        feedback = FeedbackService.submit_feedback(db=db, user_id=user_id, payload=payload_sub)
        assert feedback.rating == 5
        assert feedback.category == FeedbackCategory.WORKOUTS
        assert feedback.message == "Highly recommended fitness application!"
        assert feedback.device_info == {"model": "iPhone 15", "ram": "8GB"}
        assert feedback.app_version == "2.0.1"
        assert feedback.platform == "iOS"
        assert feedback.status == FeedbackStatus.PENDING
        print(f"  [OK] Feedback submitted and persisted successfully: ID {feedback.id}")

        # ==========================================
        # TEST 3: Rate Limiting Throttling
        # ==========================================
        print("\n--- Running Test 3: Rate Limiting ---")
        # Submit 4 more feedbacks to reach the limit of 5 per hour
        for i in range(4):
            FeedbackService.submit_feedback(
                db=db,
                user_id=user_id,
                payload=FeedbackCreateRequest(
                    rating=4,
                    category=FeedbackCategory.NUTRITION,
                    message=f"Valid message placeholder count number {i}."
                )
            )
        
        # Verify 5 feedbacks are now in the DB for this user
        count = db.query(Feedback).filter(Feedback.user_id == user_id).count()
        assert count == 5, f"Expected 5 feedbacks, got {count}"
        print("  [OK] Submitted 5 feedbacks within the hour.")

        # 6th submission should raise 429 Too Many Requests
        try:
            feedback_rate_limiter(user_id=user_id, db=db)
            raise AssertionError("6th feedback submission within the hour should raise HTTPException 429")
        except HTTPException as he:
            assert he.status_code == 429, f"Expected status code 429, got {he.status_code}"
            assert "Rate limit exceeded" in he.detail
            print(f"  [OK] Rate limit correctly enforced: {he.detail}")

        # ==========================================
        # TEST 4: Read Selectors & History
        # ==========================================
        print("\n--- Running Test 4: Query Selectors & History ---")
        
        # User history
        history = FeedbackSelector.get_user_feedback_history(db=db, user_id=user_id)
        assert len(history) == 5, f"Expected history to return 5 feedbacks, got {len(history)}"
        print("  [OK] History selector fetched all 5 feedbacks.")

        # Details owner check
        first_feedback = history[0]
        verified_fb = verify_feedback_ownership(feedback_id=first_feedback.id, user_id=user_id, db=db)
        assert verified_fb.id == first_feedback.id
        print("  [OK] Ownership verification check passed for owner.")

        # Details non-owner check (simulating different user ID)
        try:
            verify_feedback_ownership(feedback_id=first_feedback.id, user_id=99999, db=db)
            raise AssertionError("Accessing another user's feedback details should raise 403 Forbidden")
        except HTTPException as he:
            assert he.status_code == 403, f"Expected status code 403, got {he.status_code}"
            print("  [OK] Details ownership check correctly raises 403 for unauthorized users.")

        # ==========================================
        # TEST 5: Admin Management & Status Updates
        # ==========================================
        print("\n--- Running Test 5: Admin Status Updates & Notes ---")
        
        # Admin listing
        admin_list = FeedbackAdminSelector.get_admin_feedback_list(
            db=db,
            page=1,
            limit=20,
            category=FeedbackCategory.WORKOUTS
        )
        assert admin_list["total"] >= 1
        print(f"  [OK] Admin selector listing works correctly. Category filtered 'WORKOUTS' total count: {admin_list['total']}")

        # Admin patch status and notes
        patched_fb = FeedbackAdminService.update_feedback_status(
            db=db,
            feedback_id=first_feedback.id,
            new_status=FeedbackStatus.RESOLVED,
            admin_notes="Issue resolved in app version 2.0.2",
            admin_id=admin_id
        )
        assert patched_fb.status == FeedbackStatus.RESOLVED
        assert patched_fb.admin_notes == "Issue resolved in app version 2.0.2"
        print("  [OK] Admin patched status and added internal notes successfully.")

        # ==========================================
        # TEST 6: Analytics Summary & Cached Analytics
        # ==========================================
        print("\n--- Running Test 6: Analytics Calculations & Caching ---")
        
        # Invalidate/Pre-run cache task
        from app.tasks import update_feedback_analytics_cache_task, ANALYTICS_CACHE
        ANALYTICS_CACHE["analytics"] = None
        
        update_feedback_analytics_cache_task()
        
        # Fetch analytics
        analytics = FeedbackAdminSelector.get_analytics_cached(db)
        assert analytics["total_feedbacks"] == 5, f"Expected 5 total feedbacks in analytics, got {analytics['total_feedbacks']}"
        assert analytics["pending_count"] == 4, f"Expected 4 pending, got {analytics['pending_count']}"
        assert analytics["resolved_count"] == 1, f"Expected 1 resolved, got {analytics['resolved_count']}"
        assert analytics["category_distribution"]["WORKOUTS"] == 1
        assert analytics["category_distribution"]["NUTRITION"] == 4
        print(f"  [OK] Analytics summary calculated correctly: {analytics}")

        print("\nALL FEEDBACK MODULE TESTS PASSED SUCCESSFULLY!")

    except AssertionError as ae:
        print(f"\n[FAIL] Test Assertion Failed: {ae}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[FAIL] Test Failed with unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Clean up database records
        print("\nCleaning up test records from database...")
        db.query(Feedback).filter(Feedback.user_id == user_id).delete()
        db.commit()
        db.close()
        print("Cleaned up successfully.")


if __name__ == "__main__":
    run_tests()
