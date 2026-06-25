import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.core.database import SessionLocal

def run_migration():
    print("Connecting to database and running OTP brute force fields migration...")
    db = SessionLocal()
    try:
        # Check existing columns in 'users' table
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name IN (
                'otp_attempts', 'otp_locked_until'
            )
        """)).fetchall()
        existing_user_cols = [row[0] for row in result]

        if 'otp_attempts' not in existing_user_cols:
            print("Adding 'otp_attempts' column to users table...")
            db.execute(text("ALTER TABLE users ADD COLUMN otp_attempts INTEGER DEFAULT 0 NOT NULL"))
            print("Success: 'otp_attempts' column added to users.")
        else:
            print("Success: 'otp_attempts' column already exists in users table.")
        
        if 'otp_locked_until' not in existing_user_cols:
            print("Adding 'otp_locked_until' column to users table...")
            db.execute(text("ALTER TABLE users ADD COLUMN otp_locked_until TIMESTAMP NULL"))
            print("Success: 'otp_locked_until' column added to users.")
        else:
            print("Success: 'otp_locked_until' column already exists in users table.")

        # Check existing columns in 'admins' table
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'admins' AND column_name IN (
                'otp_attempts', 'otp_locked_until'
            )
        """)).fetchall()
        existing_admin_cols = [row[0] for row in result]

        if 'otp_attempts' not in existing_admin_cols:
            print("Adding 'otp_attempts' column to admins table...")
            db.execute(text("ALTER TABLE admins ADD COLUMN otp_attempts INTEGER DEFAULT 0 NOT NULL"))
            print("Success: 'otp_attempts' column added to admins.")
        else:
            print("Success: 'otp_attempts' column already exists in admins table.")
        
        if 'otp_locked_until' not in existing_admin_cols:
            print("Adding 'otp_locked_until' column to admins table...")
            db.execute(text("ALTER TABLE admins ADD COLUMN otp_locked_until TIMESTAMP NULL"))
            print("Success: 'otp_locked_until' column added to admins.")
        else:
            print("Success: 'otp_locked_until' column already exists in admins table.")

        db.commit()
        print("Database migration completed successfully!")
    except Exception as e:
        db.rollback()
        print(f"Error: Migration failed: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    run_migration()
