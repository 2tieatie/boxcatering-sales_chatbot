"""Chatbot configuration model."""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from datetime import datetime, timezone

from app.database import Base


class ChatbotConfig(Base):
    """Chatbot configuration model."""
    
    __tablename__ = "chatbot_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    welcome_message = Column(Text, nullable=False)
    business_context = Column(Text, nullable=False)
    language = Column(String, default="uk", nullable=False)  # Default to Ukrainian
    force_language = Column(Boolean, default=True, nullable=False)  # Default to strict language enforcement
    is_active = Column(Boolean, default=True)
    
    # Additional fields for enhanced configuration
    company_name = Column(String, nullable=True)
    specializations = Column(Text, nullable=True)
    friendly_tone = Column(Boolean, default=True, nullable=True)
    professional_style = Column(Boolean, default=True, nullable=True)
    suggestive_responses = Column(Boolean, default=True, nullable=True)
    manager_handover = Column(Boolean, default=True, nullable=True)
    fallback_message = Column(Text, nullable=True)
    handover_message = Column(Text, nullable=True)
    response_timeout = Column(Integer, default=30, nullable=True)
    conversation_logging = Column(Boolean, default=True, nullable=True)
    performance_analytics = Column(Boolean, default=True, nullable=True)
    error_reporting = Column(Boolean, default=True, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    def __repr__(self):
        return f"<ChatbotConfig(id={self.id}, name='{self.name}', is_active={self.is_active})>"
