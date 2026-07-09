#!/usr/bin/env python3
"""
Migration script to add created_at column to users table (PostgreSQL)
"""

import os
import psycopg2
from dotenv import load_dotenv
import sys

def migrate_database():
    """Add created_at column to users table"""
    
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
            WHERE table_name = 'users'
        """)
        existing_columns = [row[0] for row in cursor.fetchall()]
        
        # Add created_at column if it doesn't exist
        if 'created_at' not in existing_columns:
            print("Adding created_at column...")
            cursor.execute("ALTER TABLE users ADD COLUMN created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()")
            print("[+] created_at column added")
        else:
            print("[+] created_at column already exists")
        
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
