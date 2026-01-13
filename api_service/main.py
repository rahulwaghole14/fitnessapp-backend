from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import random

from database import engine, SessionLocal
from models import Base, User
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
#         # Don't fail registration if email fails, user can still verify with printed OTP
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
#     """
#     Resend OTP functionality:
#     - Generate new OTP for existing user
#     - Update existing database record (no new user creation)
#     - Reset OTP timestamp for new expiration window
#     - Send new OTP via email
#     """
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
    """
    Forgot Password - Send OTP functionality:
    - Validate email exists in database
    - Generate new OTP for password reset
    - Update existing user record with new OTP and fresh timestamp
    - Send new OTP via email using existing EmailJS function
    """
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
        # Don't fail the operation if email fails, user can still verify with printed OTP

    return {"message": "Password reset OTP sent to your email"}


# FORGOT PASSWORD - VERIFY OTP
@app.post("/forgot-password/verify-otp")
def forgot_password_verify_otp(data: ForgotPasswordVerifySchema, db: Session = Depends(get_db)):
    """
    Forgot Password - Verify OTP functionality:
    - Validate OTP correctness for password reset
    - Validate OTP expiration (5 minute)
    - Return verification status without authenticating user
    """
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
    """
    Forgot Password - Reset Password functionality:
    - Re-validate OTP and expiration for security
    - Update user password in database
    - Clear OTP and timestamp after successful reset
    - Return success message
    """
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

    # OTP is valid - update password
    # Note: Using existing password storage approach (plain text as per current implementation)
    # In production, consider adding password hashing here
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

    return {"message": "Login successful", "username": db_user.username}
