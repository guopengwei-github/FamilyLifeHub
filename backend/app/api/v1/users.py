"""
API endpoints for user management.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.security import verify_api_key, hash_password
from app.models import User
from app.schemas import UserCreate, UserResponse

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user: UserCreate,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Create a new family member (legacy API key endpoint).

    This endpoint is for external data ingestion systems (Garmin, desktop client).
    For user self-registration, use /api/v1/auth/register instead.

    Requires X-API-Key header for authentication.

    Note: Users created via this endpoint will have a randomly generated password.
    They should use the password reset flow or recreate their account via auth/register.
    """
    import secrets
    import string

    # Check if user with same name already exists
    existing = db.query(User).filter(User.name == user.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with name '{user.name}' already exists"
        )

    # Generate a random email for legacy users
    random_suffix = ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(8))
    email = f"{user.name.lower().replace(' ', '.')}_{random_suffix}@localhost"

    # Generate a random password (user won't know it)
    random_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))

    new_user = User(
        name=user.name,
        email=email,
        hashed_password=hash_password(random_password),
        avatar=user.avatar,
        is_active=1
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.get("", response_model=List[UserResponse])
async def list_users(db: Session = Depends(get_db)):
    """
    List all family members.

    No authentication required for read-only endpoints.
    """
    users = db.query(User).all()
    return users


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: Session = Depends(get_db)):
    """
    Get a specific user by ID.

    No authentication required for read-only endpoints.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )
    return user
