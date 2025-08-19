"""
Authentication utilities for the CARLA Driving Simulator.
"""

import bcrypt
import jwt
import secrets
import string
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jwt import ExpiredSignatureError

# JWT Configuration (env-driven with secure defaults)
import os
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-insecure-change-me")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))

# Password configuration
PASSWORD_MIN_LENGTH = 8
PASSWORD_SALT_ROUNDS = 12

security = HTTPBearer()


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    is_admin: bool
    created_at: datetime
    last_login: Optional[datetime]


def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    salt = bcrypt.gensalt(PASSWORD_SALT_ROUNDS)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))


def generate_session_token() -> str:
    """Generate a secure session token"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(64))


def create_jwt_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def verify_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify and decode a JWT token, including expiration check"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except ExpiredSignatureError:
        # Token is expired
        return None
    except jwt.PyJWTError:
        return None


def validate_password(password: str) -> bool:
    """Validate password strength"""
    if len(password) < PASSWORD_MIN_LENGTH:
        return False
    
    # Check for at least one uppercase, one lowercase, one digit
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    
    return has_upper and has_lower and has_digit


def validate_email(email: str) -> bool:
    """Basic email validation"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_username(username: str) -> bool:
    """Validate username format"""
    if len(username) < 3 or len(username) > 50:
        return False
    
    # Username should only contain alphanumeric characters and underscores
    import re
    pattern = r'^[a-zA-Z0-9_]+$'
    return re.match(pattern, username) is not None


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Get current user from JWT token"""
    token = credentials.credentials
    payload = verify_jwt_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return payload


def require_admin(user: Dict[str, Any]) -> None:
    """Require admin privileges"""
    if not user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        ) 
