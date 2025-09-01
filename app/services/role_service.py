"""Role-based access control service."""

from typing import List
from fastapi import HTTPException, status
from app.models.user import User, UserRole


class RoleService:
    """Service for managing role-based access control."""
    
    @staticmethod
    def require_role(user: User, required_roles: List[str]) -> User:
        """Require user to have one of the specified roles."""
        if user.role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(required_roles)}"
            )
        return user
    
    @staticmethod
    def require_system_admin(user: User) -> User:
        """Require user to be a system administrator."""
        return RoleService.require_role(user, [UserRole.SYSTEM_ADMIN])
    
    @staticmethod
    def require_admin_or_system_admin(user: User) -> User:
        """Require user to be an admin or system administrator."""
        return RoleService.require_role(user, [UserRole.ADMIN, UserRole.SYSTEM_ADMIN])
    
    @staticmethod
    def require_manager_or_higher(user: User) -> User:
        """Require user to be a manager, admin, or system administrator."""
        return RoleService.require_role(user, [UserRole.MANAGER, UserRole.ADMIN, UserRole.SYSTEM_ADMIN])
    
    @staticmethod
    def can_manage_user(current_user: User, target_user: User) -> bool:
        """Check if current user can manage target user."""
        # System admins can manage anyone
        if current_user.role == UserRole.SYSTEM_ADMIN:
            return True
        
        # Admins can manage managers and other admins, but not system admins
        if current_user.role == UserRole.ADMIN:
            return target_user.role != UserRole.SYSTEM_ADMIN
        
        # Managers cannot manage other users
        return False
    
    @staticmethod
    def can_create_role(current_user: User, new_role: UserRole) -> bool:
        """Check if current user can create a user with the specified role."""
        # System admins can create any role
        if current_user.role == UserRole.SYSTEM_ADMIN:
            return True
        
        # Admins can create managers and other admins, but not system admins
        if current_user.role == UserRole.ADMIN:
            return new_role != UserRole.SYSTEM_ADMIN
        
        # Managers cannot create users
        return False
    
    @staticmethod
    def get_role_hierarchy() -> dict:
        """Get the role hierarchy for reference."""
        return {
            UserRole.SYSTEM_ADMIN: {
                "level": 3,
                "can_manage": [UserRole.SYSTEM_ADMIN, UserRole.ADMIN, UserRole.MANAGER],
                "description": "Full system access, can manage all users and system configurations"
            },
            UserRole.ADMIN: {
                "level": 2,
                "can_manage": [UserRole.ADMIN, UserRole.MANAGER],
                "description": "User management and chatbot configuration, cannot manage system admins"
            },
            UserRole.MANAGER: {
                "level": 1,
                "can_manage": [],
                "description": "View conversations and orders, can mark orders as processed"
            }
        }
