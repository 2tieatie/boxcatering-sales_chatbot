#!/usr/bin/env python3
"""
Setup script for system configuration.
This script initializes default system configuration values in the database.
"""

import os
import sys
import logging
from datetime import datetime

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.system_config import SystemConfig

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def setup_system_config():
    """Initialize default system configuration values."""
    logger.info("🚀 Starting system configuration setup...")
    
    try:
        db = SessionLocal()
        
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
                    existing_config.updated_at = datetime.utcnow()
                    
                    logger.info(f"✅ Updated existing configuration: {config_data['key']}")
                else:
                    logger.info(f"ℹ️  Configuration already exists: {config_data['key']}")
            else:
                # Create new config
                new_config = SystemConfig(
                    key=config_data["key"],
                    value=config_data["value"],
                    description=config_data["description"],
                    is_sensitive=config_data["is_sensitive"]
                )
                db.add(new_config)
                logger.info(f"✅ Created new configuration: {config_data['key']}")
        
        # Commit all changes
        db.commit()
        logger.info("✅ All system configurations have been set up successfully!")
        
        # Display summary
        total_configs = db.query(SystemConfig).count()
        logger.info(f"📊 Total system configurations in database: {total_configs}")
        
    except Exception as e:
        logger.error(f"❌ Error setting up system configuration: {e}")
        if db:
            db.rollback()
        raise
    finally:
        if db:
            db.close()


if __name__ == "__main__":
    try:
        setup_system_config()
        logger.info("🎉 System configuration setup completed successfully!")
    except Exception as e:
        logger.error(f"💥 System configuration setup failed: {e}")
        sys.exit(1)
