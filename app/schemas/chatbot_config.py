"""Chatbot configuration schemas."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ChatbotConfigBase(BaseModel):
    """Base chatbot configuration schema."""
    name: str = Field(..., min_length=1, description="Configuration name")
    prompt: str = Field(..., min_length=1, description="Chatbot prompt/message")
    business_context: str = Field(..., min_length=1, description="Business context description")
    language: str = Field(default="uk", min_length=2, max_length=5, description="Language code")
    force_language: bool = Field(default=True, description="Whether to enforce language compliance")
    is_active: bool = Field(default=False, description="Whether this configuration is active")


class ChatbotConfigCreate(ChatbotConfigBase):
    """Chatbot configuration creation schema."""
    pass


class ChatbotConfigUpdate(BaseModel):
    """Chatbot configuration update schema."""
    name: Optional[str] = Field(None, min_length=1, description="Configuration name")
    prompt: Optional[str] = Field(None, min_length=1, description="Chatbot prompt/message")
    business_context: Optional[str] = Field(None, min_length=1, description="Business context description")
    language: Optional[str] = Field(None, min_length=2, max_length=5, description="Language code")
    force_language: Optional[bool] = Field(None, description="Whether to enforce language compliance")
    is_active: Optional[bool] = Field(None, description="Whether this configuration is active")


class ChatbotConfigResponse(ChatbotConfigBase):
    """Chatbot configuration response schema."""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
