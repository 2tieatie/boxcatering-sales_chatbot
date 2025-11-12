"""Schemas for assortment items API."""

from __future__ import annotations

from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel


class AssortmentItemResponse(BaseModel):
    """Response schema representing an assortment item."""

    id: int
    name: str
    description: Optional[str] = None
    menu: Optional[str] = None
    print_label: Optional[str] = None
    category: Optional[str] = None
    slug: Optional[str] = None
    img: Optional[str] = None
    type: Optional[str] = None
    price_uah: Decimal
    guests: Optional[int] = None
    weight: Optional[Decimal] = None

    class Config:
        from_attributes = True


class AssortmentUploadResult(BaseModel):
    """Response schema for Excel upload results."""

    replaced: bool
    total_rows: int
    imported: int
    skipped: int
    errors: Optional[List[str]] = None
