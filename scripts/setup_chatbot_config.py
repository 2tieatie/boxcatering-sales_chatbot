#!/usr/bin/env python3
"""Setup script to create default chatbot configuration with Ukrainian language enforcement."""

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
from datetime import datetime


def setup_chatbot_config():
    """Create default chatbot configuration with Ukrainian language enforcement."""
    try:
        logger.info("🚀 Setting up default chatbot configuration...")
        
        from app.database import SessionLocal
        from app.models.chatbot_config import ChatbotConfig
        
        db = SessionLocal()
        
        # Check if configuration already exists
        existing_config = db.query(ChatbotConfig).filter(ChatbotConfig.is_active == True).first()
        
        if existing_config:
            logger.info("✅ Chatbot configuration already exists, updating language settings...")
            # Update existing config to ensure Ukrainian language enforcement
            existing_config.language = "uk"
            existing_config.force_language = True
            existing_config.updated_at = datetime.utcnow()
            db.commit()
            logger.info("✅ Updated existing configuration with Ukrainian language enforcement")
        else:
            logger.info("📝 Creating new chatbot configuration...")
            # Create new default configuration
            default_config = ChatbotConfig(
                name="Boxcatering Chatbot Configuration",
                prompt="Привіт! Я ваш AI-помічник з бокскейтерингу. Я можу допомогти вам з вибором меню, цінами, дієтичними вимогами та плануванням заходів. Як я можу вам допомогти сьогодні?",
                business_context="Ми є преміум сервісом бокскейтерингу, що спеціалізується на корпоративних заходах, весіллях та приватних вечірках. Ми пропонуємо гурманську їжу, винятковий сервіс та налаштовувані меню для задоволення всіх дієтичних вимог.",
                language="uk",  # Ukrainian
                force_language=True,  # Strict language enforcement
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.add(default_config)
            db.commit()
            db.refresh(default_config)
            logger.info("✅ Created new chatbot configuration with Ukrainian language enforcement")
        
        db.close()
        
        logger.info("🎉 Chatbot configuration setup completed successfully!")
        logger.info("💡 Ukrainian language enforcement is now active!")
        
    except Exception as e:
        logger.error(f"❌ Failed to setup chatbot configuration: {e}")
        return False
    
    return True


def main():
    """Main function."""
    logger.info("🚀 Chatbot Configuration Setup Script")
    logger.info("=" * 50)
    
    if setup_chatbot_config():
        logger.info("=" * 50)
        logger.info("🎉 Success! Your chatbot is now configured with Ukrainian language enforcement.")
        logger.info("💡 Try testing the chatbot - it should now respond only in Ukrainian!")
    else:
        logger.error("❌ Setup failed! Check the error messages above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
