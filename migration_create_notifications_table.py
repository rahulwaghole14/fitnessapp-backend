"""
Database Migration Script: Create notifications table

This script creates the 'notifications' table to support user-specific notifications.

Run this script to update your database:
python migration_create_notifications_table.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from app.core.database import engine, Base, SessionLocal
from app.models.notification import Notification

def create_notifications_table():
    """Create notifications table if it doesn't exist."""
    print("Verifying database connectivity and creating table...")
    try:
        # Create all tables including notifications
        Base.metadata.create_all(bind=engine)
        print("Successfully ensured notifications table exists using SQLAlchemy create_all!")
        
        # Verify the structure using a direct query
        db = SessionLocal()
        try:
            result = db.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = 'notifications'
                ORDER BY ordinal_position
            """)).fetchall()
            
            if result:
                print("\nNotifications table structure verified:")
                print("-" * 60)
                for row in result:
                    print(f"{row[0]:<20} {row[1]:<15} {row[2]:<10}")
                print("-" * 60)
            else:
                print("Warning: info schema could not verify notifications table (might be using SQLite or different search path).")
        finally:
            db.close()
            
    except Exception as e:
        print(f"Error ensuring notifications table exists: {e}")
        raise

if __name__ == "__main__":
    print("Starting database migration for notifications table...")
    create_notifications_table()
    print("Migration execution completed!")
