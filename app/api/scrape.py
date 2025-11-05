"""Scraper control and status endpoints."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends

from app.dependencies import require_manager_or_higher_dependency
from app.models import User
from app.services.web_scraper_service import web_scraper


router = APIRouter(prefix="/scrape", tags=["scrape"])


@router.get("/status", response_model=Dict[str, Any])
async def get_status(
    current_user: User = Depends(require_manager_or_higher_dependency),
) -> Dict[str, Any]:
    s = web_scraper.status
    return {
        "running": web_scraper.is_running(),
        "last_run_utc": s.last_run_utc.isoformat() if s.last_run_utc else None,
        "last_error": s.last_error,
        "pages_scraped": s.pages_scraped,
        "url": s.url,
        "interval_minutes": s.interval_minutes,
    }


@router.post("/run", response_model=Dict[str, Any])
async def run_once(
    current_user: User = Depends(require_manager_or_higher_dependency),
) -> Dict[str, Any]:
    # Trigger an immediate scrape cycle
    return await web_scraper.scrape_once()
