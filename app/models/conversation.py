"""Conversation model for chat sessions."""

from enum import Enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLEnum, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class HandoverState(str, Enum):
    """Handover state enumeration."""
    NONE = "none"
    HANDOVER_PENDING = "handover_pending"
    HANDOVER_IN_PROGRESS = "handover_in_progress"
    RESOLVED_BY_MANAGER = "resolved_by_manager"


class Conversation(Base):
    """Conversation model."""
    
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    handover_state = Column(SQLEnum(HandoverState), default=HandoverState.NONE)
    handover_reason = Column(String, nullable=True)
    handover_reason_description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    customer = relationship("Customer", back_populates="conversations")
    assigned_user = relationship("User")
    messages = relationship("Message", back_populates="conversation")
    
    def __repr__(self):
        return f"<Conversation(id={self.id}, session_id='{self.session_id}', handover_state='{self.handover_state}')>"
