#!/usr/bin/env python3
"""
Migration script to add manual columns to daily_activities table (PostgreSQL)
"""

import os
import psycopg2
from dotenv import load_dotenv
import sys

def migrate_database():
    """Add manual activity columns to daily_activities table"""
    
    # Load environment variables
    load_dotenv()
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("[-] DATABASE_URL not found in environment variables")
        return False
    
    try:
        # Connect to PostgreSQL database
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Check if columns already exist
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'daily_activities'
        """)
        existing_columns = [row[0] for row in cursor.fetchall()]
        
        # Define columns to add
        columns_to_add = {
            'manual_steps': 'INTEGER DEFAULT 0 NOT NULL',
            'manual_distance_km': 'DOUBLE PRECISION DEFAULT 0.0 NOT NULL',
            'manual_calories': 'DOUBLE PRECISION DEFAULT 0.0 NOT NULL',
            'manual_active_minutes': 'DOUBLE PRECISION DEFAULT 0.0 NOT NULL'
        }
        
        for col_name, col_type in columns_to_add.items():
            if col_name not in existing_columns:
                print(f"Adding {col_name} column...")
                cursor.execute(f"ALTER TABLE daily_activities ADD COLUMN {col_name} {col_type}")
                print(f"[+] {col_name} column added")
            else:
                print(f"[+] {col_name} column already exists")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("\n[+] Migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"[-] Migration failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = migrate_database()
    sys.exit(0 if success else 1)
