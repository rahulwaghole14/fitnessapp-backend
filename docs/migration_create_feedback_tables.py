"""
Database Migration Script: Create feedbacks table

Run this script to update your database:
python docs/migration_create_feedback_tables.py
"""

import sys
import os
from sqlalchemy import text

# Add parent directory to path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import engine, Base, SessionLocal
from app.models import *


def run_migration():
    print("Starting database migration for Feedback Module...")
    try:
        # Create all tables (SQLAlchemy will create feedbacks table because it is imported via *)
        Base.metadata.create_all(bind=engine)
        print("SQLAlchemy tables verified/created successfully.")

        db = SessionLocal()
        try:
            # Verify feedbacks table structure
            print("\nVerifying feedbacks database table:")
            columns = db.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = 'feedbacks'
                ORDER BY ordinal_position
            """)).fetchall()
            
            if columns:
                print(f"\nTable: feedbacks")
                print("-" * 50)
                for col in columns:
                    print(f"  {col[0]:<20} {col[1]:<15} {col[2]:<10}")
                print("-" * 50)
            else:
                print("\nWarning: Could not query structure for table feedbacks")

        finally:
            db.close()

    except Exception as e:
        print(f"Migration failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    run_migration()
    print("\nFeedback Module migration completed successfully!")
