#!/usr/bin/env python3
"""Database initialization script."""

import os
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.database import engine, Base, SessionLocal
from app.models import *  # Import all models
from app.services.auth_service import AuthService
from loguru import logger


def create_admin_user(db):
    """Create the default system administrator user."""
    try:
        # Check if admin user already exists
        existing_admin = db.query(User).filter(User.username == "admin").first()
        
        if existing_admin:
            logger.info("ℹ️  Admin user already exists, updating if needed...")
            # Update admin user to ensure correct role
            if existing_admin.role != "system_admin":
                existing_admin.role = "system_admin"
                existing_admin.updated_at = datetime.now(timezone.utc)
                logger.info("✅ Updated admin user role to system_admin")
        else:
            logger.info("👤 Creating default system administrator user...")
            
            # Hash the default password
            auth_service = AuthService()
            hashed_password = auth_service.get_password_hash("admin123")
            
            # Create admin user
            admin_user = User(
                username="admin",
                email="admin@boxcatering.com",
                full_name="System Administrator",
                hashed_password=hashed_password,
                role="system_admin",
                is_active=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            
            db.add(admin_user)
            logger.info("✅ Created default admin user: admin/admin123")
        
        db.commit()
        return True
        
    except Exception as e:
        logger.error(f"❌ Error creating admin user: {e}")
        db.rollback()
        return False


def create_default_system_configs(db):
    """Create default system configuration values."""
    try:
        logger.info("⚙️  Creating default system configurations...")
        
        # Default configuration values
        default_configs = [
            # OpenAI Configuration
            {
                "key": "openai_api_key",
                "value": "",
                "description": "OpenAI API key for GPT model access",
                "is_sensitive": True
            },
            {
                "key": "openai_model",
                "value": "gpt-4o",
                "description": "OpenAI model to use (gpt-4o, gpt-4, gpt-3.5-turbo)",
                "is_sensitive": False
            },
            {
                "key": "openai_max_tokens",
                "value": "1000",
                "description": "Maximum tokens for OpenAI responses",
                "is_sensitive": False
            },
            {
                "key": "openai_temperature",
                "value": "0.7",
                "description": "Temperature setting for OpenAI responses (0.0-2.0)",
                "is_sensitive": False
            },
            
            # Telegram Configuration
            {
                "key": "telegram_bot_token",
                "value": "",
                "description": "Telegram bot token from @BotFather",
                "is_sensitive": True
            },
            {
                "key": "telegram_chat_id",
                "value": "",
                "description": "Chat ID for notifications (group or channel)",
                "is_sensitive": False
            },
            {
                "key": "telegram_notifications",
                "value": "all",
                "description": "Notification level (all, handovers, errors, none)",
                "is_sensitive": False
            },
            
            # System Configuration
            {
                "key": "system_name",
                "value": "Boxcatering Chatbot",
                "description": "System name for the application",
                "is_sensitive": False
            },
            {
                "key": "system_version",
                "value": "1.0.0",
                "description": "System version number",
                "is_sensitive": False
            },
            {
                "key": "system_timezone",
                "value": "Europe/Kyiv",
                "description": "Default timezone for the system",
                "is_sensitive": False
            },
            {
                "key": "system_language",
                "value": "uk",
                "description": "Default system language (uk, en, de, fr, es)",
                "is_sensitive": False
            },
            {
                "key": "system_log_level",
                "value": "INFO",
                "description": "System log level (DEBUG, INFO, WARNING, ERROR)",
                "is_sensitive": False
            },
            
            # Security Configuration
            {
                "key": "security_jwt_secret",
                "value": "",
                "description": "JWT secret key for token signing",
                "is_sensitive": True
            },
            {
                "key": "security_jwt_expiry",
                "value": "24",
                "description": "JWT token expiry time in hours",
                "is_sensitive": False
            },
            {
                "key": "security_password_min_length",
                "value": "8",
                "description": "Minimum password length requirement",
                "is_sensitive": False
            },
            {
                "key": "security_session_timeout",
                "value": "30",
                "description": "Session timeout in minutes",
                "is_sensitive": False
            }
        ]
        
        configs_created = 0
        configs_updated = 0
        
        # Check and create/update configurations
        for config_data in default_configs:
            existing_config = db.query(SystemConfig).filter(SystemConfig.key == config_data["key"]).first()
            
            if existing_config:
                # Update existing config if values are different
                if (existing_config.value != config_data["value"] or 
                    existing_config.description != config_data["description"] or
                    existing_config.is_sensitive != config_data["is_sensitive"]):
                    
                    existing_config.value = config_data["value"]
                    existing_config.description = config_data["description"]
                    existing_config.is_sensitive = config_data["is_sensitive"]
                    existing_config.updated_at = datetime.now(timezone.utc)
                    
                    configs_updated += 1
                    logger.debug(f"Updated configuration: {config_data['key']}")
            else:
                # Create new config
                new_config = SystemConfig(
                    key=config_data["key"],
                    value=config_data["value"],
                    description=config_data["description"],
                    is_sensitive=config_data["is_sensitive"]
                )
                db.add(new_config)
                configs_created += 1
                logger.debug(f"Created configuration: {config_data['key']}")
        
        db.commit()
        logger.info(f"✅ System configurations: {configs_created} created, {configs_updated} updated")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error creating system configurations: {e}")
        db.rollback()
        return False


def create_default_chatbot_config(db):
    """Create default chatbot configuration."""
    try:
        logger.info("🤖 Creating default chatbot configuration...")
        
        # Check if chatbot config already exists
        existing_config = db.query(ChatbotConfig).filter(ChatbotConfig.is_active == True).first()
        
        if existing_config:
            logger.info("ℹ️  Chatbot configuration already exists, updating language settings...")
            # Update existing config to ensure Ukrainian language enforcement
            existing_config.language = "uk"
            existing_config.force_language = True
            existing_config.updated_at = datetime.now(timezone.utc)
            db.commit()
            logger.info("✅ Updated existing chatbot configuration with Ukrainian language enforcement")
        else:
            logger.info("📝 Creating new chatbot configuration...")
            # Create new default configuration
            default_config = ChatbotConfig(
                name="Boxcatering Chatbot Configuration",
                prompt=("Привіт! Я Марічка, ваш AI-помічник з бокскейтерингу."
                        "Я можу допомогти вам з вибором меню, цінами, дієтичними вимогами та плануванням заходів. "
                        "Як я можу вам допомогти сьогодні?"),
                business_context=("Ми є преміум сервісом бокскейтерингу, що спеціалізується на корпоративних заходах, "
                                  "весіллях та приватних вечірках. Ми пропонуємо гурманську їжу, винятковий сервіс та налаштовувані "
                                  "меню для задоволення всіх дієтичних вимог."),
                language="uk",  # Ukrainian
                force_language=True,  # Strict language enforcement
                is_active=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            
            db.add(default_config)
            db.commit()
            logger.info("✅ Created new chatbot configuration with Ukrainian language enforcement")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error creating chatbot configuration: {e}")
        db.rollback()
        return False


def init_database():
    """Initialize the database with all tables and initial data."""
    try:
        logger.info("🚀 Starting database initialization...")
        
        # Step 1: Create database tables
        logger.info("📋 Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created successfully!")
        
        # Step 2: Create initial data
        db = SessionLocal()
        try:
            # Create admin user
            if not create_admin_user(db):
                raise Exception("Failed to create admin user")
            
            # Create default system configurations
            if not create_default_system_configs(db):
                raise Exception("Failed to create system configurations")
            
            # Create default chatbot configuration
            if not create_default_chatbot_config(db):
                raise Exception("Failed to create chatbot configuration")
            
            logger.info("✅ All initial data created successfully!")
            
        finally:
            db.close()
        
        logger.info("🎉 Database initialization completed successfully!")
        logger.info("")
        logger.info("📋 Summary of what was created:")
        logger.info("  • Database tables for all models")
        logger.info("  • System administrator user (admin/admin123)")
        logger.info("  • Default system configurations (OpenAI, Telegram, System, Security)")
        logger.info("  • Default chatbot configuration (Ukrainian language)")
        logger.info("")
        logger.info("🔑 Default login credentials:")
        logger.info("  Username: admin")
        logger.info("  Password: admin123")
        logger.info("  Role: system_admin")
        logger.info("")
        logger.info("⚠️  IMPORTANT: Change the default password after your first login!")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Check if .env file exists
    env_file = project_root / ".env"
    if not env_file.exists():
        print("❌ Error: .env file not found!")
        print("Please copy env.example to .env and configure your database settings.")
        sys.exit(1)
    
    init_database()
