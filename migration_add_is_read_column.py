"""
Database Migration Script: Add is_read column to activity_logs table

This script adds the 'is_read' column to the activity_logs table
to support notification read/unread status tracking.

Run this script to update your database:
python migration_add_is_read_column.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from app.core.database import engine, SessionLocal
from app.models.user_activity_log import UserActivityLog

def add_is_read_column():
    """Add is_read column to activity_logs table if it doesn't exist."""
    
    db = SessionLocal()
    try:
        # Check if column already exists
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'activity_logs' 
            AND column_name = 'is_read'
        """))
        
        column_exists = result.fetchone() is not None
        
        if column_exists:
            print("is_read column already exists in activity_logs table")
            return
        
        print("Adding is_read column to activity_logs table...")
        
        # Add the column
        db.execute(text("""
            ALTER TABLE activity_logs 
            ADD COLUMN is_read BOOLEAN DEFAULT FALSE NOT NULL
        """))
        
        # Add indexes for performance
        print("Adding indexes for is_read column...")
        
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_activity_logs_is_read_created 
            ON activity_logs(is_read, created_at)
        """))
        
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_activity_logs_type_read_created 
            ON activity_logs(activity_type, is_read, created_at)
        """))
        
        db.commit()
        print("Successfully added is_read column and indexes!")
        
        # Verify the column was added
        result = db.execute(text("""
            SELECT COUNT(*) as total_notifications,
                   SUM(CASE WHEN is_read = FALSE THEN 1 ELSE 0 END) as unread_count
            FROM activity_logs
        """))
        
        stats = result.fetchone()
        print(f"Database stats: Total notifications: {stats.total_notifications}, Unread: {stats.unread_count}")
        
    except Exception as e:
        print(f"Error adding is_read column: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def verify_table_structure():
    """Verify the table structure after migration."""
    db = SessionLocal()
    try:
        # Get table structure
        result = db.execute(text("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'activity_logs'
            ORDER BY ordinal_position
        """))
        
        print("\nActivity logs table structure:")
        print("-" * 80)
        for row in result:
            print(f"{row.column_name:<20} {row.data_type:<15} {row.is_nullable:<10} {row.column_default}")
        print("-" * 80)
        
    except Exception as e:
        print(f"Error verifying table structure: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    print("Starting database migration for is_read column...")
    add_is_read_column()
    verify_table_structure()
    print("Migration completed successfully!")
