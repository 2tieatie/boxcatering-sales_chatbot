#!/usr/bin/env python3
"""
Migration script to rename `prompt` column to `welcome_message` in chatbot_configs.
- Adds new column if missing
- Copies data from `prompt` to `welcome_message`
- Optionally drops `prompt` if exists
"""

import sys
from pathlib import Path

# Ensure project root on path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from sqlalchemy import text

from app.database import engine


def migrate():
    logger.info("🚀 Starting migration: prompt -> welcome_message ...")
    with engine.connect() as conn:
        # Detect existing columns
        cols = conn.execute(
            text(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'chatbot_configs'
                """
            )
        ).fetchall()
        existing = {c[0] for c in cols}
        logger.info(f"Existing columns: {sorted(existing)}")

        # Add welcome_message if missing
        if "welcome_message" not in existing:
            logger.info("Adding column welcome_message TEXT ...")
            conn.execute(text("ALTER TABLE chatbot_configs ADD COLUMN welcome_message TEXT"))

        # Backfill from prompt if data exists
        if "prompt" in existing:
            logger.info("Backfilling welcome_message from prompt ...")
            conn.execute(text("UPDATE chatbot_configs SET welcome_message = prompt WHERE welcome_message IS NULL OR welcome_message = ''"))

        # Ensure not null by setting default minimal value where needed
        conn.execute(text("UPDATE chatbot_configs SET welcome_message = 'Welcome!' WHERE welcome_message IS NULL"))

        # Optionally drop old column
        try:
            if "prompt" in existing:
                logger.info("Dropping column prompt ...")
                conn.execute(text("ALTER TABLE chatbot_configs DROP COLUMN prompt"))
        except Exception as e:
            logger.warning(f"Could not drop prompt column (safe to ignore in dev): {e}")

        conn.commit()
        logger.info("✅ Migration completed.")


if __name__ == "__main__":
    migrate()
