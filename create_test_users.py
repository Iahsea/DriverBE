#!/usr/bin/env python3
"""Create test users for development"""
import sys
sys.path.insert(0, '/home/user/LAB')

from app.database.database import SessionLocal
from app.database.models import User
from app.core.crypto_bridge import crypto_bridge
import asyncio
from uuid import uuid4
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def create_test_users():
    db = SessionLocal()
    try:
        # Check existing users
        existing = db.query(User).all()
        logger.info(f"Existing users: {len(existing)}")
        for user in existing:
            logger.info(f"  - {user.username} (ID: {user.id})")
        
        # Create test users if needed
        if len(existing) < 3:
            logger.info("\n📝 Creating test users...")
            
            test_users = [
                {"username": "alice", "email": "alice@test.com", "password": "password123"},
                {"username": "bob", "email": "bob@test.com", "password": "password123"},
                {"username": "charlie", "email": "charlie@test.com", "password": "password123"},
            ]
            
            for test_user in test_users:
                # Check if user exists
                existing_user = db.query(User).filter(
                    (User.username == test_user["username"]) | (User.email == test_user["email"])
                ).first()
                
                if existing_user:
                    logger.info(f"✓ User {test_user['username']} already exists (ID: {existing_user.id})")
                    continue
                
                # Hash password
                password_hash = await crypto_bridge.hash_password_with_driver(test_user["password"])
                
                # Create user
                user = User(
                    id=str(uuid4()),
                    username=test_user["username"],
                    email=test_user["email"],
                    password_hash=password_hash,
                    is_active=True,
                    is_verified=True,
                )
                db.add(user)
                logger.info(f"✓ Created user {test_user['username']} (ID: {user.id})")
            
            db.commit()
            logger.info("\n✓ Test users created successfully")
        
        # Show all users
        all_users = db.query(User).all()
        logger.info(f"\n📊 All users in database ({len(all_users)}):")
        for user in all_users:
            logger.info(f"  - {user.username}: {user.id}")
    
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(create_test_users())
