"""System configuration API endpoints."""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from loguru import logger
from openai import OpenAI
from telegram import Bot

from app.database import get_db
from app.models import SystemConfig, User
from app.schemas.system_config import SystemConfigCreate, SystemConfigUpdate, SystemConfigResponse
from app.dependencies import require_system_admin_dependency
from app.config import settings

router = APIRouter(prefix="/system-config", tags=["system-config"])


@router.get("/", response_model=List[SystemConfigResponse])
async def get_system_configs(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_system_admin_dependency)
):
    """Get all system configurations (system admin only)."""
    configs = db.query(SystemConfig).offset(skip).limit(limit).all()
    return configs


@router.get("/{config_id}", response_model=SystemConfigResponse)
async def get_system_config(
    config_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_system_admin_dependency)
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
    current_user: User = Depends(require_system_admin_dependency)
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
    current_user: User = Depends(require_system_admin_dependency)
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
    current_user: User = Depends(require_system_admin_dependency)
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
    current_user: User = Depends(require_system_admin_dependency)
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
    current_user: User = Depends(require_system_admin_dependency)
):
    """Get all settings organized by category (system admin only)."""
    configs = db.query(SystemConfig).all()
    
    # Organize settings by category
    settings = {
        "openai": {},
        "telegram": {},
        "widget": {},
        "system": {},
        "security": {}
    }
    
    for config in configs:
        if config.key.startswith("openai_"):
            settings["openai"][config.key.replace("openai_", "")] = config.value
        elif config.key.startswith("telegram_"):
            settings["telegram"][config.key.replace("telegram_", "")] = config.value
        elif config.key.startswith("widget_"):
            settings["widget"][config.key.replace("widget_", "")] = config.value
        elif config.key.startswith("system_"):
            settings["system"][config.key.replace("system_", "")] = config.value
        elif config.key.startswith("security_"):
            settings["security"][config.key.replace("security_", "")] = config.value
    
    return settings

@router.get("/settings/widget", response_model=Dict[str, Any])
async def get_all_widget_settings(
    db: Session = Depends(get_db),
):
    """Get all widget settings."""
    configs = db.query(SystemConfig).all()
    
    # Organize settings by category
    settings = {
        "widget": {},
    }
    
    for config in configs:
        if config.key.startswith("widget_"):
            settings["widget"][config.key.replace("widget_", "")] = config.value
    
    return settings

@router.post("/settings/bulk", response_model=Dict[str, str])
async def save_bulk_settings(
    settings: Dict[str, Dict[str, Any]],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_system_admin_dependency)
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
    current_user: User = Depends(require_system_admin_dependency)
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
    current_user: User = Depends(require_system_admin_dependency)
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
    current_user: User = Depends(require_system_admin_dependency)
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


@router.post("/settings/widget", response_model=Dict[str, str])
async def save_system_settings(
    settings: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_system_admin_dependency)
):
    """Save widget settings (system admin only)."""
    results = {}
    
    for key, value in settings.items():
        if value is not None and value != "":
            full_key = f"widget_{key}"
            
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


@router.post("/settings/openai/test", response_model=Dict[str, Any])
async def test_openai_settings(
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_system_admin_dependency),
) -> Dict[str, Any]:
    """Validate OpenAI API connectivity with a tiny completion.

    Priority for configuration values:
    1) value provided in request payload
    2) value stored in `system_configs` table
    3) application settings from environment
    """
    def _get_cfg(key: str, default: str | None = None) -> str | None:
        cfg = db.query(SystemConfig).filter(SystemConfig.key == key).first()
        return (cfg.value if cfg else default)

    try:
        api_key: str | None = payload.get("api_key") or _get_cfg("openai_api_key", settings.openai_api_key)
        model: str | None = payload.get("model") or _get_cfg("openai_model", settings.openai_model)

        # Optional parameters with safe tiny defaults
        try:
            temperature_raw = payload.get("temperature")
            temperature: float | None = float(temperature_raw) if temperature_raw is not None else None
        except Exception:
            temperature = None

        try:
            max_tokens_raw = payload.get("max_tokens")
            max_tokens: int = int(max_tokens_raw) if max_tokens_raw is not None else 1
        except Exception:
            max_tokens = 1

        if not api_key:
            return {"success": False, "message": "Missing OpenAI API key"}
        if not model:
            return {"success": False, "message": "Missing OpenAI model"}

        client = OpenAI(api_key=api_key)

        def model_supports_temperature(model_name: str) -> bool:
            # Align with ChatbotService assumption: 'gpt-5' base doesn't support temperature
            return model_name != "gpt-5"

        def model_requires_max_completion_tokens(model_name: str) -> bool:
            # Align with ChatbotService assumption for GPT-5 family
            return model_name.startswith("gpt-5")

        request_kwargs: Dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": "Health check."},
                {"role": "user", "content": "ping"},
            ],
        }

        if model_supports_temperature(model) and temperature is not None:
            request_kwargs["temperature"] = temperature

        # Use a minimal token budget to avoid unnecessary costs
        if model_requires_max_completion_tokens(model):
            request_kwargs["max_completion_tokens"] = max_tokens or 1
        else:
            request_kwargs["max_tokens"] = max_tokens or 1

        # Perform the actual test call
        resp = client.chat.completions.create(**request_kwargs)

        return {
            "success": True,
            "message": "OpenAI connection successful",
            "model": model,
            "id": getattr(resp, "id", None),
        }
    except Exception as e:
        logger.error(f"OpenAI test failed: {e}")
        # Return a non-exception response so UI can display error nicely
        return {"success": False, "message": str(e)}


@router.post("/settings/telegram/test", response_model=Dict[str, Any])
async def test_telegram_settings(
    payload: Dict[str, Any],
    current_user: User = Depends(require_system_admin_dependency),
) -> Dict[str, Any]:
    """Validate Telegram bot token and optionally chat permissions.

    - Verifies the bot token using `get_me()`.
    - If `chat_id` is provided, attempts to send a lightweight test message.
    """
    bot_token = (payload or {}).get("bot_token")
    chat_id = (payload or {}).get("chat_id")

    if not bot_token:
        return {"success": False, "message": "Missing Telegram bot token"}

    try:
        bot = Bot(token=bot_token)
        me = await bot.get_me()
        result: Dict[str, Any] = {
            "success": True,
            "message": "Telegram bot token is valid",
            "bot_id": getattr(me, "id", None),
            "bot_username": getattr(me, "username", None),
            "sent": False,
        }

        # Optionally test sending a message if chat_id provided
        if chat_id:
            try:
                msg = await bot.send_message(
                    chat_id=str(chat_id),
                    text="✅ Telegram credentials test successful.",
                )
                result["sent"] = True
                result["message"] = "Telegram bot token is valid and message sent"
                result["message_id"] = getattr(msg, "message_id", None)
            except Exception as send_err:
                # If sending fails, still return token validity with explanation
                logger.warning(f"Telegram test send failed: {send_err}")
                result["sent"] = False
                result["send_error"] = str(send_err)

        return result
    except Exception as e:
        logger.error(f"Telegram test failed: {e}")
        return {"success": False, "message": str(e)}


@router.post("/settings/security", response_model=Dict[str, str])
async def save_security_settings(
    settings: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_system_admin_dependency)
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
