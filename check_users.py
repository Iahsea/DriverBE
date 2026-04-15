#!/usr/bin/env python3
"""Check database users - simplified version"""
import sys
sys.path.insert(0, '/home/user/LAB')

# Load env first
from dotenv import load_dotenv
load_dotenv()

from app.database.database import SessionLocal
from app.database.models import User
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    db = SessionLocal()
    users = db.query(User).all()
    
    logger.info(f"📊 Total users in database: {len(users)}")
    if len(users) == 0:
        logger.warning("❌ No users found in database!")
    else:
        for user in users:
            logger.info(f"  ✓ {user.username}: {user.id}")
    
    db.close()
except Exception as e:
    logger.error(f"❌ Error connecting to database: {e}")
    import traceback
    traceback.print_exc()
