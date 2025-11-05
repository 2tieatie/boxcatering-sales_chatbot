#!/usr/bin/env python3
"""Simple test script to check chatbot configuration without external dependencies."""

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


def test_database_structure():
    """Test the database structure after fixes."""
    try:
        logger.info("🔍 Testing database structure after fixes...")

        from app.database import SessionLocal
        from sqlalchemy import text

        db = SessionLocal()

        # Check table structure
        result = db.execute(
            text(
                """
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'chatbot_configs'
            ORDER BY ordinal_position
        """
            )
        )

        columns = result.fetchall()
        logger.info("📋 Current table structure:")
        for col in columns:
            logger.info(
                f"  - {col[0]}: {col[1]} (nullable: {col[2]}, default: {col[3]})"
            )

        # Check if we have the correct columns
        column_names = [col[0] for col in columns]
        required_columns = [
            "id",
            "name",
            "prompt",
            "business_context",
            "language",
            "force_language",
            "is_active",
            "created_at",
            "updated_at",
        ]

        missing_columns = [col for col in required_columns if col not in column_names]
        if missing_columns:
            logger.error(f"❌ Missing columns: {missing_columns}")
            return False

        # Check if we have the wrong columns
        wrong_columns = [col for col in column_names if col in ["text"]]
        if wrong_columns:
            logger.error(f"❌ Wrong columns found: {wrong_columns}")
            return False

        logger.info("✅ Table structure is correct!")

        # Test inserting a record
        logger.info("🧪 Testing record insertion...")
        try:
            result = db.execute(
                text(
                    """
                INSERT INTO chatbot_configs (name, prompt, business_context, language, force_language, is_active)
                VALUES (:name, :prompt, :business_context, :language, :force_language, :is_active)
                RETURNING id
            """
                ),
                {
                    "name": "Test Configuration",
                    "prompt": "Test prompt message",
                    "business_context": "Test business context",
                    "language": "uk",
                    "force_language": True,
                    "is_active": True,
                },
            )

            new_id = result.fetchone()[0]
            logger.info(f"✅ Successfully inserted record with ID: {new_id}")

            # Clean up test record
            db.execute(
                text("DELETE FROM chatbot_configs WHERE id = :id"), {"id": new_id}
            )
            db.commit()
            logger.info("🧹 Test record cleaned up")

        except Exception as e:
            logger.error(f"❌ Failed to insert test record: {e}")
            return False

        db.close()
        return True

    except Exception as e:
        logger.error(f"❌ Database test failed: {e}")
        return False


def main():
    """Main function."""
    logger.info("🚀 Simple Chatbot Config Test")
    logger.info("=" * 40)

    if test_database_structure():
        logger.info("=" * 40)
        logger.info("🎉 Success! Database structure is correct.")
        logger.info("💡 Now try saving settings from the frontend!")
    else:
        logger.error("❌ Test failed! Check the error messages above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
