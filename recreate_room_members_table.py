"""
Recreate room_members table that was accidentally deleted.

This script will create the room_members table with proper schema,
foreign keys, and indexes as defined in models.py
"""

import sys
from sqlalchemy import text
from app.database.database import engine, SessionLocal

def recreate_room_members_table():
    """
    Recreate the room_members table in MySQL database.
    """
    
    # SQL to create room_members table
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS room_members (
        id VARCHAR(36) NOT NULL PRIMARY KEY COMMENT 'UUID string',
        room_id VARCHAR(36) NOT NULL COMMENT 'ID phòng',
        user_id VARCHAR(36) NOT NULL COMMENT 'ID user',
        role VARCHAR(20) NOT NULL DEFAULT 'member' COMMENT 'admin, moderator, member',
        joined_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'Thời gian tham gia',
        
        FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        
        UNIQUE KEY unique_member (room_id, user_id),
        INDEX idx_room (room_id),
        INDEX idx_user (user_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """
    
    try:
        with engine.connect() as connection:
            # Create table
            connection.execute(text(create_table_sql))
            connection.commit()
            
            # Verify table was created
            verify_sql = "SHOW TABLES LIKE 'room_members';"
            result = connection.execute(text(verify_sql))
            tables = result.fetchall()
            
            if tables:
                print("✅ Successfully recreated room_members table!")
                print("\nTable schema:")
                
                # Show table structure
                desc_sql = "DESCRIBE room_members;"
                desc_result = connection.execute(text(desc_sql))
                for row in desc_result:
                    print(f"  {row}")
                
                return True
            else:
                print("❌ Failed to create room_members table")
                return False
    
    except Exception as e:
        print(f"❌ Error recreating room_members table: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Recreating room_members table...")
    print("=" * 60)
    
    success = recreate_room_members_table()
    
    if success:
        print("\n✅ Done! room_members table is ready to use.")
        sys.exit(0)
    else:
        print("\n❌ Failed to recreate table. Check errors above.")
        sys.exit(1)
