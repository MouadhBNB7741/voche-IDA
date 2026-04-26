-- Migration: Add deletion_scheduled_at column to users table
-- Run this query to update your local or production database without data loss.

ALTER TABLE users ADD COLUMN IF NOT EXISTS deletion_scheduled_at TIMESTAMPTZ;
