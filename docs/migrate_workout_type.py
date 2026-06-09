"""
Migration script to add workout_type column to workouts table
"""
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def add_workout_type_column():
    """Add workout_type column to workouts table"""
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as connection:
        # Check if column already exists
        result = connection.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'workouts' AND column_name = 'workout_type'
        """))
        
        if result.fetchone():
            print("Column 'workout_type' already exists in workouts table")
            return
        
        # Add the column
        print("Adding workout_type column to workouts table...")
        connection.execute(text("""
            ALTER TABLE workouts 
            ADD COLUMN workout_type VARCHAR(50) NOT NULL DEFAULT 'home'
        """))
        
        # Commit the transaction
        connection.commit()
        print("Successfully added workout_type column to workouts table")

if __name__ == "__main__":
    add_workout_type_column()
