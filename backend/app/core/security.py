"""
Security utilities for API authentication.
Implements API Key authentication for data ingestion and JWT authentication for user accounts.
"""
from fastapi import Security, HTTPException, status, Depends
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from sqlalchemy.orm import Session
import bcrypt
from jose import JWTError, jwt
from cryptography.fernet import Fernet
from datetime import datetime, timedelta
from typing import Optional, Annotated
import base64

from app.core.config import settings
from app.core.database import get_db
from app.models import User

# ============ Token Encryption ============

# Generate a Fernet key from the secret key for encrypting OAuth tokens
# Ensure the key is 32 bytes (url-safe base64 encoded)
def _get_fernet_key() -> bytes:
    """Generate Fernet key from secret_key."""
    # Use secret_key and pad/trim to 32 bytes
    key_bytes = settings.secret_key.encode('utf-8')[:32].ljust(32, b'\0')
    # URL-safe base64 encode to get Fernet-compatible key
    return base64.urlsafe_b64encode(key_bytes)

_fernet = Fernet(_get_fernet_key())


def encrypt_token(token: str) -> str:
    """
    Encrypt a token using Fernet symmetric encryption.

    Args:
        token: Plain text token to encrypt

    Returns:
        Encrypted token string (url-safe base64)
    """
    if not token:
        return ""
    encrypted = _fernet.encrypt(token.encode('utf-8'))
    return encrypted.decode('utf-8')


def decrypt_token(encrypted: str) -> Optional[str]:
    """
    Decrypt a token using Fernet symmetric encryption.

    Args:
        encrypted: Encrypted token string

    Returns:
        Plain text token, or None if decryption fails
    """
    if not encrypted:
        return None
    try:
        decrypted = _fernet.decrypt(encrypted.encode('utf-8'))
        return decrypted.decode('utf-8')
    except Exception:
        return None

# Define API Key header scheme (for data ingestion)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Define OAuth2 scheme for JWT (for user authentication)
# Use explicit URL for tokenUrl to ensure compatibility across FastAPI versions
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# ============ Password Utilities ============

def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Hashed password string
    """
    # Truncate to 72 bytes max for bcrypt
    password_bytes = password.encode('utf-8')[:72]
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password from database

    Returns:
        True if password matches, False otherwise
    """
    # Truncate to 72 bytes max for bcrypt
    password_bytes = plain_password.encode('utf-8')[:72]
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)


# ============ JWT Utilities ============

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: Payload data to encode (typically contains user_id)
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.algorithm
    )
    return encoded_jwt


def decode_access_token(token: str) -> Optional[int]:
    """
    Decode a JWT access token and extract user_id.

    Args:
        token: JWT token string

    Returns:
        User ID if token is valid, None otherwise
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )
        user_id = payload.get("sub")
        if user_id is None:
            return None
        return int(user_id)
    except JWTError:
        return None


# ============ Authentication Dependencies ============

def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)]
) -> User:
    """
    Get current authenticated user from JWT token.

    Args:
        token: JWT token from Authorization header
        db: Database session

    Returns:
        The authenticated User object

    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    user_id = decode_access_token(token)
    if user_id is None:
        raise credentials_exception
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user


def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """
    Get the current active user.

    Args:
        current_user: User from get_current_user

    Returns:
        The User object if active

    Raises:
        HTTPException: If user is not active
    """
    if current_user.is_active != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    return current_user


# ============ API Key Authentication ============

async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    Verify API key from request header.
    Used for data ingestion endpoints.

    Args:
        api_key: API key from X-API-Key header

    Returns:
        The validated API key

    Raises:
        HTTPException: If API key is missing or invalid
    """
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API Key in X-API-Key header"
        )

    if api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API Key"
        )

    return api_key
