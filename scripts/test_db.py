#!/usr/bin/env python3
"""Test database connection and basic operations."""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger


def test_database_connection():
    """Test basic database connectivity."""
    try:
        logger.info("🔍 Testing database connection...")
        
        # Import database components
        from app.database import engine, SessionLocal
        from sqlalchemy import text
        
        logger.info("✅ Database engine created successfully")
        
        # Test basic connection
        with engine.connect() as conn:
            logger.info("✅ Database connection established")
            
            # Test simple query
            result = conn.execute(text("SELECT 1 as test"))
            row = result.fetchone()
            logger.info(f"✅ Test query successful: {row}")
            
            # Test database info
            result = conn.execute(text("SELECT current_database() as db_name, current_user as user_name"))
            db_info = result.fetchone()
            logger.info(f"✅ Connected to database: {db_info.db_name} as user: {db_info.user_name}")
            
        # Test session creation
        db = SessionLocal()
        try:
            logger.info("✅ Database session created successfully")
        finally:
            db.close()
            
        logger.info("🎉 All database tests passed!")
        return True
        
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        logger.info("Please ensure all dependencies are installed: pip install -r requirements.txt")
        return False
        
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        logger.info("\n🔧 Troubleshooting steps:")
        logger.info("1. Ensure PostgreSQL is running")
        logger.info("2. Check if database 'boxcatering_chatbot' exists")
        logger.info("3. Verify database credentials in .env file")
        logger.info("4. Test connection manually: psql -h localhost -U postgres -d boxcatering_chatbot")
        return False


def test_env_file():
    """Test environment file configuration."""
    try:
        logger.info("🔍 Checking environment configuration...")
        
        # Check if .env exists
        env_file = project_root / ".env"
        if not env_file.exists():
            logger.error("❌ .env file not found!")
            logger.info("Please run: cp env.example .env")
            logger.info("Then update the DATABASE_URL with your PostgreSQL credentials")
            return False
        
        # Load environment variables
        from dotenv import load_dotenv
        load_dotenv(env_file)
        
        # Check required variables
        database_url = os.getenv("DATABASE_URL")
        secret_key = os.getenv("SECRET_KEY")
        
        if not database_url:
            logger.error("❌ DATABASE_URL not found in .env file")
            return False
            
        if not secret_key:
            logger.error("❌ SECRET_KEY not found in .env file")
            return False
            
        logger.info("✅ Environment variables loaded successfully")
        logger.info(f"📊 Database URL: {database_url[:50]}...")
        logger.info(f"🔑 Secret key: {secret_key[:20]}...")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Environment check failed: {e}")
        return False


def main():
    """Main test function."""
    logger.info("🧪 Testing Boxcatering Chatbot Setup...")
    logger.info("=" * 50)
    
    env_ok = test_env_file()
    if not env_ok:
        logger.error("❌ Environment configuration failed!")
        sys.exit(1)
    
    db_ok = test_database_connection()
    if not db_ok:
        logger.error("❌ Database connection failed!")
        sys.exit(1)
    
    logger.info("=" * 50)
    logger.info("🎉 All tests passed! You're ready to run the setup script.")
    logger.info("Next step: python scripts/setup.py")


if __name__ == "__main__":
    main()
