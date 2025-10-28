"""Backend log API endpoints."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, BackendLog
from app.schemas.backend_log import BackendLogCreate, BackendLogResponse
from app.dependencies import require_admin_or_system_admin_dependency

router = APIRouter(prefix="/backend-log", tags=["backend-log"])


@router.get("/", response_model=List[BackendLogResponse])
async def get_backebd_logs(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_system_admin_dependency)
):
    """Get list of logs (admin and system admin only)."""

    with open('logs/app.log', 'r') as log_file:
        logs = log_file.readlines()
        # for line in log_file:
            # print(line.strip())



    # logs = db.query(BackendLog).offset(skip).limit(limit).all()
    return logs


@router.get("/{config_id}", response_model=BackendLogResponse)
async def get_backebd_log(
    config_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_system_admin_dependency)
):
    """Get backend log by ID (admin and system admin only)."""
    log = db.query(BackendLog).filter(BackendLog.config_id == config_id).first()
    if log is None:
        raise HTTPException(status_code=404, detail="Backend log by config ID not found")
    return log


@router.post("/", response_model=BackendLogResponse)
async def create_backebd_log(
    log_data: BackendLogCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_system_admin_dependency)
):
    """Upsert backend log (admin and system admin only)."""
    from sqlalchemy.exc import IntegrityError
    from fastapi import HTTPException

    log_dict = log_data.model_dump()

    db_log = BackendLog(**log_dict)

    try:
        db.add(db_log)
        db.commit()
        db.refresh(db_log)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Failed to create backend log due to constraint violation")

    return db_log
