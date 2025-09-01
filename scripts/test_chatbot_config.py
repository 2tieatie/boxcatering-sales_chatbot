#!/usr/bin/env python3
"""Test script to check chatbot configuration database and API."""

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


def test_database_connection():
    """Test database connection and table structure."""
    try:
        logger.info("🔍 Testing database connection...")
        
        from app.database import SessionLocal, engine
        from sqlalchemy import text
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            logger.info("✅ Database connection successful")
        
        # Test table structure
        db = SessionLocal()
        
        # Check if table exists
        result = db.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name = 'chatbot_configs'
        """))
        
        if result.fetchone():
            logger.info("✅ chatbot_configs table exists")
            
            # Check table structure
            result = db.execute(text("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = 'chatbot_configs'
                ORDER BY ordinal_position
            """))
            
            columns = result.fetchall()
            logger.info("📋 Table structure:")
            for col in columns:
                logger.info(f"  - {col[0]}: {col[1]} (nullable: {col[2]}, default: {col[3]})")
                
        else:
            logger.error("❌ chatbot_configs table does not exist")
            
        db.close()
        
    except Exception as e:
        logger.error(f"❌ Database test failed: {e}")
        return False
    
    return True


def test_api_endpoint():
    """Test the chatbot config API endpoint."""
    try:
        logger.info("🔍 Testing API endpoint...")
        
        import requests
        
        # Test the endpoint without authentication first
        response = requests.post(
            "http://localhost:8000/chatbot-config/",
            json={
                "name": "Test Config",
                "prompt": "Test prompt",
                "business_context": "Test context",
                "language": "uk",
                "force_language": True,
                "is_active": True
            }
        )
        
        logger.info(f"📡 API Response Status: {response.status_code}")
        logger.info(f"📡 API Response Body: {response.text}")
        
        if response.status_code == 422:
            logger.error("❌ Validation error - check the response details above")
        elif response.status_code == 401:
            logger.info("ℹ️ Unauthorized (expected without token)")
        elif response.status_code == 200:
            logger.info("✅ API call successful")
        else:
            logger.warning(f"⚠️ Unexpected status code: {response.status_code}")
            
    except Exception as e:
        logger.error(f"❌ API test failed: {e}")
        return False
    
    return True


def main():
    """Main function."""
    logger.info("🚀 Chatbot Configuration Test Script")
    logger.info("=" * 50)
    
    logger.info("1️⃣ Testing database connection...")
    if not test_database_connection():
        logger.error("❌ Database test failed!")
        sys.exit(1)
    
    logger.info("\n2️⃣ Testing API endpoint...")
    if not test_api_endpoint():
        logger.error("❌ API test failed!")
        sys.exit(1)
    
    logger.info("\n🎉 All tests completed!")
    logger.info("💡 Check the logs above for any issues")


if __name__ == "__main__":
    main()
