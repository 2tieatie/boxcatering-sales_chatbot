#!/usr/bin/env python3
"""Test authentication service without bcrypt issues."""

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


def test_auth_service():
    """Test the authentication service."""
    try:
        logger.info("🔍 Testing authentication service...")

        from app.services.auth_service import AuthService

        auth_service = AuthService()
        logger.info("✅ AuthService created successfully")

        # Test password hashing
        test_password = "test123"
        hashed = auth_service.get_password_hash(test_password)
        logger.info(f"✅ Password hashed successfully: {hashed[:50]}...")

        # Test password verification
        is_valid = auth_service.verify_password(test_password, hashed)
        if is_valid:
            logger.info("✅ Password verification successful")
        else:
            logger.error("❌ Password verification failed")
            return False

        # Test with wrong password
        is_valid = auth_service.verify_password("wrong_password", hashed)
        if not is_valid:
            logger.info("✅ Wrong password correctly rejected")
        else:
            logger.error("❌ Wrong password incorrectly accepted")
            return False

        logger.info("🎉 All authentication tests passed!")
        return True

    except Exception as e:
        logger.error(f"❌ Authentication test failed: {e}")
        return False


def main():
    """Main test function."""
    logger.info("🧪 Testing Authentication Service...")
    logger.info("=" * 50)

    success = test_auth_service()

    if success:
        logger.info("=" * 50)
        logger.info("🎉 Authentication service is working correctly!")
        logger.info("You can now run the setup script without bcrypt issues.")
    else:
        logger.error("❌ Authentication service has issues!")
        sys.exit(1)


if __name__ == "__main__":
    main()
