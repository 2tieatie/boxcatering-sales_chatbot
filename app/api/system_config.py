"""System configuration API endpoints."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import SystemConfig, User
from app.schemas.system_config import SystemConfigCreate, SystemConfigUpdate, SystemConfigResponse
from app.services.auth_service import AuthService
from app.services.role_service import RoleService

router = APIRouter(prefix="/system-config", tags=["system-config"])
auth_service = AuthService()
role_service = RoleService()


def require_system_admin(current_user: User = Depends(auth_service.get_current_active_user)) -> User:
    """Dependency to require system admin role."""
    return role_service.require_system_admin(current_user)


@router.get("/", response_model=List[SystemConfigResponse])
async def get_system_configs(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_system_admin)
):
    """Get list of system configurations (system admin only)."""
    configs = db.query(SystemConfig).offset(skip).limit(limit).all()
    return configs


@router.get("/{config_id}", response_model=SystemConfigResponse)
async def get_system_config(
    config_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_system_admin)
):
    """Get system configuration by ID (system admin only)."""
    config = db.query(SystemConfig).filter(SystemConfig.id == config_id).first()
    if config is None:
        raise HTTPException(status_code=404, detail="System configuration not found")
    return config


@router.get("/key/{key}", response_model=SystemConfigResponse)
async def get_system_config_by_key(
    key: str, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_system_admin)
):
    """Get system configuration by key (system admin only)."""
    config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    if config is None:
        raise HTTPException(status_code=404, detail="System configuration not found")
    return config


@router.post("/", response_model=SystemConfigResponse)
async def create_system_config(
    config_data: SystemConfigCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_system_admin)
):
    """Create new system configuration (system admin only)."""
    # Check if key already exists
    existing_config = db.query(SystemConfig).filter(SystemConfig.key == config_data.key).first()
    if existing_config:
        raise HTTPException(status_code=400, detail="Configuration key already exists")
    
    # Create new config
    db_config = SystemConfig(**config_data.model_dump())
    db.add(db_config)
    db.commit()
    db.refresh(db_config)
    
    return db_config


@router.put("/{config_id}", response_model=SystemConfigResponse)
async def update_system_config(
    config_id: int,
    config_data: SystemConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_system_admin)
):
    """Update system configuration (system admin only)."""
    config = db.query(SystemConfig).filter(SystemConfig.id == config_id).first()
    if config is None:
        raise HTTPException(status_code=404, detail="System configuration not found")
    
    # Update fields
    update_data = config_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(config, field, value)
    
    db.commit()
    db.refresh(config)
    return config


@router.delete("/{config_id}")
async def delete_system_config(
    config_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_system_admin)
):
    """Delete system configuration (system admin only)."""
    config = db.query(SystemConfig).filter(SystemConfig.id == config_id).first()
    if config is None:
        raise HTTPException(status_code=404, detail="System configuration not found")
    
    db.delete(config)
    db.commit()
    
    return {"message": "System configuration deleted successfully"}
