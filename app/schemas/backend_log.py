"""Backend log schemas."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class BackendLogBase(BaseModel):
    """Base backend log schema."""
    user_id: Optional[int] = None
    conversation_id: Optional[int] = None
    config_id: Optional[int] = None
    log_info: Optional[str] = None
    error_info: Optional[str] = None


class BackendLogCreate(BaseModel):
    """Backend log creation schema."""
    user_id: Optional[int] = None
    conversation_id: Optional[int] = None
    config_id: Optional[int] = None
    log_info: Optional[str] = None
    error_info: Optional[str] = None

class BackendLogResponse(BackendLogBase):
    """Backend log response schema."""
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
