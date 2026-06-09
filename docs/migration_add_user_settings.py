import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from app.core.database import engine, SessionLocal

def run_migration():
    print("Connecting to database and running migration...")
    db = SessionLocal()
    try:
        # Check existing columns in 'users' table
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name IN ('timezone', 'sleep_goal')
        """)).fetchall()
        
        existing_columns = [row[0] for row in result]
        
        # Add timezone column if not exists
        if 'timezone' not in existing_columns:
            print("Adding 'timezone' column...")
            db.execute(text("ALTER TABLE users ADD COLUMN timezone VARCHAR(100) NOT NULL DEFAULT 'Asia/Kolkata'"))
            print("Success: 'timezone' column added.")
        else:
            print("Success: 'timezone' column already exists.")

        # Add sleep_goal column if not exists
        if 'sleep_goal' not in existing_columns:
            print("Adding 'sleep_goal' column...")
            db.execute(text("ALTER TABLE users ADD COLUMN sleep_goal INTEGER NOT NULL DEFAULT 480"))
            print("Success: 'sleep_goal' column added.")
        else:
            print("Success: 'sleep_goal' column already exists.")

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
