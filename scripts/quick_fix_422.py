#!/usr/bin/env python3
"""Quick fix for 422 errors caused by missing created_at values."""

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
from datetime import datetime


def quick_fix_422_errors():
    """Quick fix for 422 errors by setting missing created_at values."""
    try:
        logger.info("🚀 Quick fix for 422 errors...")

        from app.database import SessionLocal
        from app.models import User, Conversation, Order

        db = SessionLocal()
        current_time = datetime.utcnow()

        # Fix users table
        users_fixed = 0
        users_without_created_at = (
            db.query(User).filter(User.created_at.is_(None)).all()
        )
        for user in users_without_created_at:
            user.created_at = current_time
            if user.is_active is None:
                user.is_active = True
            users_fixed += 1

        if users_fixed > 0:
            logger.info(f"🔧 Fixed {users_fixed} users")

        # Fix conversations table
        convs_fixed = 0
        convs_without_created_at = (
            db.query(Conversation).filter(Conversation.created_at.is_(None)).all()
        )
        for conv in convs_without_created_at:
            conv.created_at = current_time
            convs_fixed += 1

        if convs_fixed > 0:
            logger.info(f"🔧 Fixed {convs_fixed} conversations")

        # Fix orders table
        orders_fixed = 0
        orders_without_created_at = (
            db.query(Order).filter(Order.created_at.is_(None)).all()
        )
        for order in orders_without_created_at:
            order.created_at = current_time
            orders_fixed += 1

        if orders_fixed > 0:
            logger.info(f"🔧 Fixed {orders_fixed} orders")

        # Commit all changes
        if users_fixed > 0 or convs_fixed > 0 or orders_fixed > 0:
            db.commit()
            logger.info("✅ All database fixes committed!")
        else:
            logger.info(
                "✅ No fixes needed - all records already have created_at values"
            )

        db.close()

        logger.info("🎉 Quick fix completed!")
        logger.info(
            "💡 Try accessing your dashboard again - 422 errors should be gone!"
        )

    except Exception as e:
        logger.error(f"❌ Quick fix failed: {e}")
        return False

    return True


def main():
    """Main function."""
    logger.info("🚀 Quick Fix for 422 Errors")
    logger.info("=" * 40)

    if quick_fix_422_errors():
        logger.info("=" * 40)
        logger.info("🎉 Success! Your 422 errors should now be fixed.")
        logger.info(
            "💡 Restart your application and try accessing the dashboard again."
        )
    else:
        logger.error("❌ Fix failed! Check the error messages above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
