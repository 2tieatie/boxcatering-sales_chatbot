"""Application configuration and settings."""

import os
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Database
    database_url: str = Field(..., env="DATABASE_URL")
    
    # OpenAI
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-5", env="OPENAI_MODEL")
    openai_temperature: float = Field(default=0.7, env="OPENAI_TEMPERATURE")
    openai_max_tokens: int = Field(default=500, env="OPENAI_MAX_TOKENS")
    
    # Telegram
    telegram_bot_token: Optional[str] = Field(None, env="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: Optional[str] = Field(None, env="TELEGRAM_CHAT_ID")
    
    # Security
    secret_key: str = Field(..., env="SECRET_KEY")
    algorithm: str = Field(default="HS256", env="ALGORITHM")
    access_token_expire_minutes: int = Field(default=60, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # Application
    debug: bool = Field(default=False, env="DEBUG")
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    
    # Context documents
    context_docs_enabled: bool = Field(default=True, env="CONTEXT_DOCS_ENABLED")
    context_docs_dir: str = Field(
        default="agent_context_documents", env="CONTEXT_DOCS_DIR"
    )
    context_docs_max_chars: int = Field(
        default=4000, env="CONTEXT_DOCS_MAX_CHARS"
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Lazy loading of settings - only load when accessed
_settings = None

def get_settings() -> Settings:
    """Get settings instance, loading from environment if needed."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings

# For backward compatibility
settings = get_settings()
