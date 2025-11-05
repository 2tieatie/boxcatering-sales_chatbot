#!/usr/bin/env python3
"""
Migration script to add promt fields to chatbot_configs table.
Run this script to add the new fields for promts chatbot configuration.
"""

import sys
import os
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from app.config import settings
from loguru import logger


def migrate_chatbot_config_promts():
    """Add promts fields to chatbot_configs table."""
    logger.info("🚀 Starting chatbot config promts migration...")

    try:
        # Create database engine
        engine = create_engine(settings.database_url)

        with engine.connect() as conn:
            # Check if columns already exist
            result = conn.execute(
                text(
                    """
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'chatbot_configs' 
                AND column_name IN (
                    'language_instruction', 'persona_instruction', 'system_instruction', 
                    'order_flow_block', 'other_instruction'
                )
            """
                )
            )

            existing_columns = {row[0] for row in result}
            logger.info(f"Existing extended columns: {existing_columns}")

            # Add missing columns
            columns_to_add = [
                ("language_instruction", "TEXT"),
                ("persona_instruction", "TEXT"),
                ("system_instruction", "TEXT"),
                ("order_flow_block", "TEXT"),
                ("other_instruction", "TEXT"),
            ]

            for column_name, column_type in columns_to_add:
                if column_name not in existing_columns:
                    logger.info(f"Adding column: {column_name}")
                    sql = f"ALTER TABLE chatbot_configs ADD COLUMN {column_name} {column_type}"
                    conn.execute(text(sql))
                    logger.info(f"✅ Added column: {column_name}")
                else:
                    logger.info(f"⏭️ Column already exists: {column_name}")

            # Commit changes
            conn.commit()
            logger.info("✅ Migration completed successfully!")

            # Verify the new structure
            result = conn.execute(
                text(
                    """
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = 'chatbot_configs'
                ORDER BY ordinal_position
            """
                )
            )

            logger.info("📋 Final table structure:")
            for row in result:
                logger.info(
                    f"  - {row[0]}: {row[1]} (nullable: {row[2]}, default: {row[3]})"
                )

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise


if __name__ == "__main__":
    migrate_chatbot_config_promts()
