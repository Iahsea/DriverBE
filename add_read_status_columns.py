#!/usr/bin/env python3
"""
Migration script to add is_read and read_at columns to messages table
"""

import sys
from sqlalchemy import text
from app.database.database import engine

def add_columns():
    """Add is_read and read_at columns to messages table"""
    try:
        with engine.connect() as connection:
            print("🔄 Checking if columns already exist...")
            
            # Check if columns exist
            result = connection.execute(
                text("SHOW COLUMNS FROM messages WHERE Field='is_read'")
            )
            if result.fetchone():
                print("✅ Column 'is_read' already exists")
            else:
                print("➕ Adding 'is_read' column...")
                connection.execute(text(
                    "ALTER TABLE messages ADD COLUMN is_read BOOLEAN DEFAULT FALSE"
                ))
                print("✅ Added 'is_read' column")
            
            result = connection.execute(
                text("SHOW COLUMNS FROM messages WHERE Field='read_at'")
            )
            if result.fetchone():
                print("✅ Column 'read_at' already exists")
            else:
                print("➕ Adding 'read_at' column...")
                connection.execute(text(
                    "ALTER TABLE messages ADD COLUMN read_at DATETIME NULL"
                ))
                print("✅ Added 'read_at' column")
            
            # Add index for is_read
            try:
                connection.execute(text(
                    "CREATE INDEX idx_messages_is_read ON messages(is_read)"
                ))
                print("✅ Added index on 'is_read' column")
            except Exception as e:
                if "Duplicate key name" in str(e):
                    print("✅ Index on 'is_read' already exists")
                else:
                    raise
            
            connection.commit()
            print("\n✨ Migration completed successfully!")
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = add_columns()
    sys.exit(0 if success else 1)
