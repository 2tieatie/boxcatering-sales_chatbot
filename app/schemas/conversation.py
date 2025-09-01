"""Conversation schemas for API requests and responses."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel

from app.models.conversation import HandoverState


class ConversationResponse(BaseModel):
    """Conversation response schema."""
    id: int
    session_id: str
    customer_id: Optional[int] = None
    assigned_to: Optional[int] = None
    handover_state: HandoverState
    handover_reason: Optional[str] = None
    handover_reason_description: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ConversationUpdate(BaseModel):
    """Conversation update schema."""
    assigned_to: Optional[int] = None
    handover_state: Optional[HandoverState] = None
    handover_reason: Optional[str] = None
    handover_reason_description: Optional[str] = None
