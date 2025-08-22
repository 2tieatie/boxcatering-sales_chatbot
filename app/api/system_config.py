"""System configuration API endpoints."""

from typing import List, Dict, Any
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
    """Get all system configurations (system admin only)."""
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


@router.get("/settings/all", response_model=Dict[str, Any])
async def get_all_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_system_admin)
):
    """Get all settings organized by category (system admin only)."""
    configs = db.query(SystemConfig).all()
    
    # Organize settings by category
    settings = {
        "openai": {},
        "telegram": {},
        "system": {},
        "security": {}
    }
    
    for config in configs:
        if config.key.startswith("openai_"):
            settings["openai"][config.key.replace("openai_", "")] = config.value
        elif config.key.startswith("telegram_"):
            settings["telegram"][config.key.replace("telegram_", "")] = config.value
        elif config.key.startswith("system_"):
            settings["system"][config.key.replace("system_", "")] = config.value
        elif config.key.startswith("security_"):
            settings["security"][config.key.replace("security_", "")] = config.value
    
    return settings


@router.post("/settings/bulk", response_model=Dict[str, str])
async def save_bulk_settings(
    settings: Dict[str, Dict[str, Any]],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_system_admin)
):
    """Save multiple settings at once (system admin only)."""
    results = {}
    
    for category, category_settings in settings.items():
        for key, value in category_settings.items():
            if value is not None and value != "":
                full_key = f"{category}_{key}"
                
                # Check if config exists
                existing_config = db.query(SystemConfig).filter(SystemConfig.key == full_key).first()
                
                if existing_config:
                    # Update existing config
                    existing_config.value = str(value)
                    results[full_key] = "updated"
                else:
                    # Create new config
                    is_sensitive = key in ["api_key", "bot_token", "jwt_secret"]
                    new_config = SystemConfig(
                        key=full_key,
                        value=str(value),
                        description=f"{category.title()} {key.replace('_', ' ').title()}",
                        is_sensitive=is_sensitive
                    )
                    db.add(new_config)
                    results[full_key] = "created"
    
    db.commit()
    return results


@router.post("/settings/openai", response_model=Dict[str, str])
async def save_openai_settings(
    settings: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_system_admin)
):
    """Save OpenAI settings (system admin only)."""
    results = {}
    
    for key, value in settings.items():
        if value is not None and value != "":
            full_key = f"openai_{key}"
            
            # Check if config exists
            existing_config = db.query(SystemConfig).filter(SystemConfig.key == full_key).first()
            
            if existing_config:
                # Update existing config
                existing_config.value = str(value)
                results[full_key] = "updated"
            else:
                # Create new config
                is_sensitive = key == "api_key"
                new_config = SystemConfig(
                    key=full_key,
                    value=str(value),
                    description=f"OpenAI {key.replace('_', ' ').title()}",
                    is_sensitive=is_sensitive
                )
                db.add(new_config)
                results[full_key] = "created"
    
    db.commit()
    return results


@router.post("/settings/telegram", response_model=Dict[str, str])
async def save_telegram_settings(
    settings: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_system_admin)
):
    """Save Telegram settings (system admin only)."""
    results = {}
    
    for key, value in settings.items():
        if value is not None and value != "":
            full_key = f"telegram_{key}"
            
            # Check if config exists
            existing_config = db.query(SystemConfig).filter(SystemConfig.key == full_key).first()
            
            if existing_config:
                # Update existing config
                existing_config.value = str(value)
                results[full_key] = "updated"
            else:
                # Create new config
                is_sensitive = key == "bot_token"
                new_config = SystemConfig(
                    key=full_key,
                    value=str(value),
                    description=f"Telegram {key.replace('_', ' ').title()}",
                    is_sensitive=is_sensitive
                )
                db.add(new_config)
                results[full_key] = "created"
    
    db.commit()
    return results


@router.post("/settings/system", response_model=Dict[str, str])
async def save_system_settings(
    settings: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_system_admin)
):
    """Save system settings (system admin only)."""
    results = {}
    
    for key, value in settings.items():
        if value is not None and value != "":
            full_key = f"system_{key}"
            
            # Check if config exists
            existing_config = db.query(SystemConfig).filter(SystemConfig.key == full_key).first()
            
            if existing_config:
                # Update existing config
                existing_config.value = str(value)
                results[full_key] = "updated"
            else:
                # Create new config
                new_config = SystemConfig(
                    key=full_key,
                    value=str(value),
                    description=f"System {key.replace('_', ' ').title()}",
                    is_sensitive=False
                )
                db.add(new_config)
                results[full_key] = "created"
    
    db.commit()
    return results


@router.post("/settings/security", response_model=Dict[str, str])
async def save_security_settings(
    settings: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_system_admin)
):
    """Save security settings (system admin only)."""
    results = {}
    
    for key, value in settings.items():
        if value is not None and value != "":
            full_key = f"security_{key}"
            
            # Check if config exists
            existing_config = db.query(SystemConfig).filter(SystemConfig.key == full_key).first()
            
            if existing_config:
                # Update existing config
                existing_config.value = str(value)
                results[full_key] = "updated"
            else:
                # Create new config
                is_sensitive = key == "jwt_secret"
                new_config = SystemConfig(
                    key=full_key,
                    value=str(value),
                    description=f"Security {key.replace('_', ' ').title()}",
                    is_sensitive=is_sensitive
                )
                db.add(new_config)
                results[full_key] = "created"
    
    db.commit()
    return results
