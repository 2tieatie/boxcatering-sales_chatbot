#!/usr/bin/env python3
"""Test if the database fix worked."""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables early
from dotenv import load_dotenv

load_dotenv(project_root / ".env")

from loguru import logger


def test_database_fix():
    """Test if the database fix worked."""
    try:
        logger.info("🧪 Testing if database fix worked...")

        from app.database import SessionLocal
        from app.models import User, Conversation, Order

        db = SessionLocal()

        # Test users table
        users = db.query(User).all()
        logger.info(f"👥 Found {len(users)} users")

        for user in users:
            if user.created_at is None:
                logger.error(f"❌ User {user.username} still has NULL created_at!")
                return False
            if user.is_active is None:
                logger.error(f"❌ User {user.username} still has NULL is_active!")
                return False
            logger.info(
                f"✅ User {user.username}: created_at={user.created_at}, is_active={user.is_active}"
            )

        # Test conversations table
        conversations = db.query(Conversation).all()
        logger.info(f"💬 Found {len(conversations)} conversations")

        for conv in conversations:
            if conv.created_at is None:
                logger.error(f"❌ Conversation {conv.id} still has NULL created_at!")
                return False
            logger.info(f"✅ Conversation {conv.id}: created_at={conv.created_at}")

        # Test orders table
        orders = db.query(Order).all()
        logger.info(f"📦 Found {len(orders)} orders")

        for order in orders:
            if order.created_at is None:
                logger.error(f"❌ Order {order.id} still has NULL created_at!")
                return False
            logger.info(f"✅ Order {order.id}: created_at={order.created_at}")

        db.close()

        logger.info("🎉 All database records have proper timestamps!")
        return True

    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False


def main():
    """Main function."""
    logger.info("🧪 Database Fix Test")
    logger.info("=" * 30)

    if test_database_fix():
        logger.info("=" * 30)
        logger.info("🎉 SUCCESS! Your 422 errors should now be fixed.")
        logger.info("💡 Try accessing your dashboard and change-password page again.")
    else:
        logger.error("❌ FAILED! The database still has issues.")
        logger.error("💡 Run the fix script again: python scripts/quick_fix_422.py")


if __name__ == "__main__":
    main()
