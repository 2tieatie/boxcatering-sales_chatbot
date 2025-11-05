#!/usr/bin/env python3
"""
Test script to create a chatbot config with extended schema.
This will test if the backend can handle the new fields properly.
"""

import sys
import os
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from app.config import settings
from loguru import logger


def test_chatbot_config_create():
    """Test creating a chatbot config with extended schema."""
    logger.info("🚀 Testing chatbot config creation with extended schema...")

    try:
        # Create database engine
        engine = create_engine(settings.database_url)

        with engine.connect() as conn:
            # Test data with extended fields
            test_config = {
                "name": "Test Extended Config",
                "prompt": "Hello! I am a test chatbot.",
                "business_context": "This is a test business context.",
                "language": "en",
                "force_language": True,
                "is_active": True,
                "company_name": "Test Company",
                "specializations": "Test specializations",
                "friendly_tone": True,
                "professional_style": True,
                "suggestive_responses": True,
                "manager_handover": True,
                "fallback_message": "I did not understand that.",
                "handover_message": "Let me connect you to a manager.",
                "response_timeout": 45,
                "conversation_logging": True,
                "performance_analytics": True,
                "error_reporting": True,
            }

            # Insert test config
            columns = ", ".join(test_config.keys())
            placeholders = ", ".join([f":{key}" for key in test_config.keys()])

            sql = f"""
                INSERT INTO chatbot_configs ({columns})
                VALUES ({placeholders})
                RETURNING id
            """

            result = conn.execute(text(sql), test_config)
            config_id = result.fetchone()[0]
            conn.commit()

            logger.info(f"✅ Created test config with ID: {config_id}")

            # Verify the config was created with all fields
            result = conn.execute(
                text(
                    """
                SELECT * FROM chatbot_configs WHERE id = :config_id
            """
                ),
                {"config_id": config_id},
            )

            row = result.fetchone()
            if row:
                logger.info("✅ Config retrieved successfully")
                logger.info(f"  - ID: {row[0]}")
                logger.info(f"  - Name: {row[1]}")
                logger.info(f"  - Company: {row[7]}")
                logger.info(f"  - Specializations: {row[8]}")
                logger.info(f"  - Response Timeout: {row[18]}")
            else:
                logger.error("❌ Failed to retrieve created config")

            # Clean up - delete test config
            conn.execute(
                text("DELETE FROM chatbot_configs WHERE id = :config_id"),
                {"config_id": config_id},
            )
            conn.commit()
            logger.info("✅ Test config cleaned up")

    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        raise


if __name__ == "__main__":
    test_chatbot_config_create()
