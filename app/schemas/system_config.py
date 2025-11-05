"""System configuration schemas."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class SystemConfigBase(BaseModel):
    """Base system configuration schema."""

    key: str
    value: str
    description: Optional[str] = None
    is_sensitive: bool = False


class SystemConfigCreate(SystemConfigBase):
    """System configuration creation schema."""

    pass


class SystemConfigUpdate(BaseModel):
    """System configuration update schema."""

    value: Optional[str] = None
    description: Optional[str] = None
    is_sensitive: Optional[bool] = None


class SystemConfigResponse(SystemConfigBase):
    """System configuration response schema."""

    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
