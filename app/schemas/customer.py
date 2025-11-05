"""Customer schemas for API requests and responses."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class CustomerCreate(BaseModel):
    """Customer creation schema."""

    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None


class CustomerUpdate(BaseModel):
    """Customer update schema."""

    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None


class CustomerResponse(BaseModel):
    """Customer response schema."""

    id: int
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
