"""
Authentication endpoints for user management and authentication.
"""
from datetime import timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer

from ..auth.models import (
    UserCreate, UserResponse, UserLogin, Token, UserUpdate,
    APIKeyCreate, ChangePassword, PasswordReset
)
from ..auth.dependencies import (
    get_current_active_user, require_admin, get_auth_repository,
    rate_limit_general
)
from ..auth.security import (
    create_token_response, generate_api_key, hash_api_key,
    validate_password_strength
)
from ..repositories.auth_repository import AuthRepository


router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()


@router.post("/register", response_model=UserResponse)
async def register_user(
    user_data: UserCreate,
    auth_repo: AuthRepository = Depends(get_auth_repository)
):
    """Register a new user."""
    # Validate password strength
    if not validate_password_strength(user_data.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters with uppercase, lowercase, digit, and special character"
        )

    # Create user
    user = auth_repo.create_user(
        username=user_data.username,
        email=user_data.email,
        password=user_data.password,
        full_name=user_data.full_name,
        role=user_data.role
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered"
        )

    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        status=user.status,
        created_at=user.created_at,
        last_login=user.last_login
    )


@router.post("/login", response_model=Token)
async def login_user(
    login_data: UserLogin,
    auth_repo: AuthRepository = Depends(get_auth_repository)
):
    """Authenticate user and return access token."""
    user = auth_repo.authenticate_user(login_data.username, login_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is inactive"
        )

    # Create token response
    token_data = create_token_response({
        "username": user.username,
        "id": user.id,
        "role": user.role.value
    })

    return Token(**token_data)


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str,
    auth_repo: AuthRepository = Depends(get_auth_repository)
):
    """Refresh access token using refresh token."""
    from ..auth.security import verify_token

    try:
        # Verify refresh token
        payload = verify_token(refresh_token, token_type="refresh")
        username = payload.get("sub")
        user_id = payload.get("user_id")

        # Get user
        user = auth_repo.get_user_by_username(username)
        if not user or user.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )

        # Create new tokens
        token_data = create_token_response({
            "username": user.username,
            "id": user.id,
            "role": user.role.value
        })

        return Token(**token_data)

    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user = Depends(get_current_active_user)
):
    """Get current user information."""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        status=current_user.status,
        created_at=current_user.created_at,
        last_login=current_user.last_login
    )


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user = Depends(get_current_active_user),
    auth_repo: AuthRepository = Depends(get_auth_repository)
):
    """Update current user information."""
    # Users can only update their own email and full_name
    # Admins can update role and status
    update_data = {}

    if user_update.email is not None:
        update_data["email"] = user_update.email
    if user_update.full_name is not None:
        update_data["full_name"] = user_update.full_name

    # Only admins can change role and status
    if current_user.role == "admin":
        if user_update.role is not None:
            update_data["role"] = user_update.role
        if user_update.status is not None:
            update_data["status"] = user_update.status

    updated_user = auth_repo.update_user(current_user.id, **update_data)

    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update user"
        )

    return UserResponse(
        id=updated_user.id,
        username=updated_user.username,
        email=updated_user.email,
        full_name=updated_user.full_name,
        role=updated_user.role,
        status=updated_user.status,
        created_at=updated_user.created_at,
        last_login=updated_user.last_login
    )


@router.post("/change-password")
async def change_password(
    password_data: ChangePassword,
    current_user = Depends(get_current_active_user),
    auth_repo: AuthRepository = Depends(get_auth_repository)
):
    """Change user password."""
    # Verify current password
    user = auth_repo.authenticate_user(current_user.username, password_data.current_password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    # Validate new password strength
    if not validate_password_strength(password_data.new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters with uppercase, lowercase, digit, and special character"
        )

    # Update password
    success = auth_repo.change_password(current_user.id, password_data.new_password)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password"
        )

    return {"message": "Password changed successfully"}


@router.post("/api-key")
async def create_api_key(
    current_user = Depends(get_current_active_user),
    auth_repo: AuthRepository = Depends(get_auth_repository)
):
    """Create API key for current user."""
    # Generate API key
    api_key = generate_api_key()
    api_key_hash = hash_api_key(api_key)

    # Store hashed API key
    success = auth_repo.set_api_key(current_user.id, api_key_hash)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create API key"
        )

    return {
        "api_key": api_key,
        "message": "API key created successfully. Store it securely - it won't be shown again."
    }


@router.delete("/api-key")
async def revoke_api_key(
    current_user = Depends(get_current_active_user),
    auth_repo: AuthRepository = Depends(get_auth_repository)
):
    """Revoke current user's API key."""
    success = auth_repo.revoke_api_key(current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke API key"
        )

    return {"message": "API key revoked successfully"}


# Admin endpoints
@router.get("/users", response_model=List[UserResponse])
async def get_all_users(
    skip: int = 0,
    limit: int = 100,
    current_user = Depends(require_admin),
    auth_repo: AuthRepository = Depends(get_auth_repository)
):
    """Get all users (admin only)."""
    users = auth_repo.get_all_users(skip=skip, limit=limit)
    return [
        UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            status=user.status,
            created_at=user.created_at,
            last_login=user.last_login
        )
        for user in users
    ]


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: int,
    current_user = Depends(require_admin),
    auth_repo: AuthRepository = Depends(get_auth_repository)
):
    """Get user by ID (admin only)."""
    user = auth_repo.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        status=user.status,
        created_at=user.created_at,
        last_login=user.last_login
    )


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user_by_id(
    user_id: int,
    user_update: UserUpdate,
    current_user = Depends(require_admin),
    auth_repo: AuthRepository = Depends(get_auth_repository)
):
    """Update user by ID (admin only)."""
    # Check if user exists
    user = auth_repo.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Update user
    update_data = user_update.dict(exclude_unset=True)
    updated_user = auth_repo.update_user(user_id, **update_data)

    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update user"
        )

    return UserResponse(
        id=updated_user.id,
        username=updated_user.username,
        email=updated_user.email,
        full_name=updated_user.full_name,
        role=updated_user.role,
        status=updated_user.status,
        created_at=updated_user.created_at,
        last_login=updated_user.last_login
    )


@router.delete("/users/{user_id}")
async def delete_user_by_id(
    user_id: int,
    current_user = Depends(require_admin),
    auth_repo: AuthRepository = Depends(get_auth_repository)
):
    """Delete user by ID (admin only)."""
    # Check if user exists
    user = auth_repo.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Prevent self-deletion
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )

    success = auth_repo.delete_user(user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user"
        )

    return {"message": "User deleted successfully"}