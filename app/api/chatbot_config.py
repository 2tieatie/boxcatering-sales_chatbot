"""Chatbot configuration API endpoints."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ChatbotConfig, User
from app.schemas.chatbot_config import ChatbotConfigCreate, ChatbotConfigUpdate, ChatbotConfigResponse
from app.services.auth_service import AuthService
from app.services.role_service import RoleService

router = APIRouter(prefix="/chatbot-config", tags=["chatbot-config"])
auth_service = AuthService()
role_service = RoleService()


def require_admin_or_system_admin(current_user: User = Depends(auth_service.get_current_active_user)) -> User:
    """Dependency to require admin or system admin role."""
    return role_service.require_admin_or_system_admin(current_user)


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


@router.get("/{config_id}", response_model=ChatbotConfigResponse)
async def get_chatbot_config(
    config_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_system_admin)
):
    """Get chatbot configuration by ID (admin and system admin only)."""
    config = db.query(ChatbotConfig).filter(ChatbotConfig.id == config_id).first()
    if config is None:
        raise HTTPException(status_code=404, detail="Chatbot configuration not found")
    return config


@router.get("/active", response_model=ChatbotConfigResponse)
async def get_active_chatbot_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_active_user)  # All authenticated users can see active config
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
    # If this is the first config, make it active
    existing_configs = db.query(ChatbotConfig).count()
    if existing_configs == 0:
        config_data.is_active = True
    
    # Create new config
    db_config = ChatbotConfig(**config_data.model_dump())
    db.add(db_config)
    db.commit()
    db.refresh(db_config)
    
    return db_config


@router.put("/{config_id}", response_model=ChatbotConfigResponse)
async def update_chatbot_config(
    config_id: int,
    config_data: ChatbotConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_system_admin)
):
    """Update chatbot configuration (admin and system admin only)."""
    config = db.query(ChatbotConfig).filter(ChatbotConfig.id == config_id).first()
    if config is None:
        raise HTTPException(status_code=404, detail="Chatbot configuration not found")
    
    # Update fields
    update_data = config_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(config, field, value)
    
    # If setting this config as active, deactivate others
    if config_data.is_active:
        db.query(ChatbotConfig).filter(ChatbotConfig.id != config_id).update({"is_active": False})
    
    db.commit()
    db.refresh(config)
    return config


@router.delete("/{config_id}")
async def delete_chatbot_config(
    config_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_system_admin)
):
    """Delete chatbot configuration (admin and system admin only)."""
    config = db.query(ChatbotConfig).filter(ChatbotConfig.id == config_id).first()
    if config is None:
        raise HTTPException(status_code=404, detail="Chatbot configuration not found")
    
    # Don't allow deletion of active config if it's the only one
    if config.is_active:
        total_configs = db.query(ChatbotConfig).count()
        if total_configs == 1:
            raise HTTPException(
                status_code=400, 
                detail="Cannot delete the only chatbot configuration"
            )
    
    db.delete(config)
    db.commit()
    
    return {"message": "Chatbot configuration deleted successfully"}
