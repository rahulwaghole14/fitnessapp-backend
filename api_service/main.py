from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import random
from sqlalchemy import func, extract, text, and_
from fitness_service import FitnessActivityService
import calendar
from database import engine, SessionLocal
from models import *
from schemas import *
# from schemas import RegisterSchema, VerifyOTPSchema, LoginSchema, ResendOTPSchema,ForgotPasswordEmailSchema
from emailjs_utils import send_otp_email

app = FastAPI()
Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# # REGISTER → SEND OTP
# @app.post("/register")
# def register(data: RegisterSchema, db: Session = Depends(get_db)):
#     if db.query(User).filter(User.email == data.email).first():
#         raise HTTPException(status_code=400, detail="Email already exists")
#
#     otp = str(random.randint(100000, 999999))
#
#     user = User(
#         email=data.email,
#         password=data.password,
#         otp=otp,
#         otp_created_at=datetime.utcnow(),  # Store OTP creation time for expiration check
#         is_verified=False
#     )
#     db.add(user)
#     db.commit()
#     print(f"OTP for {data.email}: {otp}")
#
#     try:
#         send_otp_email(data.email, otp)
#     except Exception as e:
#         print(f"Email sending failed: {e}")
#
#     return {"message": "OTP sent"}
#
#
# # VERIFY OTP
# @app.post("/verify-otp")
# def verify_otp(data: VerifyOTPSchema, db: Session = Depends(get_db)):
#     user = db.query(User).filter(User.email == data.email).first()
#
#     if not user or user.otp != data.otp:
#         raise HTTPException(status_code=400, detail="Invalid OTP")
#
#     # Check OTP expiration (60 seconds validity)
#     if user.otp_created_at:
#         time_elapsed = datetime.utcnow() - user.otp_created_at
#         if time_elapsed.total_seconds() > 60:  # OTP expires after 60 seconds
#             raise HTTPException(
#                 status_code=400,
#                 detail="OTP expired. Please request a new OTP."
#             )
#
#     user.is_verified = True
#     user.otp = None
#     user.otp_created_at = None  # Clear OTP timestamp after successful verification
#     db.commit()
#
#     return {"message": "Verification successful"}
#
#
# # RESEND OTP
# @app.post("/resend-otp")
# def resend_otp(data: ResendOTPSchema, db: Session = Depends(get_db)):

#     user = db.query(User).filter(User.email == data.email).first()
#
#     if not user:
#         raise HTTPException(status_code=404, detail="Email not found. Please register first.")
#
#     # Generate new OTP
#     new_otp = str(random.randint(100000, 999999))
#
#     # Update existing user record with new OTP and fresh timestamp
#     user.otp = new_otp
#     user.otp_created_at = datetime.utcnow()  # Reset expiration timer
#     db.commit()
#
#     print(f"New OTP for {data.email}: {new_otp}")
#
#     # Send new OTP via email using existing EmailJS function
#     try:
#         send_otp_email(data.email, new_otp)
#     except Exception as e:
#         print(f"Email sending failed: {e}")
#         # Don't fail the operation if email fails, user can still verify with printed OTP
#
#     return {"message": "New OTP sent to your email"}
#

@app.post("/register")
def register(user: RegisterSchema,
            db: Session = Depends(get_db)
            ):

    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        username=user.username,
        email=user.email,
        password=user.password  # plain text for now
    )

    db.add(new_user)
    db.commit()

    return {"message": "Registration successful"}


# FORGOT PASSWORD - SEND OTP
@app.post("/forgot-password/send-otp")
def forgot_password_send_otp(user: ForgotPasswordEmailSchema, db: Session = Depends(get_db)):

    user = db.query(User).filter(User.email == user.email).first()

    if not user:
        raise HTTPException(status_code=404, detail="Email not found. Please check your email or register.")

    # Generate new OTP for password reset
    new_otp = str(random.randint(100000, 999999))

    # Update existing user record with new OTP and fresh timestamp
    user.otp = new_otp
    user.otp_created_at = datetime.utcnow()  # Reset expiration timer for password reset
    db.commit()

    print(f"Forgot Password OTP for {user.email}: {new_otp}")

    # Send new OTP via email using existing EmailJS function
    try:
        send_otp_email(user.email, new_otp)
    except Exception as e:
        print(f"Email sending failed: {e}")

    return {"message": "Password reset OTP sent to your email"}


# FORGOT PASSWORD - VERIFY OTP
@app.post("/forgot-password/verify-otp")
def forgot_password_verify_otp(data: ForgotPasswordVerifySchema, db: Session = Depends(get_db)):

    user = db.query(User).filter(User.email == data.email).first()

    if not user or user.otp != data.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    # Check OTP expiration (300 seconds validity) - reuse existing logic
    if user.otp_created_at:
        time_elapsed = datetime.utcnow() - user.otp_created_at
        if time_elapsed.total_seconds() > 300:  # OTP expires after 60 seconds
            raise HTTPException(
                status_code=400,
                detail="OTP expired. Please request a new OTP."
            )
    # OTP is valid - allow password reset
    return {"message": "OTP verified successfully. You can now reset your password."}


# FORGOT PASSWORD - RESET PASSWORD
@app.post("/forgot-password/reset-password")
def forgot_password_reset_password(data: ForgotPasswordResetSchema, db: Session = Depends(get_db)):

    user = db.query(User).filter(User.email == data.email).first()

    if not user or user.otp != data.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    # Re-check OTP expiration (300 seconds validity) for security
    if user.otp_created_at:
        time_elapsed = datetime.utcnow() - user.otp_created_at
        if time_elapsed.total_seconds() > 300:  # OTP expires after 60 seconds
            raise HTTPException(
                status_code=400,
                detail="OTP expired. Please request a new OTP."
            )

    user.password = data.new_password

    # Clear OTP and timestamp after successful password reset
    user.otp = None
    user.otp_created_at = None

    db.commit()

    return {"message": "Password reset successfully. You can now login with your new password."}


# LOGIN
@app.post("/login")
def login(user: LoginSchema,
          db: Session = Depends(get_db)
          ):
    # db: Session = get_db()

    db_user = db.query(User).filter(
        User.email == user.email,
        User.password == user.password

    ).first()

    if not db_user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return {"message": "Login successful", "username": {
            "user_id": db_user.id,
            "username": db_user.username,
            "email": db_user.email,
                }
            }

@app.put("/setup-profile")
def update_profile(data: ProfileSetupSchema, db: Session = Depends(get_db)):

    user = db.query(User).filter(User.email == data.email).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    #Update fields
    user.gender = data.gender
    user.age = data.age
    user.height = data.height
    user.weight = data.weight
    user.bmi = data.bmi
    user.weight_goal = data.weight_goal
    user.activity_level = data.activity_level

    db.commit()
    db.refresh(user)

    return {
        "message": "Profile updated successfully",
        "email": user.email,
        "gender": user.gender,
        "age": user.age,
        "weight": user.weight,
        "height": user.height,
        "bmi": user.bmi,
        "weight_goal": user.weight_goal,
        "activity_level": user.activity_level,
    }

@app.get("/get-profile/{email}")
def get_profile(email: str, db: Session = Depends(get_db)):

    user = db.query(User).filter(User.email == email).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "message":"profile Get successfully",
        "email": user.email,
        "gender": user.gender,
        "age": user.age,
        "height": user.height,
        "weight": user.weight,
        "bmi": user.bmi,
        "weight_goal": user.weight_goal,
        "activity_level": user.activity_level
    }

@app.post("/activity/daily")
def store_daily_activity(
        data: DailyActivityRequest,
        db: Session = Depends(get_db)
):
    """
    Store user daily activity and automatically trigger monthly & Yearly summarization
    """

    # Validate input data
    if data.steps < 0 or data.distance_km < 0 or data.calories < 0 or data.active_minutes < 0:
        raise HTTPException(
            status_code=400,
            detail="All numeric values must be non-negative"
        )

    # Validate date is not too far in future (allow current month)
    today = date.today()
    max_future_date = today.replace(year=today.year + 1, month=12, day=31)
    if data.activity_date > max_future_date:
        raise HTTPException(
            status_code=400,
            detail="Activity date cannot be more than 1 year in the future"
        )

    #Initialize fitness service
    fitness_service = FitnessActivityService(db)

    try:
        #Store/Update daily activity (UPSERT logic)
        daily_record_id = fitness_service.upsert_daily_activity(
            data.user_id, data.activity_date, data.steps,
            data.distance_km, data.calories, data.active_minutes
        )

        #Check if monthly summarization should be triggered
        should_summarize = fitness_service.should_trigger_monthly_summary(
            data.user_id, data.activity_date
        )

        monthly_summary_data = None
        daily_records_deleted = 0
        old_monthly_records_deleted = 0

        if should_summarize:
            #Get the month to aggregate from stored values
            if hasattr(fitness_service, '_month_to_aggregate_year'):
                prev_year = fitness_service._month_to_aggregate_year
                prev_month = fitness_service._month_to_aggregate_month

                #Aggregate and store monthly summary
                monthly_summary_data = fitness_service.aggregate_and_store_monthly_summary(
                    data.user_id, prev_year, prev_month
                )

                if monthly_summary_data:
                    daily_records_deleted = monthly_summary_data['daily_records_deleted']
                    old_monthly_records_deleted = monthly_summary_data['old_monthly_records_deleted']

        #Check if yearly summarization should be triggered
        should_summarize_yearly = fitness_service.should_trigger_yearly_aggregation(
            data.user_id, data.activity_date
        )

        yearly_summary_data = None
        monthly_records_deleted = 0

        if should_summarize_yearly:
            #Get year to aggregate from stored values
            if hasattr(fitness_service, '_year_to_aggregate'):
                year_to_aggregate = fitness_service._year_to_aggregate

                #Aggregate and store yearly summary
                yearly_summary_data = fitness_service.aggregate_and_store_yearly_summary(
                    data.user_id, year_to_aggregate
                )

                if yearly_summary_data:
                    monthly_records_deleted = yearly_summary_data['monthly_records_deleted']

        #Get the stored daily record for response
        daily_record = db.execute(text("""
                                       SELECT id,
                                              user_id, date, steps, distance_km, calories, active_minutes, created_at
                                       FROM daily_activities
                                       WHERE id = :record_id
                                       """), {"record_id": daily_record_id}).fetchone()

        daily_response = DailyActivityResponse(
            id=daily_record[0],
            user_id=daily_record[1],
            activity_date=daily_record[2],
            steps=daily_record[3],
            distance_km=daily_record[4],
            calories=daily_record[5],
            active_minutes=daily_record[6],
            created_at=daily_record[7].isoformat() if daily_record[7] else ""
        )

        # Prepare response message
        message_parts = []

        if should_summarize and monthly_summary_data:
            message_parts.append(
                f"Previous month ({prev_year}-{prev_month:02d}) summarized: {monthly_summary_data['total_steps']} steps")
            message_parts.append(f"Daily records deleted: {daily_records_deleted}")
            message_parts.append(f"Old monthly records deleted: {old_monthly_records_deleted}")

        if should_summarize_yearly and yearly_summary_data:
            message_parts.append(f"Year {year_to_aggregate} aggregated: {yearly_summary_data['total_steps']} steps")
            message_parts.append(f"Monthly records deleted: {monthly_records_deleted}")

        if not message_parts:
            message = "Daily activity stored successfully."
        else:
            message = "Daily activity stored successfully. " + " ".join(message_parts) + "."

        return MonthlySummaryResponse(
            message=message,
            daily_activity_stored=True,
            monthly_summary_created=should_summarize and monthly_summary_data is not None,
            daily_records_deleted=daily_records_deleted,
            old_monthly_records_deleted=old_monthly_records_deleted,
            monthly_data=monthly_summary_data
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@app.get("/activity/daily/{user_id}")
def get_user_daily_activities(user_id: int, db: Session = Depends(get_db)):
    """
    Get all daily activities for a specific user
    Returns daily activities ordered by date (newest first)
    """
    # Verify user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        # Get daily activities for the user (LINES 225-243)
        activities = db.query(DailyActivity).filter(
            DailyActivity.user_id == user_id
        ).order_by(DailyActivity.date.desc()).all()

        return [
            UserDailyActivityResponse(
                id=activity.id,
                user_id=activity.user_id,
                date=activity.date,
                steps=activity.steps,
                distance_km=activity.distance_km,
                calories=activity.calories,
                active_minutes=activity.active_minutes,
                created_at=activity.created_at.isoformat(),
                updated_at=activity.updated_at.isoformat()
            )
            for activity in activities
        ]

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/activity/weekly")
def get_weekly_analytics(
        user_id: int,
        year: int,
        month: int,
        db: Session = Depends(get_db)
):
    """
    Get weekly aggregated activity data for a specific month.
    Splits month into 4 weeks and aggregates data per week.
    """

    # Verify user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get all activities for the month
    activities = db.query(DailyActivity).filter(
        and_(
            DailyActivity.user_id == user_id,
            extract('year', DailyActivity.date) == year,
            extract('month', DailyActivity.date) == month
        )
    ).all()

    # Group activities by week
    weekly_data = []

    for week_num in range(1, 5):  # 4 weeks per month
        # Calculate week start and end dates
        month_start = date(year, month, 1)

        if week_num == 1:
            week_start = month_start
            week_end = date(year, month, min(7, calendar.monthrange(year, month)[1]))
        elif week_num == 2:
            week_start = date(year, month, 8)
            week_end = date(year, month, min(14, calendar.monthrange(year, month)[1]))
        elif week_num == 3:
            week_start = date(year, month, 15)
            week_end = date(year, month, min(21, calendar.monthrange(year, month)[1]))
        else:  # week 4
            week_start = date(year, month, 22)
            week_end = date(year, month, calendar.monthrange(year, month)[1])

        # Filter activities for this week
        week_activities = [
            activity for activity in activities
            if week_start <= activity.date <= week_end
        ]

        # Calculate totals for the week
        total_steps = sum(activity.steps for activity in week_activities)
        total_calories = sum(activity.calories for activity in week_activities)
        total_distance = sum(activity.distance_km for activity in week_activities)
        total_active_minutes = sum(activity.active_minutes for activity in week_activities)

        weekly_data.append(WeeklyActivityData(
            week_number=week_num,
            start_date=week_start.isoformat(),
            end_date=week_end.isoformat(),
            total_steps=total_steps,
            total_calories=total_calories,
            total_distance=total_distance,
            total_active_minutes=total_active_minutes
        ))

    return WeeklyAnalyticsResponse(
        user_id=user_id,
        year=year,
        month=month,
        weeks=weekly_data
    )

@app.get("/activity/monthly/{user_id}") # New monthly activities endpoint
def get_user_monthly_activities(
        user_id: int,
        db: Session = Depends(get_db)
):
    """
    Get all monthly activity records for a specific user
    Returns monthly activities ordered by year and month (newest first)
    """
    # Verify user exists
    user = db.execute(text("SELECT id FROM users WHERE id = :user_id"), {"user_id": user_id}).fetchone()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Initialize fitness service
    fitness_service = FitnessActivityService(db)

    try:
        # Get monthly activities for the user
        monthly_records = fitness_service.get_user_monthly_activities(user_id)

        if not monthly_records:
            return []

        # Format response
        monthly_activities = []
        for record in monthly_records:
            monthly_activities.append(MonthlyActivityResponse(
                id=record[0],
                user_id=user_id,
                year=record[1],
                month=record[2],
                total_steps=record[3],
                total_distance_km=record[4],
                total_calories=record[5],
                total_active_minutes=record[6],
                created_at=record[7].isoformat() if record[7] else ""
            ))

        return monthly_activities

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
