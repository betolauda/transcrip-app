"""
Authentication dependencies for FastAPI endpoints.
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from sqlalchemy.orm import Session

from .models import TokenData, UserRole, User
from .security import verify_token, verify_api_key, hash_api_key
from ..repositories.auth_repository import AuthRepository


# Security schemes
security = HTTPBearer()
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_auth_repository() -> AuthRepository:
    """Get authentication repository instance."""
    return AuthRepository()


async def get_current_user_from_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_repo: AuthRepository = Depends(get_auth_repository)
) -> User:
    """Get current user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Verify token
        payload = verify_token(credentials.credentials)
        username: str = payload.get("sub")
        user_id: int = payload.get("user_id")

        if username is None or user_id is None:
            raise credentials_exception

        token_data = TokenData(username=username, user_id=user_id)

    except HTTPException:
        raise credentials_exception

    # Get user from database
    user = auth_repo.get_user_by_username(token_data.username)
    if user is None:
        raise credentials_exception

    # Check if user is active
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive"
        )

    return user


async def get_current_user_from_api_key(
    api_key: Optional[str] = Depends(api_key_header),
    auth_repo: AuthRepository = Depends(get_auth_repository)
) -> Optional[User]:
    """Get current user from API key."""
    if not api_key:
        return None

    # Hash the provided API key
    hashed_key = hash_api_key(api_key)

    # Get user by API key
    user = auth_repo.get_user_by_api_key(hashed_key)
    if not user:
        return None

    # Check if user is active
    if user.status != "active":
        return None

    # Update last API key usage
    auth_repo.update_api_key_usage(user.id)

    return user


async def get_current_user(
    token_user: Optional[User] = Depends(get_current_user_from_token),
    api_key_user: Optional[User] = Depends(get_current_user_from_api_key)
) -> User:
    """Get current user from either JWT token or API key."""
    user = token_user or api_key_user

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user."""
    if current_user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


def require_role(required_role: UserRole):
    """Dependency factory for role-based access control."""
    def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role == UserRole.ADMIN:
            # Admins can access everything
            return current_user

        if current_user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires {required_role.value} role"
            )
        return current_user

    return role_checker


def require_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """Require admin role."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


def require_user_or_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """Require user or admin role (exclude guests)."""
    if current_user.role == UserRole.GUEST:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account required"
        )
    return current_user


class RateLimiter:
    """Simple rate limiter for API endpoints."""
    def __init__(self, max_requests: int = 100, window_minutes: int = 60):
        self.max_requests = max_requests
        self.window_minutes = window_minutes
        self.requests = {}

    def is_allowed(self, identifier: str) -> bool:
        """Check if request is allowed for the identifier."""
        import time
        now = time.time()
        window_start = now - (self.window_minutes * 60)

        # Clean old entries
        self.requests = {
            k: v for k, v in self.requests.items()
            if v > window_start
        }

        # Count current requests
        user_requests = [
            timestamp for timestamp in self.requests.values()
            if timestamp > window_start
        ]

        if len(user_requests) >= self.max_requests:
            return False

        # Add current request
        self.requests[f"{identifier}_{now}"] = now
        return True


# Rate limiter instances
general_limiter = RateLimiter(max_requests=100, window_minutes=60)
upload_limiter = RateLimiter(max_requests=10, window_minutes=60)


def rate_limit_general(current_user: User = Depends(get_current_user)):
    """General rate limiting dependency."""
    if not general_limiter.is_allowed(f"user_{current_user.id}"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Try again later."
        )
    return current_user


def rate_limit_upload(current_user: User = Depends(get_current_user)):
    """Upload-specific rate limiting dependency."""
    if not upload_limiter.is_allowed(f"upload_{current_user.id}"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Upload rate limit exceeded. Try again later."
        )
    return current_user