"""Admin endpoints to query prompt logs."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.models.prompt_log import PromptLog
from app.dependencies import require_admin_or_system_admin_dependency
from app.schemas.backend_log import BackendLogResponse


router = APIRouter(prefix="/logs", tags=["logs"])

@router.get("/prompts", response_model=List[dict])
async def list_prompt_logs(
    conversation_id: Optional[int] = None,
    config_id: Optional[int] = None,
    correlation_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_system_admin_dependency),
):
    """List prompt logs with optional filters (admin/system admin only)."""
    q = db.query(PromptLog).order_by(PromptLog.created_at.desc())
    if conversation_id is not None:
        q = q.filter(PromptLog.conversation_id == conversation_id)
    if config_id is not None:
        q = q.filter(PromptLog.config_id == config_id)
    if correlation_id:
        q = q.filter(PromptLog.correlation_id == correlation_id)
    rows = q.offset(skip).limit(limit).all()
    return [
        {
            "id": r.id,
            "created_at": r.created_at,
            "user_id": r.user_id,
            "conversation_id": r.conversation_id,
            "config_id": r.config_id,
            "model": r.model,
            "system_prompt_hash": r.system_prompt_hash,
            "system_prompt_length": r.system_prompt_length,
            "duration_ms": r.duration_ms,
            "error": r.error,
        }
        for r in rows
    ]


@router.get("/prompts/{log_id}", response_model=dict)
async def get_prompt_log(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_system_admin_dependency),
):
    """Get a single prompt log by id (admin/system admin only)."""
    row = db.query(PromptLog).filter(PromptLog.id == log_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Prompt log not found")
    return {
        "id": row.id,
        "created_at": row.created_at,
        "user_id": row.user_id,
        "conversation_id": row.conversation_id,
        "config_id": row.config_id,
        "model": row.model,
        "system_prompt_hash": row.system_prompt_hash,
        "system_prompt_preview": row.system_prompt_preview,
        "system_prompt_length": row.system_prompt_length,
        "prompt_trace_json": row.prompt_trace_json,
        "user_message": row.user_message,
        "request_json": row.request_json,
        "response_json": row.response_json,
        "duration_ms": row.duration_ms,
        "error": row.error,
    }

from collections import deque

@router.get("/back", response_model=List[BackendLogResponse])
async def get_backend_logs(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_system_admin_dependency)
):
    """Get last N lines of logs (admin and system admin only)."""

    with open('logs/prompt.log', 'r') as log_file:
        # Efficiently get the last `limit` lines
        logs = list(deque((line.strip() for line in log_file), maxlen=limit))

    return logs
