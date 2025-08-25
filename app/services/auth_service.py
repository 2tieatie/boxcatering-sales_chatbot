import jwt

from datetime import datetime, timedelta, timezone
from typing import Optional, Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User
from app.schemas import TokenData, UserInDB, UserBase


# class Token(BaseModel):
#     access_token: str
#     token_type: str

# class TokenData(BaseModel):
#     username: str | None = None


# class User(BaseModel):
#     username: str
#     email: str | None = None
#     full_name: str | None = None
#     disabled: bool | None = None


# class UserInDB(User):
#     hashed_password: str


class AuthService:
    """Authentication service for user management and JWT handling."""
    
    oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
    
    def __init__(self):
        self.secret_key = settings.secret_key
        self.algorithm = settings.algorithm
        self.access_token_expire_minutes = settings.access_token_expire_minutes
        # self.oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
        # Use sha256_crypt as primary, with bcrypt as fallback for compatibility
        # self.pwd_context = CryptContext(schemes=["sha256_crypt", "bcrypt"], deprecated="auto")
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""

        return self.pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """Generate password hash."""

        return self.pwd_context.hash(password)
    
    # def get_user(self, db, username: str):
    #     if username in db:
    #         user_dict = db[username]
    #         return UserInDB(**user_dict)
    
    def authenticate_user(self, db: Session, username: str, password: str) -> Optional[UserBase]:
        """Authenticate user with username and password."""

        user = db.query(User).filter(User.username == username).first()
        if not user or not self.verify_password(password, user.hashed_password):
            return None

        # user = self.get_user(db, username=username)
        # if not user:
        #     return None
        # if not self.verify_password(password, user.hashed_password):
        #     return None
        
        return user
    
    def create_access_token(self, data: dict, expires_delta: timedelta | None = None) -> str:
        """Create JWT access token."""

        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=self.access_token_expire_minutes)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

        return encoded_jwt
    
    async def get_current_user(self, token: Annotated[str, Depends(oauth2_scheme)], db: Session = Depends(get_db)) -> UserBase:
        """Get current authenticated user from JWT token."""

        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            username = payload.get("sub")
            if username is None:
                raise credentials_exception
            token_data = TokenData(username=username)
        except InvalidTokenError:
            raise credentials_exception
        
        user = db.query(User).filter(User.username == token_data.username).first()
        # user = self.get_user(db, username=token_data.username)
        if user is None:
            raise credentials_exception
        return user
    
    async def get_current_active_user(self, current_user: User) -> User:
        """Get current active user."""

        if not current_user.is_active:
            raise HTTPException(status_code=400, detail="Inactive user")
        
        return current_user
