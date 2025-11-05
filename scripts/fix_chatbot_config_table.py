#!/usr/bin/env python3
"""Script to fix chatbot configuration table structure."""

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


def fix_chatbot_config_table():
    """Fix the chatbot configuration table structure."""
    try:
        logger.info("🔧 Fixing chatbot configuration table...")

        from app.database import engine

        with engine.connect() as conn:
            # Check if table exists
            result = conn.execute(
                text(
                    """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name = 'chatbot_configs'
            """
                )
            )

            if not result.fetchone():
                logger.info("📝 Creating chatbot_configs table...")

                # Create table with correct structure
                conn.execute(
                    text(
                        """
                    CREATE TABLE chatbot_configs (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR NOT NULL,
                        prompt TEXT NOT NULL,
                        business_context TEXT NOT NULL,
                        language VARCHAR DEFAULT 'uk' NOT NULL,
                        force_language BOOLEAN DEFAULT TRUE NOT NULL,
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    )
                """
                    )
                )

                logger.info("✅ Table created successfully")
            else:
                logger.info("✅ Table already exists, checking structure...")

                # Check current table structure
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

                current_columns = {row[0]: row for row in result.fetchall()}
                logger.info(f"📋 Current columns: {list(current_columns.keys())}")

                # Check if we have the wrong column structure (text instead of prompt/business_context)
                if "text" in current_columns and "prompt" not in current_columns:
                    logger.info(
                        "🔧 Found 'text' column instead of 'prompt' - fixing structure..."
                    )

                    # Drop the existing table and recreate it
                    conn.execute(text("DROP TABLE IF EXISTS chatbot_configs CASCADE"))
                    conn.commit()

                    # Create table with correct structure
                    conn.execute(
                        text(
                            """
                        CREATE TABLE chatbot_configs (
                            id SERIAL PRIMARY KEY,
                            name VARCHAR NOT NULL,
                            prompt TEXT NOT NULL,
                            business_context TEXT NOT NULL,
                            language VARCHAR DEFAULT 'uk' NOT NULL,
                            force_language BOOLEAN DEFAULT TRUE NOT NULL,
                            is_active BOOLEAN DEFAULT TRUE,
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
                            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                        )
                    """
                        )
                    )

                    logger.info("✅ Table recreated with correct structure")
                    conn.commit()
                    return True

                # Check if language and force_language columns exist
                if "language" not in current_columns:
                    logger.info("➕ Adding 'language' column...")
                    conn.execute(
                        text(
                            "ALTER TABLE chatbot_configs ADD COLUMN language VARCHAR DEFAULT 'uk' NOT NULL"
                        )
                    )

                if "force_language" not in current_columns:
                    logger.info("➕ Adding 'force_language' column...")
                    conn.execute(
                        text(
                            "ALTER TABLE chatbot_configs ADD COLUMN force_language BOOLEAN DEFAULT TRUE NOT NULL"
                        )
                    )

                # Check if prompt and business_context columns exist
                if "prompt" not in current_columns:
                    logger.info("➕ Adding 'prompt' column...")
                    conn.execute(
                        text(
                            "ALTER TABLE chatbot_configs ADD COLUMN prompt TEXT NOT NULL DEFAULT ''"
                        )
                    )

                if "business_context" not in current_columns:
                    logger.info("➕ Adding 'business_context' column...")
                    conn.execute(
                        text(
                            "ALTER TABLE chatbot_configs ADD COLUMN business_context TEXT NOT NULL DEFAULT ''"
                        )
                    )

                # Check if created_at and updated_at have proper defaults
                for col_name in ["created_at", "updated_at"]:
                    if col_name in current_columns:
                        col_info = current_columns[col_name]
                        if not col_info[3]:  # No default value
                            logger.info(f"🔧 Fixing {col_name} default...")
                            conn.execute(
                                text(
                                    f"ALTER TABLE chatbot_configs ALTER COLUMN {col_name} SET DEFAULT CURRENT_TIMESTAMP"
                                )
                            )

            conn.commit()
            logger.info("🎉 Table structure fixed successfully!")

    except Exception as e:
        logger.error(f"❌ Failed to fix table: {e}")
        return False

    return True


def main():
    """Main function."""
    logger.info("🚀 Chatbot Config Table Fix Script")
    logger.info("=" * 40)

    if fix_chatbot_config_table():
        logger.info("=" * 40)
        logger.info("🎉 Success! Table structure is now correct.")
        logger.info("💡 Try saving settings again!")
    else:
        logger.error("❌ Fix failed! Check the error messages above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
