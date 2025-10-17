"""Prompt logging model for auditing AI interactions."""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey

from app.database import Base


class PromptLog(Base):
    """Stores metadata for prompts and responses for audit and debugging."""

    __tablename__ = "prompt_logs"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=True)
    config_id = Column(Integer, ForeignKey("chatbot_configs.id"), nullable=True)

    model = Column(String, nullable=True)
    system_prompt_hash = Column(String, nullable=True)

    user_message = Column(Text, nullable=True)
    request_json = Column(Text, nullable=True)
    response_json = Column(Text, nullable=True)

    duration_ms = Column(Integer, nullable=True)
    error = Column(Text, nullable=True)


