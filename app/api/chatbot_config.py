"""Chatbot configuration API endpoints."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ChatbotConfig, User
from app.schemas.chatbot_config import ChatbotConfigCreate, ChatbotConfigUpdate, ChatbotConfigResponse
from app.dependencies import get_current_active_user_dependency, require_admin_or_system_admin_dependency

router = APIRouter(prefix="/chatbot-config", tags=["chatbot-config"])


@router.get("/", response_model=List[ChatbotConfigResponse])
async def get_chatbot_configs(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_system_admin_dependency)
):
    """Get list of chatbot configurations (admin and system admin only)."""
    configs = db.query(ChatbotConfig).offset(skip).limit(limit).all()
    return configs


@router.get("/active", response_model=ChatbotConfigResponse)
async def get_active_chatbot_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user_dependency)  # All authenticated users can see active config
):
    """Get active chatbot configuration (all authenticated users).

    Falls back to the most recently created configuration if none are active.
    """
    # Prefer explicitly active configuration
    config = db.query(ChatbotConfig).filter(ChatbotConfig.is_active == True).first()
    if config is None:
        # Fallback to latest configuration if none is marked active
        config = (
            db.query(ChatbotConfig)
            .order_by(ChatbotConfig.created_at.desc())
            .first()
        )

    if config is None:
        raise HTTPException(status_code=404, detail="No chatbot configuration found")

    return config


@router.get("/{config_id}", response_model=ChatbotConfigResponse)
async def get_chatbot_config(
    config_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_system_admin_dependency)
):
    """Get chatbot configuration by ID (admin and system admin only)."""
    config = db.query(ChatbotConfig).filter(ChatbotConfig.id == config_id).first()
    if config is None:
        raise HTTPException(status_code=404, detail="Chatbot configuration not found")
    return config


@router.post("/", response_model=ChatbotConfigResponse)
async def create_chatbot_config(
    config_data: ChatbotConfigCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_system_admin_dependency)
):
    """Upsert chatbot configuration (admin and system admin only).

    If an active configuration exists, update it in-place with the provided values.
    Otherwise, create a new configuration and mark it active.
    """
    from sqlalchemy.exc import IntegrityError
    from fastapi import HTTPException

    # Try to find the currently active configuration
    active_config = (
        db.query(ChatbotConfig).filter(ChatbotConfig.is_active == True).first()
    )

    if active_config:
        # Update existing active configuration with incoming data
        update_data = config_data.model_dump()
        # Ensure the active flag remains true and we don't accidentally toggle it
        update_data.pop("is_active", None)

        for field, value in update_data.items():
            setattr(active_config, field, value)
        active_config.is_active = True

        db.commit()
        db.refresh(active_config)
        return active_config

    # No active configuration; create a new one and mark it active
    config_dict = config_data.model_dump()
    config_dict["is_active"] = True

    db_config = ChatbotConfig(**config_dict)

    try:
        db.add(db_config)
        db.commit()
        db.refresh(db_config)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Failed to create config due to constraint violation")

    return db_config


@router.post("/new", response_model=ChatbotConfigResponse)
async def create_new_chatbot_config(
    config_data: ChatbotConfigCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_system_admin_dependency),
):
    """Create a new chatbot configuration (admin/system admin only).

    - Creates a brand new row with provided values.
    - If `is_active=True` is provided, deactivates all other configs.
    - Returns the newly created configuration.
    """
    from sqlalchemy.exc import IntegrityError

    payload = config_data.model_dump()
    # If requested active, deactivate others first
    if payload.get("is_active"):
        db.query(ChatbotConfig).update({"is_active": False})

    new_config = ChatbotConfig(**payload)
    try:
        db.add(new_config)
        db.commit()
        db.refresh(new_config)
        return new_config
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to create config: {exc.__class__.__name__}")


@router.post("/{config_id}/clone", response_model=ChatbotConfigResponse)
async def clone_chatbot_config(
    config_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_system_admin_dependency),
):
    """Clone an existing chatbot configuration (admin/system admin only).

    Duplicates all fields except identifiers and timestamps. The clone is created
    as inactive and with a unique name.
    """
    from datetime import datetime
    from sqlalchemy.exc import IntegrityError

    source = db.query(ChatbotConfig).filter(ChatbotConfig.id == config_id).first()
    if source is None:
        raise HTTPException(status_code=404, detail="Chatbot configuration not found")

    # Generate a safe unique name
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M")
    base_name = f"{source.name} - copy - {timestamp}"

    clone = ChatbotConfig(
        name=base_name,
        chatbot_name=source.chatbot_name,
        welcome_message=source.welcome_message,
        business_context=source.business_context,
        language=source.language,
        force_language=source.force_language,
        is_active=False,
        company_name=source.company_name,
        specializations=source.specializations,
        friendly_tone=source.friendly_tone,
        professional_style=source.professional_style,
        suggestive_responses=source.suggestive_responses,
        manager_handover=source.manager_handover,
        fallback_message=source.fallback_message,
        handover_message=source.handover_message,
        response_timeout=source.response_timeout,
        conversation_logging=source.conversation_logging,
        performance_analytics=source.performance_analytics,
        error_reporting=source.error_reporting,
        language_instruction=source.language_instruction,
        persona_instruction=source.persona_instruction,
        system_instruction=source.system_instruction,
        order_flow_block=source.order_flow_block,
        other_instruction=source.other_instruction,
    )

    try:
        db.add(clone)
        db.commit()
        db.refresh(clone)
        return clone
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to clone config: {exc.__class__.__name__}")


@router.put("/{config_id}", response_model=ChatbotConfigResponse)
async def update_chatbot_config(
    config_id: int,
    config_data: ChatbotConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_system_admin_dependency)
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
    current_user: User = Depends(require_admin_or_system_admin_dependency)
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
