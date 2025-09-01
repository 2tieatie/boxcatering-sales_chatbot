#!/usr/bin/env python3
"""Complete setup script for Boxcatering Chatbot."""

import os
import sys
import subprocess
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables early
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from loguru import logger


def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 8):
        logger.error("❌ Python 3.8 or higher is required!")
        sys.exit(1)
    logger.info(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")


def check_dependencies():
    """Check if required dependencies are installed."""
    try:
        import fastapi
        import sqlalchemy
        import pydantic
        logger.info("✅ Required Python packages are installed")
    except ImportError as e:
        logger.error(f"❌ Missing required package: {e}")
        logger.info("Please install dependencies with: pip install -r requirements.txt")
        sys.exit(1)


def check_env_file():
    """Check and create .env file if needed."""
    env_file = project_root / ".env"
    env_example = project_root / "env.example"
    
    if not env_file.exists():
        if env_example.exists():
            logger.info("📝 Creating .env file from template...")
            with open(env_example, 'r') as f:
                env_content = f.read()
            
            # Replace placeholder values with more appropriate defaults
            env_content = env_content.replace(
                "DATABASE_URL=postgresql://user:password@localhost/boxcatering_chatbot",
                "DATABASE_URL=postgresql://postgres:postgres@localhost/boxcatering_chatbot"
            )
            env_content = env_content.replace(
                "SECRET_KEY=your_secret_key_here_make_it_long_and_random",
                "SECRET_KEY=dev_secret_key_change_in_production_very_long_random_string_here"
            )
            
            with open(env_file, 'w') as f:
                f.write(env_content)
            
            logger.info("✅ .env file created successfully!")
            logger.warning("⚠️  Please review and update the .env file with your actual values!")
        else:
            logger.error("❌ env.example file not found!")
            sys.exit(1)
    else:
        logger.info("✅ .env file already exists")


def check_database():
    """Check if database is accessible."""
    try:
        # Load environment variables first
        from dotenv import load_dotenv
        load_dotenv()
        
        from app.database import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✅ Database connection successful!")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        logger.info("Please ensure:")
        logger.info("1. PostgreSQL is running")
        logger.info("2. Database 'boxcatering_chatbot' exists")
        logger.info("3. Database credentials in .env are correct")
        sys.exit(1)


def init_database():
    """Initialize database tables."""
    try:
        logger.info("🗄️  Initializing database...")
        subprocess.run([sys.executable, "scripts/init_db.py"], check=True)
        logger.info("✅ Database tables created successfully!")
    except subprocess.CalledProcessError:
        logger.error("❌ Failed to initialize database")
        sys.exit(1)


def create_admin_user():
    """Create initial system administrator user."""
    try:
        logger.info("👤 Creating system administrator user...")
        subprocess.run([sys.executable, "scripts/create_admin.py"], check=True)
        logger.info("✅ Admin user created successfully!")
    except subprocess.CalledProcessError:
        logger.error("❌ Failed to create admin user")
        sys.exit(1)


def print_next_steps():
    """Print next steps for the user."""
    logger.info("\n🎉 Setup completed successfully!")
    logger.info("\n📋 Next steps:")
    logger.info("1. Start the application: python -m app.main")
    logger.info("2. Open your browser and go to: http://localhost:8000")
    logger.info("3. Login with:")
    logger.info("   - Username: admin")
    logger.info("   - Password: admin123")
    logger.info("4. ⚠️  IMPORTANT: Change the default password after first login!")
    logger.info("\n🔧 To start the app, run: python -m app.main")


def main():
    """Main setup function."""
    logger.info("🚀 Setting up Boxcatering Chatbot...")
    logger.info("=" * 50)
    
    check_python_version()
    check_dependencies()
    check_env_file()
    check_database()
    init_database()
    create_admin_user()
    
    logger.info("=" * 50)
    print_next_steps()


if __name__ == "__main__":
    main()
