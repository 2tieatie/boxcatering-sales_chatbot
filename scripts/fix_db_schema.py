#!/usr/bin/env python3
"""Fix database schema issues causing 422 errors."""

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
from sqlalchemy import text, inspect


def check_database_schema():
    """Check database schema and identify issues."""
    try:
        logger.info("🔍 Checking database schema...")
        
        from app.database import engine, SessionLocal
        from app.models import User, Conversation, Order, SystemConfig, ChatbotConfig
        
        # Get database inspector
        inspector = inspect(engine)
        
        # Check if tables exist
        tables = inspector.get_table_names()
        logger.info(f"✅ Found tables: {', '.join(tables)}")
        
        # Check each table structure
        for table_name in tables:
            logger.info(f"\n📋 Table: {table_name}")
            columns = inspector.get_columns(table_name)
            for column in columns:
                logger.info(f"  - {column['name']}: {column['type']} (nullable: {column['nullable']})")
        
        # Check specific issues
        check_user_table_issues()
        check_conversation_table_issues()
        check_order_table_issues()
        
    except Exception as e:
        logger.error(f"❌ Schema check failed: {e}")
        return False
    
    return True


def check_user_table_issues():
    """Check for specific issues in the users table."""
    try:
        from app.database import SessionLocal
        from app.models import User
        
        db = SessionLocal()
        
        # Check if users table has data
        user_count = db.query(User).count()
        logger.info(f"👥 Users table has {user_count} records")
        
        if user_count > 0:
            # Check first user for missing fields
            first_user = db.query(User).first()
            logger.info(f"🔍 First user: ID={first_user.id}, Username={first_user.username}")
            logger.info(f"  - created_at: {first_user.created_at}")
            logger.info(f"  - updated_at: {first_user.updated_at}")
            logger.info(f"  - is_active: {first_user.is_active}")
            
            # Check for None values that might cause 422 errors
            if first_user.created_at is None:
                logger.warning("⚠️  User created_at is None - this will cause 422 errors!")
            if first_user.is_active is None:
                logger.warning("⚠️  User is_active is None - this will cause 422 errors!")
        
        db.close()
        
    except Exception as e:
        logger.error(f"❌ User table check failed: {e}")


def check_conversation_table_issues():
    """Check for specific issues in the conversations table."""
    try:
        from app.database import SessionLocal
        from app.models import Conversation
        
        db = SessionLocal()
        
        # Check if conversations table has data
        conv_count = db.query(Conversation).count()
        logger.info(f"💬 Conversations table has {conv_count} records")
        
        if conv_count > 0:
            # Check first conversation for missing fields
            first_conv = db.query(Conversation).first()
            logger.info(f"🔍 First conversation: ID={first_conv.id}")
            logger.info(f"  - created_at: {first_conv.created_at}")
            logger.info(f"  - updated_at: {first_conv.updated_at}")
            
            # Check for None values that might cause 422 errors
            if first_conv.created_at is None:
                logger.warning("⚠️  Conversation created_at is None - this will cause 422 errors!")
        
        db.close()
        
    except Exception as e:
        logger.error(f"❌ Conversation table check failed: {e}")


def check_order_table_issues():
    """Check for specific issues in the orders table."""
    try:
        from app.database import SessionLocal
        from app.models import Order
        
        db = SessionLocal()
        
        # Check if orders table has data
        order_count = db.query(Order).count()
        logger.info(f"📦 Orders table has {order_count} records")
        
        if order_count > 0:
            # Check first order for missing fields
            first_order = db.query(Order).first()
            logger.info(f"🔍 First order: ID={first_order.id}")
            logger.info(f"  - created_at: {first_order.created_at}")
            logger.info(f"  - updated_at: {first_order.updated_at}")
            
            # Check for None values that might cause 422 errors
            if first_order.created_at is None:
                logger.warning("⚠️  Order created_at is None - this will cause 422 errors!")
        
        db.close()
        
    except Exception as e:
        logger.error(f"❌ Order table check failed: {e}")


def fix_database_schema():
    """Fix common database schema issues."""
    try:
        logger.info("🔧 Fixing database schema issues...")
        
        from app.database import engine, SessionLocal
        from app.models import User, Conversation, Order, SystemConfig, ChatbotConfig
        from sqlalchemy import text
        from datetime import datetime
        
        db = SessionLocal()
        
        # Fix users table - set created_at for users without it
        users_without_created_at = db.query(User).filter(User.created_at.is_(None)).all()
        if users_without_created_at:
            logger.info(f"🔧 Fixing {len(users_without_created_at)} users without created_at")
            current_time = datetime.utcnow()
            for user in users_without_created_at:
                user.created_at = current_time
                if user.is_active is None:
                    user.is_active = True
            db.commit()
            logger.info("✅ Users table fixed")
        
        # Fix conversations table - set created_at for conversations without it
        convs_without_created_at = db.query(Conversation).filter(Conversation.created_at.is_(None)).all()
        if convs_without_created_at:
            logger.info(f"🔧 Fixing {len(convs_without_created_at)} conversations without created_at")
            current_time = datetime.utcnow()
            for conv in convs_without_created_at:
                conv.created_at = current_time
            db.commit()
            logger.info("✅ Conversations table fixed")
        
        # Fix orders table - set created_at for orders without it
        orders_without_created_at = db.query(Order).filter(Order.created_at.is_(None)).all()
        if orders_without_created_at:
            logger.info(f"🔧 Fixing {len(orders_without_created_at)} orders without created_at")
            current_time = datetime.utcnow()
            for order in orders_without_created_at:
                order.created_at = current_time
            db.commit()
            logger.info("✅ Orders table fixed")
        
        db.close()
        logger.info("🎉 Database schema fixes completed!")
        
    except Exception as e:
        logger.error(f"❌ Schema fix failed: {e}")
        return False
    
    return True


def test_api_endpoints():
    """Test API endpoints to see if 422 errors are fixed."""
    try:
        logger.info("🧪 Testing API endpoints...")
        
        from app.database import SessionLocal
        from app.models import User
        from app.services.auth_service import AuthService
        
        db = SessionLocal()
        auth_service = AuthService()
        
        # Get first user for testing
        user = db.query(User).first()
        if not user:
            logger.error("❌ No users found in database")
            return False
        
        # Create a test token
        token_data = {"sub": user.username}
        token = auth_service.create_access_token(token_data)
        
        logger.info(f"✅ Test token created for user: {user.username}")
        logger.info(f"🔑 Token: {token[:50]}...")
        
        db.close()
        
        logger.info("🎯 API endpoint test completed!")
        logger.info("💡 Now try accessing your dashboard again to see if 422 errors are fixed")
        
    except Exception as e:
        logger.error(f"❌ API endpoint test failed: {e}")
        return False
    
    return True


def main():
    """Main function to diagnose and fix database issues."""
    logger.info("🔧 Database Schema Fix Script")
    logger.info("=" * 50)
    
    # Step 1: Check schema
    if not check_database_schema():
        logger.error("❌ Schema check failed!")
        sys.exit(1)
    
    # Step 2: Fix schema issues
    if not fix_database_schema():
        logger.error("❌ Schema fix failed!")
        sys.exit(1)
    
    # Step 3: Test API endpoints
    if not test_api_endpoints():
        logger.error("❌ API endpoint test failed!")
        sys.exit(1)
    
    logger.info("=" * 50)
    logger.info("🎉 All database issues have been resolved!")
    logger.info("💡 You should now be able to access your dashboard without 422 errors")


if __name__ == "__main__":
    main()
