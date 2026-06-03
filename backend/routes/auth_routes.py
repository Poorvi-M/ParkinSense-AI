# FastAPI
from fastapi import APIRouter, Depends, HTTPException, status

# SQLAlchemy
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

# Internal -- auth
from auth import (
    create_access_token,
    hash_password,
    raise_invalid_credentials,
    verify_password,
)

# Internal -- database
from database import get_db

# Internal -- dependencies
from dependencies import get_current_user

# Internal -- models
from models import User

# Internal -- schemas
from schemas import TokenResponse, UserLogin, UserRegister, UserResponse


router = APIRouter(prefix="/auth", tags=["Authentication"])


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _check_duplicate_user(email: str, username: str, db: Session) -> None:
    """
    Pre-flight uniqueness check for email and username.

    Runs before the DB INSERT to surface conflicts early with a clear 400,
    avoiding an unnecessary write attempt in the common case. The IntegrityError
    handler in register_route remains as the definitive guard for the race
    condition where two concurrent requests pass this check simultaneously.

    Both checks return an identical message -- the caller cannot determine
    whether the email or the username caused the conflict, preventing
    field-level enumeration attacks.

    Args:
        email:    Normalised (lowercased) email to check.
        username: Username to check.
        db:       Active SQLAlchemy database session.

    Raises:
        HTTP 400 -- if a user with the given email or username already exists.
    """
    if (
        db.query(User).filter(User.email == email).first()
        or db.query(User).filter(User.username == username).first()
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email or username already exists.",
        )


# ---------------------------------------------------------------------------
# POST /auth/register
# ---------------------------------------------------------------------------

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Register a new patient or doctor account. Returns the created user profile.",
    response_description="The newly registered user profile (no password or hash returned).",
    responses={
        400: {"description": "Email or username already registered."},
        500: {"description": "Database failure during account creation."},
    },
)
def register_route(
    payload: UserRegister,
    db:      Session = Depends(get_db),
) -> UserResponse:
    """
    Register a new user account.

    EMAIL NORMALISATION (security requirement):
    Email is lowercased before all checks and storage. Without normalisation,
    'User@Example.com' and 'user@example.com' would be treated as distinct
    accounts, breaking uniqueness guarantees and enabling duplicate registration.

    PRE-FLIGHT + INTEGRITY GUARD (two-layer protection):
    _check_duplicate_user() provides fast UX feedback for the common case.
    The IntegrityError catch handles the race condition where two concurrent
    requests both pass the pre-flight check and one loses the DB unique
    constraint -- the rollback keeps the session clean for pool reuse.

    PASSWORD SECURITY:
    The plain-text password is hashed with bcrypt immediately. It is never
    written to the database, never logged, and never returned in any response.
    hashed_password is excluded from UserResponse at the Pydantic serialisation
    layer -- it cannot leak even if the ORM object is returned directly.
    """
    # Security: normalise email before any check or storage -- see docstring
    normalised_email: str = payload.email.lower()

    # Pre-flight uniqueness check -- centralised in helper to avoid duplication
    _check_duplicate_user(email=normalised_email, username=payload.username, db=db)

    user: User = User(
        username        = payload.username,
        email           = normalised_email,
        hashed_password = hash_password(payload.password),  # plain-text never stored
        role            = payload.role,
    )

    try:
        db.add(user)
        db.commit()
        # refresh() loads DB-generated fields (id, created_at) back onto the object
        db.refresh(user)
    except IntegrityError:
        # Race condition: concurrent request won the unique constraint -- rollback
        # and surface the same generic 400 as the pre-flight check
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email or username already exists.",
        )
    except SQLAlchemyError:
        # Narrow catch: covers connection loss and non-integrity DB failures only.
        # Non-SQLAlchemy exceptions (e.g. MemoryError, bugs) propagate naturally
        # so they are not silently swallowed and hidden from error tracking.
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create account. Please try again.",
        )

    # Security: UserResponse excludes hashed_password -- cannot leak via this route
    return user


# ---------------------------------------------------------------------------
# POST /auth/login
# ---------------------------------------------------------------------------

@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Login and obtain a JWT token",
    description="Authenticate with email and password. Returns a Bearer JWT token.",
    response_description="A JWT access token with token_type='bearer'.",
    responses={
        401: {"description": "Invalid email or password."},
    },
)
def login_route(
    payload: UserLogin,
    db:      Session = Depends(get_db),
) -> TokenResponse:
    """
    Authenticate a user and return a signed JWT access token.

    EMAIL NORMALISATION (security requirement):
    Email is lowercased before the DB lookup to match the normalised value
    stored at registration. Without this, a user registered as 'A@B.com'
    could not log in as 'a@b.com', breaking their account.

    IDENTICAL FAILURE MESSAGE (security requirement):
    Both "user not found" and "wrong password" call raise_invalid_credentials(),
    which always returns "Invalid email or password". Distinct messages would
    allow an unauthenticated caller to enumerate which emails are registered
    (user enumeration attack). The single-branch check below is intentional:
        `if user is None or not verify_password(...)`
    This ensures both conditions reach the same code path.

    JWT PAYLOAD: contains user_id (sub), role, and expiry (exp).
    hashed_password is never included in or derivable from the token.
    """
    # Security: normalise email -- must match the value stored at registration
    normalised_email: str = payload.email.lower()

    user: User | None = db.query(User).filter(User.email == normalised_email).first()

    # Security: single branch for missing user AND wrong password --
    # prevents user enumeration by returning identical responses for both cases
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise_invalid_credentials()

    token: str = create_access_token(user_id=user.id, role=user.role.value)

    return TokenResponse(access_token=token)


# ---------------------------------------------------------------------------
# GET /auth/me
# ---------------------------------------------------------------------------

@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user profile",
    description="Return the profile of the currently authenticated user.",
    response_description="The authenticated user's profile (no password or hash returned).",
    responses={
        401: {"description": "Missing, expired, or invalid JWT token."},
    },
)
def me_route(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """
    Return the profile of the currently authenticated user.

    get_current_user decodes and validates the JWT, then fetches the live User
    record from the database. HTTP 401 is raised by the dependency before this
    function body runs if the token is missing, expired, or invalid, or if the
    user has been deleted since the token was issued.

    No additional database query is made here -- the ORM object is fully
    resolved by the dependency.

    Security: UserResponse excludes hashed_password at the Pydantic
    serialisation layer -- it cannot leak through this route.
    """
    return current_user