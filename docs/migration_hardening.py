import sys
import os
from sqlalchemy import text

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal

def run_migration():
    print("Connecting to database and running hardening migrations...")
    db = SessionLocal()
    try:
        # 1. Add logical_event_id to notifications
        print("Adding column logical_event_id to notifications...")
        db.execute(text("ALTER TABLE notifications ADD COLUMN IF NOT EXISTS logical_event_id VARCHAR(255);"))
        
        print("Creating conditional unique index on notifications(logical_event_id)...")
        db.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS uq_notifications_logical_event 
            ON notifications (logical_event_id) 
            WHERE logical_event_id IS NOT NULL;
        """))
        
        # 2. Add processing_started_at to scheduled_notification_jobs
        print("Adding column processing_started_at to scheduled_notification_jobs...")
        db.execute(text("ALTER TABLE scheduled_notification_jobs ADD COLUMN IF NOT EXISTS processing_started_at TIMESTAMP WITH TIME ZONE;"))
        
        # 3. Add unique index on notification_delivery_queue(notification_id, channel)
        print("Creating unique index on notification_delivery_queue(notification_id, channel)...")
        # To avoid failure on existing duplicate queue items (if any exist), we'll print a warning
        # but in standard cases, this table shouldn't have duplicate channel entries for a single notification.
        try:
            db.execute(text("""
                CREATE UNIQUE INDEX IF NOT EXISTS uq_delivery_queue_notif_channel 
                ON notification_delivery_queue (notification_id, channel);
            """))
        except Exception as e:
            print(f"Warning: Could not create unique index on notification_delivery_queue. "
                  f"There might be existing duplicate queue records that need manual cleanup: {e}")
            db.rollback()
            # Clean up duplicates before attempting unique constraint
            print("Attempting to clean up duplicate delivery queue entries (keeping the oldest)...")
            db.execute(text("""
                DELETE FROM notification_delivery_queue a USING notification_delivery_queue b
                WHERE a.id > b.id 
                  AND a.notification_id = b.notification_id 
                  AND a.channel = b.channel;
            """))
            db.commit()
            print("Duplicate delivery queue entries cleaned. Retrying unique index creation...")
            db.execute(text("""
                CREATE UNIQUE INDEX IF NOT EXISTS uq_delivery_queue_notif_channel 
                ON notification_delivery_queue (notification_id, channel);
            """))
        
        db.commit()
        print("Hardening migrations applied successfully!")
    except Exception as e:
        db.rollback()
        print(f"Error: Hardening migration failed: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    run_migration()
