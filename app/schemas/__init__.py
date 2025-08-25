"""Pydantic schemas for API requests and responses."""

from .chat import ChatRequest, ChatResponse, HandoverReason
from .user import UserCreate, UserUpdate, UserResponse, UserLogin, Token, TokenData, PasswordChange, UserBase, UserInDB
from .conversation import ConversationResponse, ConversationUpdate
from .order import OrderResponse, OrderUpdate
from .customer import CustomerCreate, CustomerResponse

from .chatbot_config import ChatbotConfigCreate, ChatbotConfigUpdate, ChatbotConfigResponse
from .system_config import SystemConfigCreate, SystemConfigUpdate, SystemConfigResponse

__all__ = [
    "ChatRequest",
    "ChatResponse", 
    "HandoverReason",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserLogin",
    "Token",
    "TokenData",
    "PasswordChange",
    "UserBase",
    "UserInDB",
    "ConversationResponse",
    "ConversationUpdate",
    "OrderResponse",
    "OrderUpdate",
    "CustomerCreate",
    "CustomerResponse",
    "ChatbotConfigCreate",
    "ChatbotConfigUpdate",
    "ChatbotConfigResponse",
    "SystemConfigCreate",
    "SystemConfigUpdate",
    "SystemConfigResponse"
]
