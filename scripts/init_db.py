#!/usr/bin/env python3
"""Database initialization script."""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.database import engine, Base
from app.models import *  # Import all models
from loguru import logger


def init_database():
    """Initialize the database with all tables."""
    try:
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully!")
        
        # TODO: Add initial data (admin user, default configs, etc.)
        logger.info("Database initialization completed!")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Check if .env file exists
    env_file = project_root / ".env"
    if not env_file.exists():
        print("❌ Error: .env file not found!")
        print("Please copy env.example to .env and configure your database settings.")
        sys.exit(1)
    
    init_database()
