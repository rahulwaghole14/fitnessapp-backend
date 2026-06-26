import sys
import os
from sqlalchemy import text

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal

def run_migration():
    print("Connecting to database and creating indexes...")
    db = SessionLocal()
    try:
        # Create indexes
        print("Creating idx_delivery_queue_channel_status_priority_created...")
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_delivery_queue_channel_status_priority_created ON notification_delivery_queue (channel, status, priority, created_at);"))
        
        print("Creating idx_jobs_user_status...")
        db.execute(text("CREATE INDEX IF NOT EXISTS idx_jobs_user_status ON scheduled_notification_jobs (user_id, status);"))
        
        print("Dropping old idx_delivery_queue_poll if exists...")
        db.execute(text("DROP INDEX IF EXISTS idx_delivery_queue_poll;"))
        
        db.commit()
        print("Indexes created successfully!")
    except Exception as e:
        db.rollback()
        print(f"Error: Index migration failed: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    run_migration()
