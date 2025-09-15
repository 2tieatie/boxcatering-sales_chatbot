"""Order schemas for API requests and responses."""

from datetime import datetime
from typing import Optional
from decimal import Decimal
from pydantic import BaseModel

from app.models.order import OrderState
from app.schemas.customer import CustomerResponse


class OrderCreate(BaseModel):
    """Order creation schema.

    Used by API and internal chat flow to create a new order.
    """
    customer_id: Optional[int] = None
    # When customer_id is not provided, use these to create or resolve a customer
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_address: Optional[str] = None
    conversation_id: Optional[int] = None
    state: Optional[OrderState] = None
    total_amount: Optional[Decimal] = None
    currency: Optional[str] = None
    notes: Optional[str] = None
    delivery_date: Optional[datetime] = None
    delivery_time: Optional[str] = None
    menu_items: Optional[str] = None
    priority: Optional[str] = None
    guests_count: Optional[int] = None


class OrderResponse(BaseModel):
    """Order response schema."""
    id: int
    order_number: str
    customer_id: int
    conversation_id: Optional[int] = None
    state: OrderState
    total_amount: Decimal
    currency: str
    delivery_date: Optional[datetime] = None
    delivery_time: Optional[str] = None
    menu_items: Optional[str] = None
    notes: Optional[str] = None
    is_processed: bool
    processed_by: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    customer: Optional[CustomerResponse] = None
    priority: Optional[str] = None
    guests_count: Optional[int] = None
    
    class Config:
        from_attributes = True


class OrderUpdate(BaseModel):
    """Order update schema."""
    state: Optional[OrderState] = None
    total_amount: Optional[Decimal] = None
    notes: Optional[str] = None
    is_processed: Optional[bool] = None
    processed_by: Optional[int] = None
    priority: Optional[str] = None
