"""Message schemas for API responses."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class MessageResponse(BaseModel):
    """Message response schema.

    Represents a chat message stored in the database.
    """

    id: int
    chat_id: int
    sender: str
    channel: str
    text: str
    timestamp: Optional[datetime] = None

    class Config:
        from_attributes = True


