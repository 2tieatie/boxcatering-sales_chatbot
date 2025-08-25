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
    
    # Additional fields for enhanced configuration
    company_name: Optional[str] = Field(None, description="Company name")
    specializations: Optional[str] = Field(None, description="Business specializations")
    friendly_tone: Optional[bool] = Field(True, description="Use friendly tone")
    professional_style: Optional[bool] = Field(True, description="Maintain professional style")
    suggestive_responses: Optional[bool] = Field(True, description="Offer follow-up suggestions")
    manager_handover: Optional[bool] = Field(True, description="Enable manager handover")
    fallback_message: Optional[str] = Field(None, description="Fallback message when AI can't understand")
    handover_message: Optional[str] = Field(None, description="Message when transferring to manager")
    response_timeout: Optional[int] = Field(30, description="Response timeout in seconds")
    conversation_logging: Optional[bool] = Field(True, description="Enable conversation logging")
    performance_analytics: Optional[bool] = Field(True, description="Enable performance analytics")
    error_reporting: Optional[bool] = Field(True, description="Enable error reporting")


class ChatbotConfigCreate(BaseModel):
    """Chatbot configuration creation schema."""
    name: str = Field(..., min_length=1, description="Configuration name")
    prompt: str = Field(..., min_length=1, description="Chatbot prompt/message")
    business_context: str = Field(..., min_length=1, description="Business context description")
    language: str = Field(default="uk", min_length=2, max_length=5, description="Language code")
    force_language: bool = Field(default=True, description="Whether to enforce language compliance")
    is_active: Optional[bool] = Field(False, description="Whether this configuration is active")
    
    # Additional fields for enhanced configuration
    company_name: Optional[str] = Field(None, description="Company name")
    specializations: Optional[str] = Field(None, description="Business specializations")
    friendly_tone: Optional[bool] = Field(True, description="Use friendly tone")
    professional_style: Optional[bool] = Field(True, description="Maintain professional style")
    suggestive_responses: Optional[bool] = Field(True, description="Offer follow-up suggestions")
    manager_handover: Optional[bool] = Field(True, description="Enable manager handover")
    fallback_message: Optional[str] = Field(None, description="Fallback message when AI can't understand")
    handover_message: Optional[str] = Field(None, description="Message when transferring to manager")
    response_timeout: Optional[int] = Field(30, description="Response timeout in seconds")
    conversation_logging: Optional[bool] = Field(True, description="Enable conversation logging")
    performance_analytics: Optional[bool] = Field(True, description="Enable performance analytics")
    error_reporting: Optional[bool] = Field(True, description="Enable error reporting")


class ChatbotConfigUpdate(BaseModel):
    """Chatbot configuration update schema."""
    name: Optional[str] = Field(None, min_length=1, description="Configuration name")
    prompt: Optional[str] = Field(None, min_length=1, description="Chatbot prompt/message")
    business_context: Optional[str] = Field(None, min_length=1, description="Business context description")
    language: Optional[str] = Field(None, min_length=2, max_length=5, description="Language code")
    force_language: Optional[bool] = Field(None, description="Whether to enforce language compliance")
    is_active: Optional[bool] = Field(None, description="Whether this configuration is active")
    
    # Additional fields for enhanced configuration
    company_name: Optional[str] = Field(None, description="Company name")
    specializations: Optional[str] = Field(None, description="Business specializations")
    friendly_tone: Optional[bool] = Field(None, description="Use friendly tone")
    professional_style: Optional[bool] = Field(None, description="Maintain professional style")
    suggestive_responses: Optional[bool] = Field(None, description="Offer follow-up suggestions")
    manager_handover: Optional[bool] = Field(None, description="Enable manager handover")
    fallback_message: Optional[str] = Field(None, description="Fallback message when AI can't understand")
    handover_message: Optional[str] = Field(None, description="Message when transferring to manager")
    response_timeout: Optional[int] = Field(None, description="Response timeout in seconds")
    conversation_logging: Optional[bool] = Field(None, description="Enable conversation logging")
    performance_analytics: Optional[bool] = Field(None, description="Enable performance analytics")
    error_reporting: Optional[bool] = Field(None, description="Enable error reporting")


class ChatbotConfigResponse(ChatbotConfigBase):
    """Chatbot configuration response schema."""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
