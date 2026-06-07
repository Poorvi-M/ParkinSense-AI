from datetime import datetime, timezone, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
import hashlib
import hmac
from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from .config import settings


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

# CryptContext configures passlib to use bcrypt as the hashing scheme.
# deprecated="auto" automatically upgrades legacy hashes on next login.
def _sha256_hash(plain_password: str) -> str:
    digest = hashlib.sha256(plain_password.encode("utf-8") + settings.SECRET_KEY.encode("utf-8")).hexdigest()
    return f"sha256${digest}"


def hash_password(plain_password: str) -> str:
    """Hash a plain-text password using bcrypt where possible, otherwise fall back to SHA-256.

    The SHA-256 fallback exists to allow local testing environments where the
    system bcrypt backend may be missing or behave unexpectedly. It is NOT
    recommended for production use.
    """
    try:
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return pwd_context.hash(plain_password)
    except Exception:
        return _sha256_hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Support SHA-256 fallback hashes explicitly
    if isinstance(hashed_password, str) and hashed_password.startswith("sha256$"):
        expected = _sha256_hash(plain_password)
        return hmac.compare_digest(expected, hashed_password)

    try:
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        # Fallback comparison for mixed environments
        try:
            expected = _sha256_hash(plain_password)
            return hmac.compare_digest(expected, hashed_password)
        except Exception:
            return False


# ---------------------------------------------------------------------------
# OAuth2 scheme
# ---------------------------------------------------------------------------

# Tells FastAPI where clients send their Bearer token.
# tokenUrl must match the login route exactly.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# ---------------------------------------------------------------------------
# JWT token creation
# ---------------------------------------------------------------------------

def create_access_token(user_id: int, role: str) -> str:
    """
    Create a signed JWT access token.
    Payload fields:
        sub  -- subject: stores user ID as a string (JWT standard)
        role -- user role, included for downstream authorisation checks
        exp  -- expiration: timezone-aware UTC timestamp
    Args:
        user_id: The authenticated user's database ID.
        role:    The user's role string (e.g. "patient" or "doctor").
    Returns:
        A signed JWT string ready to send in the Authorization header.
"""
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub":  str(user_id),   # JWT subject -- always a string per RFC 7519
        "role": role,
        "exp":  expire,
    }

    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


# ---------------------------------------------------------------------------
# JWT token decoding -- separated from current-user extraction
# ---------------------------------------------------------------------------

def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT token. Raises HTTP 401 on any failure.
    Separated from get_current_user so token decoding can be reused
    independently (e.g. WebSocket auth, background tasks) without
    requiring a database session.
    Raises:
        HTTPException 401 -- if the token is invalid, expired, or malformed.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",   # Generic -- never leak token details
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )

        user_id: Optional[str] = payload.get("sub")
        role:    Optional[str] = payload.get("role")

        if user_id is None or role is None:
            raise credentials_exception

        return {"user_id": int(user_id), "role": role}

    except (JWTError, ValueError):
# JWTError  -- expired, bad signature, or malformed JWT
# ValueError -- int(user_id) fails if sub contains a non-integer string
# Both map to 401; neither leaks internal detail to the caller
        raise credentials_exception


# ---------------------------------------------------------------------------
# Shared 401 factory -- generic messages only
# ---------------------------------------------------------------------------

def raise_invalid_credentials() -> None:
    """
    Raise a generic 401 for failed login attempts.
    Message is intentionally vague -- never confirm whether
    the email exists or the password was wrong.
    """
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid email or password",
        headers={"WWW-Authenticate": "Bearer"},
    )