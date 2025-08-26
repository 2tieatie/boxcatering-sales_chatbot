#!/usr/bin/env python3
"""Development startup script."""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

if __name__ == "__main__":
    # Check if .env file exists
    env_file = project_root / ".env"
    if not env_file.exists():
        print("⚠️  Warning: .env file not found!")
        print("Please copy env.example to .env and configure your settings.")
        print()
    
    # Import and run the app
    try:
        from app.main import app
        import uvicorn
        
        print("🚀 Starting Boxcatering Chatbot...")
        print("📖 API Documentation: http://localhost:8000/docs")
        print("🔌 WebSocket endpoint: http://localhost:8000/chat/ws")
        print("💚 Health check: http://localhost:8000/health")
        print()
        
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="debug"
        )
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Please install dependencies: pip install -e .")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error starting application: {e}")
        sys.exit(1)
