"""Chat schemas for WebSocket communication."""

from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel


class HandoverReason(str, Enum):
    """Handover reason enumeration."""

    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    SENSITIVE_CASE = "SENSITIVE_CASE"
    TECH_OR_FINANCIAL_LIMITATION = "TECH_OR_FINANCIAL_LIMITATION"
    USER_REQUEST_MANAGER = "USER_REQUEST_MANAGER"


class ChatRequest(BaseModel):
    """Chat request schema."""

    session_id: str
    sender: str
    message: str
    timestamp: datetime


class ChatResponse(BaseModel):
    """Chat response schema."""

    response: str
    handover_to_manager: bool = False
    handover_reason: Optional[HandoverReason] = None
    handover_reason_description: Optional[str] = None
    debug: Optional[Dict[str, Any]] = None
    # Optional action to instruct the app to perform something (e.g., create order)
    action: Optional[str] = None
    # Optional payload for actions, free-form to allow incremental evolution
    data: Optional[Dict[str, Any]] = None


class SummaryRequest(BaseModel):
    """Summary request schema."""

    conversation_id: int
    mappedMessages: str
