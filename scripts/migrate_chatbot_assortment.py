#!/usr/bin/env python3
"""
Migration script `guests` & `weight` column to assortment_items.
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
    logger.info("🚀 Starting migration: assortment_items ->  ...")
    with engine.connect() as conn:
        # Detect existing columns
        cols = conn.execute(
            text(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'assortment_items'
                """
            )
        ).fetchall()
        existing = {c[0] for c in cols}
        logger.info(f"Existing columns: {sorted(existing)}")

        # Add welcome_message if missing
        if "guests" not in existing:
            logger.info("Adding column guests INTEGER ...")
            conn.execute(text("ALTER TABLE assortment_items ADD COLUMN guests INTEGER"))

        # Ensure not null by setting default minimal value where needed
        conn.execute(text("UPDATE assortment_items SET guests = '1' WHERE guests IS NULL"))

        # Add welcome_message if missing
        if "weight" not in existing:
            logger.info("Adding column weight INTEGER ...")
            conn.execute(text("ALTER TABLE assortment_items ADD COLUMN weight INTEGER"))

        # Ensure not null by setting default minimal value where needed
        conn.execute(text("UPDATE assortment_items SET weight = '1' WHERE weight IS NULL"))

        conn.commit()
        logger.info("✅ Migration completed.")


if __name__ == "__main__":
    migrate()
