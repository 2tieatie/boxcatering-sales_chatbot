"""Health check endpoint."""

import time
from fastapi import APIRouter

router = APIRouter(tags=["health"])

start_time = time.time()


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    uptime = time.time() - start_time
    return {
        "status": "ok",
        "uptime": f"{uptime:.2f}s"
    }
