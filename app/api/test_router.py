"""Test router to isolate the self parameter issue."""

from fastapi import APIRouter, Depends, HTTPException
from app.dependencies import get_current_active_user_dependency

router = APIRouter(prefix="/test", tags=["test"])


@router.get("/")
async def test_endpoint():
    """Simple test endpoint."""
    return {"message": "Test endpoint working"}


@router.post("/")
async def test_post_endpoint():
    """Simple test POST endpoint."""
    return {"message": "Test POST endpoint working"}


@router.get("/auth")
async def test_auth_endpoint(current_user = Depends(get_current_active_user_dependency)):
    """Test endpoint with auth dependency."""
    return {"message": "Auth test endpoint working", "user": current_user.username}
