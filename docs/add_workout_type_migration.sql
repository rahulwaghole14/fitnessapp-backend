-- Migration to add workout_type column to workouts table
-- Run this script to update existing database

ALTER TABLE workouts 
ADD COLUMN workout_type VARCHAR(50) NOT NULL DEFAULT 'home';

-- Update any existing records to have a default value
UPDATE workouts SET workout_type = 'home' WHERE workout_type IS NULL;
