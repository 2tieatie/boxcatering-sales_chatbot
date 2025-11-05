#!/usr/bin/env python3
"""Create initial system administrator user."""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.database import SessionLocal
from app.models.user import User, UserRole
from app.services.auth_service import AuthService
from loguru import logger


def create_system_admin():
    """Create the first system administrator user."""
    db = SessionLocal()
    try:
        # Check if any users exist
        existing_users = db.query(User).count()
        if existing_users > 0:
            logger.warning(
                "Users already exist in the database. Skipping admin creation."
            )
            return

        # Create system admin user
        auth_service = AuthService()
        hashed_password = auth_service.get_password_hash(
            "admin123"
        )  # Change this password!

        admin_user = User(
            username="admin",
            email="admin@boxcatering.com",
            full_name="System Administrator",
            hashed_password=hashed_password,
            role=UserRole.SYSTEM_ADMIN,
            is_active=True,
        )

        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)

        logger.info("✅ System administrator user created successfully!")
        logger.info(f"Username: {admin_user.username}")
        logger.info(f"Email: {admin_user.email}")
        logger.info(f"Role: {admin_user.role}")
        logger.info(
            "⚠️  IMPORTANT: Change the default password 'admin123' after first login!"
        )

    except Exception as e:
        logger.error(f"Failed to create system admin user: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    # Check if .env file exists
    env_file = project_root / ".env"
    if not env_file.exists():
        print("❌ Error: .env file not found!")
        print("Please copy env.example to .env and configure your database settings.")
        sys.exit(1)

    create_system_admin()
