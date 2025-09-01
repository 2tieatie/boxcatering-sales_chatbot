"""Chatbot configuration schemas."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ChatbotConfigBase(BaseModel):
    """Base chatbot configuration schema."""
    name: str
    prompt: str
    business_context: str
    language: str = "uk"  # Default to Ukrainian
    force_language: bool = True  # Default to strict language enforcement
    is_active: bool = False


class ChatbotConfigCreate(ChatbotConfigBase):
    """Chatbot configuration creation schema."""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ChatbotConfigUpdate(BaseModel):
    """Chatbot configuration update schema."""
    name: Optional[str] = None
    prompt: Optional[str] = None
    business_context: Optional[str] = None
    language: Optional[str] = None
    force_language: Optional[bool] = None
    is_active: Optional[bool] = None


class ChatbotConfigResponse(ChatbotConfigBase):
    """Chatbot configuration response schema."""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
