"""System configuration model for system parameters."""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.sql import func

from app.database import Base


class SystemConfig(Base):
    """System configuration model."""
    
    __tablename__ = "system_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True, nullable=False)
    value = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    is_sensitive = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<SystemConfig(id={self.id}, key='{self.key}', is_sensitive={self.is_sensitive})>"
