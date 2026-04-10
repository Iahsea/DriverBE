-- Migration SQL Script
-- Add is_read and read_at columns to messages table
-- Run this script in MySQL Workbench or via command line

-- Add is_read column if it doesn't exist
ALTER TABLE messages ADD COLUMN is_read BOOLEAN DEFAULT FALSE;

-- Add read_at column if it doesn't exist
ALTER TABLE messages ADD COLUMN read_at DATETIME NULL;

-- Create index for is_read column
CREATE INDEX idx_messages_is_read ON messages(is_read);

-- Verify the changes
SELECT COLUMN_NAME, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_NAME = 'messages' AND TABLE_SCHEMA = DATABASE();
