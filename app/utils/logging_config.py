"""Centralized logging configuration for the application."""

import sys
import json
from datetime import datetime

from pathlib import Path
from loguru import logger
from typing import Dict, Any


class LoggingConfig:
    """Centralized logging configuration."""
    
    def __init__(self):
        self.logs_dir = Path("logs")
        self.logs_dir.mkdir(exist_ok=True)
        
    def setup_logging(self):
        """Configure loguru sinks for different log types."""
        # Remove default handler
        logger.remove()
        
        # Console logging
        logger.add(
            sys.stdout,
            level="INFO",
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            colorize=True
        )
        
        # Application log (general app events)
        logger.add(
            self.logs_dir / "app.log",
            level="DEBUG",
            rotation="10 MB",
            retention="14 days",
            enqueue=True,
            backtrace=False,
            diagnose=False,
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
            filter=lambda record: record["extra"].get("log_type", "app") == "app"
        )
        
        # Prompt log (AI interactions)
        logger.add(
            self.logs_dir / "prompt.log",
            level="DEBUG",
            rotation="10 MB",
            retention="14 days",
            enqueue=True,
            backtrace=False,
            diagnose=False,
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {message}",
            filter=lambda record: record["extra"].get("log_type") == "prompt"
        )
        
        # HTTP request/response log
        logger.add(
            self.logs_dir / "http.log",
            level="INFO",
            rotation="10 MB",
            retention="7 days",
            enqueue=True,
            backtrace=False,
            diagnose=False,
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {message}",
            filter=lambda record: record["extra"].get("log_type") == "http"
        )
        
        # Error log (critical errors only)
        logger.add(
            self.logs_dir / "error.log",
            level="ERROR",
            rotation="5 MB",
            retention="30 days",
            enqueue=True,
            backtrace=True,
            diagnose=True,
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
            filter=lambda record: record["level"].name == "ERROR"
        )

# Global instance
logging_config = LoggingConfig()

def get_logger(log_type: str = "app"):
    """Get a logger with specific log type."""
    return logger.bind(log_type=log_type)
