"""
JWT Authentication utilities.
"""

import os
import hashlib
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

# Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
if not SECRET_KEY:
    import warnings
    SECRET_KEY = "dev-only-insecure-key-change-in-production"
    warnings.warn(
        "JWT_SECRET_KEY not set — using insecure default. "
        "Set it in production: python -c \"import secrets; print(secrets.token_urlsafe(64))\"",
        stacklevel=2,
    )
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# Password hashing
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


class Token(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Data encoded in JWT."""
    username: Optional[str] = None
    user_id: Optional[int] = None


class UserCreate(BaseModel):
    """User registration request."""
    username: str
    email: str
    password: str


class UserLogin(BaseModel):
    """User login request."""
    username: str
    password: str


class UserResponse(BaseModel):
    """User info response."""
    id: int
    username: str
    email: str
    created_at: datetime
    
    class Config:
        from_attributes = True


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash password."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[TokenData]:
    """Decode and validate JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        
        if username is None:
            return None
            
        return TokenData(username=username, user_id=user_id)
    except JWTError:
        return None
