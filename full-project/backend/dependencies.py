from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from .auth import decode_token, oauth2_scheme
from .database import get_db
from .models import User, UserRole

# Core dependency: authenticated user

def get_current_user(
    token: str     = Depends(oauth2_scheme),
    db:    Session = Depends(get_db),
) -> User:
    """
    Decode the Bearer token, look up the user in the database, and return
    the live User ORM object.

    Raises HTTP 401 if:
        - The token is invalid, expired, or malformed (raised inside decode_token)
        - The user ID in the token does not exist in the database

    Usage in routes:
        current_user: User = Depends(get_current_user)
    """
    # decode_token raises HTTP 401 on any token failure -- no extra try/except needed
    token_data = decode_token(token)

    user = db.query(User).filter(User.id == token_data["user_id"]).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",   # Generic -- never confirm user existence
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user
# Role-based authorization dependencies

def require_role(*roles: UserRole):
    """
    Dependency factory for role-based access control.

    Returns a FastAPI dependency that allows access only if the authenticated
    user's role is in the specified set. Raises HTTP 403 otherwise.

    Designed as a factory so it remains composable and reusable:
        - Single role:    Depends(require_role(UserRole.doctor))
        - Multiple roles: Depends(require_role(UserRole.doctor, UserRole.patient))

    Usage in routes:
        current_user: User = Depends(require_role(UserRole.doctor))
    """
    def _check_role(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return current_user
    return _check_role

# Convenience role dependencies -- ready to use without future changes
# Allows access to patients only
require_patient = require_role(UserRole.patient)

# Allows access to doctors only
require_doctor = require_role(UserRole.doctor)

# Allows access to either role -- equivalent to get_current_user but explicit
require_any_role = require_role(UserRole.patient, UserRole.doctor)