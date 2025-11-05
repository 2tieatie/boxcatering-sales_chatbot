"""Context documents management API endpoints.

Provides secure endpoints for managers and above to list, upload, and delete
files in the configured context documents directory. Supported file types:
PDF, TXT, MD, CSV, DOCX.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session
from loguru import logger

from app.database import get_db
from app.dependencies import require_manager_or_higher_dependency
from app.models import SystemConfig, User
from app.config import settings
from app.api.chat import chatbot_service  # reuse singleton to clear cache


router = APIRouter(prefix="/context-docs", tags=["context-docs"])


ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md", ".csv", ".docx"}


def _safe_join(base_dir: Path, filename: str) -> Path:
    """Safely join a filename to base_dir, preventing path traversal."""
    # Strip path separators and normalize
    sanitized = filename.replace("\\", "/").split("/")[-1]
    target = base_dir / sanitized
    if not str(target.resolve()).startswith(str(base_dir.resolve())):
        raise HTTPException(status_code=400, detail="Invalid file path")
    return target


def _get_effective_context_dir(db: Session) -> Path:
    """Return the effective context directory from DB or fallback settings.

    - system_context_docs_dir in DB overrides
    - falls back to settings.context_docs_dir
    - returns absolute path
    """
    try:
        cfg = (
            db.query(SystemConfig)
            .filter(SystemConfig.key == "system_context_docs_dir")
            .first()
        )
        dir_value = cfg.value if cfg and cfg.value else settings.context_docs_dir
    except Exception as e:
        logger.warning(f"Failed to read context dir from DB, using default: {e}")
        dir_value = settings.context_docs_dir

    base = Path(dir_value)
    if not base.is_absolute():
        base = Path.cwd() / base
    return base


@router.get("/list", response_model=Dict[str, Any])
async def list_context_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_higher_dependency),
) -> Dict[str, Any]:
    """List files in the context documents directory."""
    base = _get_effective_context_dir(db)
    if not base.exists():
        return {"dir": str(base), "files": []}

    files: List[Dict[str, Any]] = []
    for p in sorted(base.glob("*")):
        if not p.is_file():
            continue
        ext = p.suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            continue
        try:
            stat = p.stat()
            files.append(
                {
                    "name": p.name,
                    "size": stat.st_size,
                    "modified": int(stat.st_mtime),
                    "ext": ext,
                }
            )
        except Exception as e:
            logger.warning(f"Failed to stat file {p}: {e}")
    return {"dir": str(base), "files": files}


@router.post("/upload", response_model=Dict[str, Any])
async def upload_context_documents(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_higher_dependency),
) -> Dict[str, Any]:
    """Upload one or more context documents. Returns saved filenames."""
    base = _get_effective_context_dir(db)
    base.mkdir(parents=True, exist_ok=True)

    saved: List[str] = []
    skipped: List[Dict[str, str]] = []

    for uf in files:
        original_name = uf.filename or ""
        ext = Path(original_name).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            skipped.append({"name": original_name, "reason": "unsupported_extension"})
            continue

        try:
            target = _safe_join(base, original_name)
            # De-duplicate by appending numeric suffix if needed
            if target.exists():
                stem = target.stem
                suffix = target.suffix
                i = 1
                while True:
                    candidate = target.with_name(f"{stem} ({i}){suffix}")
                    if not candidate.exists():
                        target = candidate
                        break
                    i += 1

            content = await uf.read()
            target.write_bytes(content)
            saved.append(target.name)
            # Invalidate context cache so new content is used
            try:
                chatbot_service._context_docs_cache.clear()
            except Exception:
                pass
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to save uploaded file '{original_name}': {e}")
            skipped.append({"name": original_name, "reason": "save_failed"})

    return {"dir": str(base), "saved": saved, "skipped": skipped}


@router.delete("/{filename}", response_model=Dict[str, str])
async def delete_context_document(
    filename: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_higher_dependency),
) -> Dict[str, str]:
    """Delete a context document by filename."""
    base = _get_effective_context_dir(db)
    target = _safe_join(base, filename)
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    if target.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    try:
        target.unlink()
        # Clear chatbot context cache so new state is picked up on next request
        try:
            chatbot_service._context_docs_cache.clear()
        except Exception:
            pass
        return {"message": "Deleted"}
    except Exception as e:
        logger.error(f"Failed to delete file '{target}': {e}")
        raise HTTPException(status_code=500, detail="Failed to delete file")
