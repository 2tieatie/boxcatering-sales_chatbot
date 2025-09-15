"""Order model for customer orders."""

from enum import Enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLEnum, ForeignKey, Text, Numeric, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class OrderState(str, Enum):
    """Order state enumeration."""
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Order(Base):
    """Order model."""
    
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String, unique=True, index=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=True)
    state = Column(SQLEnum(OrderState), default=OrderState.DRAFT)
    total_amount = Column(Numeric(10, 2), nullable=False, default=0)
    currency = Column(String, default="UAH")
    # Scheduling and content
    delivery_date = Column(DateTime(timezone=True), nullable=True)
    delivery_time = Column(String, nullable=True)
    menu_items = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    is_processed = Column(Boolean, default=False)
    processed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    priority = Column(String, nullable=True)
    guests_count = Column(Integer, nullable=True)
    
    # Relationships
    customer = relationship("Customer", back_populates="orders")
    conversation = relationship("Conversation")
    processed_user = relationship("User")
    
    def __repr__(self):
        return f"<Order(id={self.id}, order_number='{self.order_number}', state='{self.state}')>"
