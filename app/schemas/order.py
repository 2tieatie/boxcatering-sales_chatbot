"""Order schemas for API requests and responses."""

from datetime import datetime
from typing import Optional
from decimal import Decimal
from pydantic import BaseModel

from app.models.order import OrderState


class OrderResponse(BaseModel):
    """Order response schema."""
    id: int
    order_number: str
    customer_id: int
    conversation_id: Optional[int] = None
    state: OrderState
    total_amount: Decimal
    currency: str
    notes: Optional[str] = None
    is_processed: bool
    processed_by: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class OrderUpdate(BaseModel):
    """Order update schema."""
    state: Optional[OrderState] = None
    total_amount: Optional[Decimal] = None
    notes: Optional[str] = None
    is_processed: Optional[bool] = None
    processed_by: Optional[int] = None
