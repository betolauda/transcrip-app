"""
Authentication models and schemas for user management.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from enum import Enum


class UserRole(str, Enum):
    """User roles with different access levels."""
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"


class UserStatus(str, Enum):
    """User account status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


# Database Models (for SQLAlchemy/SQLite)
class User:
    """User model for database storage."""
    def __init__(self, id: int, username: str, email: str, hashed_password: str,
                 full_name: str, role: UserRole, status: UserStatus,
                 created_at: datetime, last_login: Optional[datetime] = None,
                 api_key: Optional[str] = None):
        self.id = id
        self.username = username
        self.email = email
        self.hashed_password = hashed_password
        self.full_name = full_name
        self.role = role
        self.status = status
        self.created_at = created_at
        self.last_login = last_login
        self.api_key = api_key


# Pydantic Schemas for API
class UserBase(BaseModel):
    """Base user schema with common fields."""
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    email: EmailStr = Field(..., description="User email address")
    full_name: str = Field(..., min_length=1, max_length=100, description="User's full name")


class UserCreate(UserBase):
    """Schema for user creation."""
    password: str = Field(..., min_length=8, max_length=128, description="User password")
    role: UserRole = Field(default=UserRole.USER, description="User role")


class UserUpdate(BaseModel):
    """Schema for user updates."""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, min_length=1, max_length=100)
    role: Optional[UserRole] = None
    status: Optional[UserStatus] = None


class UserResponse(UserBase):
    """Schema for user response (without sensitive data)."""
    id: int
    role: UserRole
    status: UserStatus
    created_at: datetime
    last_login: Optional[datetime] = None


class UserLogin(BaseModel):
    """Schema for user login."""
    username: str = Field(..., description="Username or email")
    password: str = Field(..., description="User password")


class Token(BaseModel):
    """JWT token response schema."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: Optional[str] = None


class TokenData(BaseModel):
    """Token payload data."""
    username: Optional[str] = None
    user_id: Optional[int] = None
    role: Optional[UserRole] = None


class APIKey(BaseModel):
    """API key schema."""
    key: str
    name: str
    created_at: datetime
    last_used: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class APIKeyCreate(BaseModel):
    """Schema for creating API keys."""
    name: str = Field(..., min_length=1, max_length=100, description="API key name")
    expires_days: Optional[int] = Field(None, gt=0, le=365, description="Expiration in days")


class PasswordReset(BaseModel):
    """Schema for password reset request."""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Schema for password reset confirmation."""
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)


class ChangePassword(BaseModel):
    """Schema for password change."""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)