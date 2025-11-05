"""Shared dependency functions for FastAPI endpoints."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.services.auth_service import AuthService
from app.services.role_service import RoleService

# Initialize services
auth_service = AuthService()
role_service = RoleService()


async def get_current_user_dependency(
    token: str = Depends(auth_service.oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    """Dependency function for getting current user."""
    return await auth_service.get_current_user(token, db)


async def get_current_active_user_dependency(
    current_user: User = Depends(get_current_user_dependency),
) -> User:
    """Dependency function for getting current active user."""
    return await auth_service.get_current_active_user(current_user)


def require_admin_or_system_admin_dependency(
    current_user: User = Depends(get_current_active_user_dependency),
) -> User:
    """Dependency to require admin or system admin role."""
    return role_service.require_admin_or_system_admin(current_user)


def require_system_admin_dependency(
    current_user: User = Depends(get_current_active_user_dependency),
) -> User:
    """Dependency to require system admin role."""
    return role_service.require_system_admin(current_user)


def require_manager_or_higher_dependency(
    current_user: User = Depends(get_current_active_user_dependency),
) -> User:
    """Dependency to require manager, admin, or system admin role."""
    return role_service.require_manager_or_higher(current_user)
