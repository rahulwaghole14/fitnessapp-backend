import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.core.database import engine, SessionLocal, Base
from app.models import ScheduledNotificationJob

def run_migration():
    print("Connecting to database and running migration...")
    db = SessionLocal()
    try:
        # Create scheduled_notification_jobs table if not exists
        print("Ensuring scheduled_notification_jobs table exists...")
        Base.metadata.create_all(bind=engine)
        print("Success: scheduled_notification_jobs table verified.")

        # Check existing columns in 'notifications' table
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'notifications' AND column_name IN (
                'source_module', 'delivery_status', 'push_sent', 'push_sent_at', 'websocket_sent', 'websocket_sent_at'
            )
        """)).fetchall()
        existing_notification_cols = [row[0] for row in result]

        # Add new columns to 'notifications' table
        notification_columns_to_add = {
            'source_module': "ALTER TABLE notifications ADD COLUMN source_module VARCHAR(100) NULL",
            'delivery_status': "ALTER TABLE notifications ADD COLUMN delivery_status VARCHAR(50) DEFAULT 'PENDING' NULL",
            'push_sent': "ALTER TABLE notifications ADD COLUMN push_sent BOOLEAN DEFAULT FALSE NOT NULL",
            'push_sent_at': "ALTER TABLE notifications ADD COLUMN push_sent_at TIMESTAMP WITH TIME ZONE NULL",
            'websocket_sent': "ALTER TABLE notifications ADD COLUMN websocket_sent BOOLEAN DEFAULT FALSE NOT NULL",
            'websocket_sent_at': "ALTER TABLE notifications ADD COLUMN websocket_sent_at TIMESTAMP WITH TIME ZONE NULL"
        }

        for col, sql in notification_columns_to_add.items():
            if col not in existing_notification_cols:
                print(f"Adding '{col}' column to notifications...")
                db.execute(text(sql))
                print(f"Success: '{col}' column added.")
            else:
                print(f"Success: '{col}' column already exists in notifications.")

        # Check existing columns in 'device_tokens' table
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'device_tokens' AND column_name IN (
                'failure_count', 'last_push_success', 'last_push_failure'
            )
        """)).fetchall()
        existing_device_token_cols = [row[0] for row in result]

        # Add new columns to 'device_tokens' table
        device_token_columns_to_add = {
            'failure_count': "ALTER TABLE device_tokens ADD COLUMN failure_count INTEGER DEFAULT 0 NOT NULL",
            'last_push_success': "ALTER TABLE device_tokens ADD COLUMN last_push_success TIMESTAMP WITH TIME ZONE NULL",
            'last_push_failure': "ALTER TABLE device_tokens ADD COLUMN last_push_failure TIMESTAMP WITH TIME ZONE NULL"
        }

        for col, sql in device_token_columns_to_add.items():
            if col not in existing_device_token_cols:
                print(f"Adding '{col}' column to device_tokens...")
                db.execute(text(sql))
                print(f"Success: '{col}' column added.")
            else:
                print(f"Success: '{col}' column already exists in device_tokens.")

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
