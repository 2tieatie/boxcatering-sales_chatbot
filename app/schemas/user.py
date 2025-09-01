"""User schemas for authentication and management."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr

from app.models.user import UserRole


class UserBase(BaseModel):
    """Base user schema."""
    username: str
    email: EmailStr
    full_name: str
    role: UserRole = UserRole.MANAGER


class UserCreate(UserBase):
    """User creation schema."""
    password: str


class UserUpdate(BaseModel):
    """User update schema."""
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


class UserResponse(UserBase):
    """User response schema."""
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    """User login schema."""
    username: str
    password: str


class Token(BaseModel):
    """Token schema."""
    access_token: str
    token_type: str


class TokenData(BaseModel):
    """Token data schema."""
    username: Optional[str] = None


class PasswordChange(BaseModel):
    """Password change schema."""
    current_password: str
    new_password: str
