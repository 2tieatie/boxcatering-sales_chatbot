"""Simple chatbot configuration API endpoints."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ChatbotConfig, User
from app.schemas.chatbot_config import ChatbotConfigCreate, ChatbotConfigUpdate, ChatbotConfigResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/chatbot-config", tags=["chatbot-config"])
auth_service = AuthService()


def require_admin_or_system_admin(current_user: User = Depends(auth_service.get_current_active_user)) -> User:
    """Dependency to require admin or system admin role."""
    if current_user.role not in ["admin", "system_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Required roles: admin or system_admin"
        )
    return current_user


@router.get("/", response_model=List[ChatbotConfigResponse])
async def get_chatbot_configs(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_system_admin)
):
    """Get list of chatbot configurations (admin and system admin only)."""
    configs = db.query(ChatbotConfig).offset(skip).limit(limit).all()
    return configs


@router.get("/active", response_model=ChatbotConfigResponse)
async def get_active_chatbot_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_active_user)
):
    """Get active chatbot configuration (all authenticated users)."""
    config = db.query(ChatbotConfig).filter(ChatbotConfig.is_active == True).first()
    if config is None:
        raise HTTPException(status_code=404, detail="No active chatbot configuration found")
    return config


@router.post("/", response_model=ChatbotConfigResponse)
async def create_chatbot_config(
    config_data: ChatbotConfigCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_system_admin)
):
    """Create new chatbot configuration (admin and system admin only)."""
    from datetime import datetime, timezone
    
    # If this is the first config, make it active
    existing_configs = db.query(ChatbotConfig).count()
    if existing_configs == 0:
        config_data.is_active = True
    
    # Prepare data with explicit datetime values
    config_dict = config_data.model_dump()
    current_time = datetime.now(timezone.utc)
    config_dict["created_at"] = current_time
    config_dict["updated_at"] = current_time
    
    # Create new config
    db_config = ChatbotConfig(**config_dict)
    db.add(db_config)
    db.commit()
    db.refresh(db_config)
    
    return db_config
