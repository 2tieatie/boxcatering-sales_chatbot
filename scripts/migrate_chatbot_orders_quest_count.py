#!/usr/bin/env python3
"""
Migration script `guests_count` column to orders.
- Adds new column if missing
"""

import sys
from pathlib import Path

# Ensure project root on path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from sqlalchemy import text

from app.database import engine


def migrate():
    logger.info("🚀 Starting migration: orders -> guests_count ...")
    with engine.connect() as conn:
        # Detect existing columns
        cols = conn.execute(
            text(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'orders'
                """
            )
        ).fetchall()
        existing = {c[0] for c in cols}
        logger.info(f"Existing columns: {sorted(existing)}")

        # Add welcome_message if missing
        if "guests_count" not in existing:
            logger.info("Adding column guests_count INTEGER ...")
            conn.execute(text("ALTER TABLE orders ADD COLUMN guests_count INTEGER"))

        # Ensure not null by setting default minimal value where needed
        conn.execute(
            text(
                "UPDATE orders SET guests_count = 1 WHERE guests_count IS NULL OR guests_count = 0"
            )
        )

        conn.commit()
        logger.info("✅ Migration completed.")


if __name__ == "__main__":
    migrate()
