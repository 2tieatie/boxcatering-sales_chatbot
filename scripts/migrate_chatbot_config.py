#!/usr/bin/env python3
"""Migration script to add language and force_language fields to chatbot_configs table."""

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
from sqlalchemy import text


def migrate_chatbot_config():
    """Add language and force_language fields to chatbot_configs table."""
    try:
        logger.info("🚀 Starting chatbot configuration migration...")

        from app.database import engine

        with engine.connect() as conn:
            # Check if the fields already exist
            result = conn.execute(
                text(
                    """
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'chatbot_configs' 
                AND column_name IN ('language', 'force_language')
            """
                )
            )

            existing_columns = [row[0] for row in result]

            if "language" not in existing_columns:
                logger.info("➕ Adding 'language' column...")
                conn.execute(
                    text(
                        "ALTER TABLE chatbot_configs ADD COLUMN language VARCHAR DEFAULT 'uk' NOT NULL"
                    )
                )
                logger.info("✅ 'language' column added successfully")
            else:
                logger.info("ℹ️ 'language' column already exists")

            if "force_language" not in existing_columns:
                logger.info("➕ Adding 'force_language' column...")
                conn.execute(
                    text(
                        "ALTER TABLE chatbot_configs ADD COLUMN force_language BOOLEAN DEFAULT TRUE NOT NULL"
                    )
                )
                logger.info("✅ 'force_language' column added successfully")
            else:
                logger.info("ℹ️ 'force_language' column already exists")

            # Update existing records to have Ukrainian language by default
            if "language" not in existing_columns:
                logger.info("🔄 Updating existing records to use Ukrainian language...")
                conn.execute(
                    text(
                        "UPDATE chatbot_configs SET language = 'uk' WHERE language IS NULL"
                    )
                )
                logger.info("✅ Existing records updated")

            if "force_language" not in existing_columns:
                logger.info("🔄 Updating existing records to enforce language...")
                conn.execute(
                    text(
                        "UPDATE chatbot_configs SET force_language = TRUE WHERE force_language IS NULL"
                    )
                )
                logger.info("✅ Existing records updated")

            conn.commit()
            logger.info("🎉 Migration completed successfully!")

            # Verify the changes
            result = conn.execute(text("SELECT * FROM chatbot_configs LIMIT 1"))
            columns = result.keys()
            logger.info(f"📋 Current table columns: {list(columns)}")

            return True

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return False


def main():
    """Main function."""
    logger.info("🚀 Chatbot Configuration Migration")
    logger.info("=" * 40)

    if migrate_chatbot_config():
        logger.info("=" * 40)
        logger.info("🎉 SUCCESS! Chatbot configuration table has been updated.")
        logger.info("💡 The AI agent will now speak Ukrainian by default.")
        logger.info(
            "💡 You can configure language settings in the chatbot settings page."
        )
    else:
        logger.error("❌ FAILED! Migration could not be completed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
