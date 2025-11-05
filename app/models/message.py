"""Message model for chat messages."""

from enum import Enum
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class MessageSender(str, Enum):
    """Message sender enumeration."""

    USER = "user"
    BOT = "bot"
    MANAGER = "manager"


class MessageChannel(str, Enum):
    """Message channel enumeration."""

    WEB = "web"
    TELEGRAM = "telegram"


class Message(Base):
    """Message model."""

    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    sender = Column(SQLEnum(MessageSender), nullable=False)
    channel = Column(SQLEnum(MessageChannel), default=MessageChannel.WEB)
    text = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")

    def __repr__(self):
        return (
            f"<Message(id={self.id}, sender='{self.sender}', channel='{self.channel}')>"
        )
