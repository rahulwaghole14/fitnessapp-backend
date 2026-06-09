#!/usr/bin/env python3
"""
Migration script to add meal_image and description fields to meals table (PostgreSQL)
"""

import os
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv
import sys

def migrate_database():
    """Add meal_image and description columns to meals table"""
    
    # Load environment variables
    load_dotenv()
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not found in environment variables")
        return False
    
    try:
        # Connect to PostgreSQL database
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Check if columns already exist
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'meals'
        """)
        existing_columns = [row[0] for row in cursor.fetchall()]
        
        # Add meal_image column if it doesn't exist
        if 'meal_image' not in existing_columns:
            print("Adding meal_image column...")
            cursor.execute("ALTER TABLE meals ADD COLUMN meal_image TEXT")
            print("✓ meal_image column added")
        else:
            print("✓ meal_image column already exists")
        
        # Add description column if it doesn't exist
        if 'description' not in existing_columns:
            print("Adding description column...")
            cursor.execute("ALTER TABLE meals ADD COLUMN description TEXT")
            print("✓ description column added")
        else:
            print("✓ description column already exists")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("\n✅ Migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = migrate_database()
    sys.exit(0 if success else 1)
