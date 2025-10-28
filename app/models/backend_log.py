"""Prompt logging model for auditing AI interactions."""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, DateTime, Text, ForeignKey

from app.database import Base


class BackendLog(Base):
    """Stores metadata for audit and debugging."""

    __tablename__ = "backend_logs"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=True)
    config_id = Column(Integer, ForeignKey("chatbot_configs.id"), nullable=True)

    log_info = Column(Text, nullable=True)

    error = Column(Text, nullable=True)
