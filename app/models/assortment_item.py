"""Assortment item model representing products offered for sale."""

from __future__ import annotations

from datetime import datetime
from sqlalchemy import Column, Integer, String, Numeric, DateTime

from app.database import Base


class AssortmentItem(Base):
    """SQLAlchemy model for assortment items.

    Stores item name, description, and price in UAH.
    """

    __tablename__ = "assortment_items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(String, nullable=True)
    price_uah = Column(Numeric(10, 2), nullable=False, default=0)
    guests = Column(Integer, nullable=True)
    weight = Column(Numeric(10, 2), nullable=True, default=1)
    created_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<AssortmentItem(id={self.id}, name='{self.name}', price_uah={self.price_uah})>"
