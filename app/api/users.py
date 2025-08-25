"""Users API endpoints."""

from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import UserCreate, UserUpdate, UserResponse, PasswordChange
from app.dependencies import get_current_active_user_dependency, role_service, auth_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=List[UserResponse])
async def get_users(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user_dependency)
):
    """Get list of users (admin and system admin only)."""
    # Check if current user is admin or system admin
    role_service.require_admin_or_system_admin(current_user)
    
    users = db.query(User).offset(skip).limit(limit).all()
    return users


@router.get("/me", response_model=UserResponse)
async def get_current_user(current_user: User = Depends(get_current_active_user_dependency)):
    """Get current user information."""

    return current_user


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user_dependency)
):
    """Get user by ID (admin, system admin, or self)."""
    # Check permissions - users can only see themselves unless they're admin/system_admin
    if current_user.id != user_id:
        role_service.require_admin_or_system_admin(current_user)
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/", response_model=UserResponse)
async def create_user(
    user_data: UserCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user_dependency)
):
    """Create new user (admin only)."""
    # Check if current user is admin
    role_service.require_admin_or_system_admin(current_user)
    
    # Role hierarchy enforcement
    if not role_service.can_create_role(current_user, user_data.role):
        raise HTTPException(
            status_code=403, 
            detail="You cannot create users with this role"
        )
    
    # Check if user already exists
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    existing_email = db.query(User).filter(User.email == user_data.email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user
    hashed_password = auth_service.get_password_hash(user_data.password)
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=hashed_password,
        role=user_data.role
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user_dependency)
):
    """Update user (admin or self)."""
    # Check permissions
    if current_user.id != user_id:
        role_service.require_admin_or_system_admin(current_user)
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Role hierarchy enforcement for role changes
    if "role" in user_data.model_dump(exclude_unset=True):
        new_role = user_data.role
        if not role_service.can_create_role(current_user, new_role):
            raise HTTPException(
                status_code=403, 
                detail="You cannot assign this role to users"
            )
        if not role_service.can_manage_user(current_user, user):
            raise HTTPException(
                status_code=403, 
                detail="You cannot modify this user"
            )
    
    # Update fields
    update_data = user_data.model_dump(exclude_unset=True)
    if "password" in update_data:
        update_data["hashed_password"] = auth_service.get_password_hash(update_data.pop("password"))
    
    for field, value in update_data.items():
        setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user_dependency)
):
    """Delete user (admin only)."""
    role_service.require_admin_or_system_admin(current_user)
    
    if current_user.id == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    user = db.query(User).filter(User.id == user_id).first()
    
    # Role hierarchy enforcement
    if not role_service.can_manage_user(current_user, user):
        raise HTTPException(
            status_code=403, 
            detail="You cannot delete this user"
        )
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.delete(user)
    db.commit()
    
    return {"message": "User deleted successfully"}


@router.put("/me/change-password")
async def change_password(
    password_data: PasswordChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user_dependency)
):
    """Change current user's password."""
    # Verify current password
    if not auth_service.verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    # Hash and update new password
    hashed_password = auth_service.get_password_hash(password_data.new_password)
    current_user.hashed_password = hashed_password
    
    db.commit()
    db.refresh(current_user)
    
    return {"message": "Password changed successfully"}
