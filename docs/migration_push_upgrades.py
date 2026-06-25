import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.core.database import engine, SessionLocal, Base
from app.models import PushDeliveryLog, PushRetryQueue

def run_migration():
    print("Connecting to database and running migration...")
    db = SessionLocal()
    try:
        # Create new tables if not exists
        print("Ensuring push_delivery_logs and push_retry_queue tables exist...")
        Base.metadata.create_all(bind=engine)
        print("Success: Tables verified.")

        # Check existing columns in 'users' table
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name IN (
                'last_websocket_seen', 'last_app_activity'
            )
        """)).fetchall()
        existing_user_cols = [row[0] for row in result]

        # Add new columns to 'users' table if they don't exist
        user_columns_to_add = {
            'last_websocket_seen': "ALTER TABLE users ADD COLUMN last_websocket_seen TIMESTAMP WITH TIME ZONE NULL",
            'last_app_activity': "ALTER TABLE users ADD COLUMN last_app_activity TIMESTAMP WITH TIME ZONE NULL"
        }

        for col, sql in user_columns_to_add.items():
            if col not in existing_user_cols:
                print(f"Adding '{col}' column to users table...")
                db.execute(text(sql))
                print(f"Success: '{col}' column added.")
            else:
                print(f"Success: '{col}' column already exists in users table.")

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
