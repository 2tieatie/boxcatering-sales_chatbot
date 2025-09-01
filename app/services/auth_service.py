"""Authentication service."""
from datetime import datetime, timedelta
from typing import Optional
from app.config import settings
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.schemas import Token


class AuthService:
    """Authentication service for user management and JWT handling."""
    
    def __init__(self):
        self.secret_key = settings.secret_key
        self.algorithm = settings.algorithm
        self.access_token_expire_minutes = settings.access_token_expire_minutes
        self.oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
        # Use sha256_crypt as primary, with bcrypt as fallback for compatibility
        self.pwd_context = CryptContext(schemes=["sha256_crypt", "bcrypt"], deprecated="auto")
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """Generate password hash."""
        return self.pwd_context.hash(password)
    
    def authenticate_user(self, db: Session, username: str, password: str) -> Optional[User]:
        """Authenticate user with username and password."""
        user = db.query(User).filter(User.username == username).first()
        if not user or not self.verify_password(password, user.hashed_password):
            return None
        return user
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def get_current_user(self, token: str = Depends(OAuth2PasswordBearer(tokenUrl="auth/login")), db: Session = Depends(get_db)) -> User:
        """Get current authenticated user from JWT token."""
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            username: str = payload.get("sub")
            if username is None:
                raise credentials_exception
        except JWTError:
            raise credentials_exception
        
        user = db.query(User).filter(User.username == username).first()
        if user is None:
            raise credentials_exception
        return user
    
    def get_current_active_user(self, current_user: User = Depends(get_current_user)) -> User:
        """Get current active user."""
        if not current_user.is_active:
            raise HTTPException(status_code=400, detail="Inactive user")
        return current_user
