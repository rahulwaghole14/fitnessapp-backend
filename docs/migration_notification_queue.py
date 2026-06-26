import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import engine, SessionLocal, Base
from app.models import NotificationDeliveryQueue

def run_migration():
    print("Connecting to database and running migration...")
    db = SessionLocal()
    try:
        # Create new tables if not exists
        print("Ensuring notification_delivery_queue table exists...")
        Base.metadata.create_all(bind=engine)
        print("Success: Tables verified.")
        print("Database migration completed successfully!")
    except Exception as e:
        print(f"Error: Migration failed: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    run_migration()
