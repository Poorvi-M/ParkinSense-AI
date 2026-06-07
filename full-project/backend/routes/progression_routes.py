# Standard library
from typing import Annotated

# FastAPI
from fastapi import APIRouter, Depends, Path, status

# SQLAlchemy
from sqlalchemy.orm import Session

# Internal -- database
from ..database import get_db

# Internal -- dependencies
from ..dependencies import get_current_user, require_doctor

# Internal -- models
from ..models import User

# Internal -- progression service
from ..services.progression_service import (
    create_progression,
    get_all_progressions,
    get_progression_by_id,
    get_user_progressions,
    update_progression,
)

# Internal -- schemas
from ..schemas import (
    ProgressionCreate,
    ProgressionResponse,
    ProgressionUpdate,
)


router = APIRouter(prefix="/progression", tags=["Progression"])


# ---------------------------------------------------------------------------
# ROUTE REGISTRATION ORDER -- DO NOT CHANGE
# ---------------------------------------------------------------------------
#
# Static routes (/me, /all) MUST be registered before parameterised
# routes (/{progression_id}) or FastAPI will attempt to interpret strings
# like "me" or "all" as integer path parameters and return HTTP 422.
#
# This ordering rule applies to all FastAPI routers using dynamic paths.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# POST /progression
# ---------------------------------------------------------------------------
#
# BACKEND RESPONSIBILITIES:
#   - Create progression monitoring records
#   - Associate records with authenticated users
#   - Validate input via schemas + service layer
#
# SECURITY NOTES:
#   - user_id is always sourced from JWT identity
#   - ownership cannot be forged from request payloads
#
# FUTURE ML INTEGRATION POINT:
#   Future ML services may automatically generate progression metrics
#   from longitudinal audio analysis data.
#
#   Example future integration:
#
#       # TODO: Trigger progression analysis pipeline here
#
# ---------------------------------------------------------------------------

@router.post(
    "/",
    response_model=ProgressionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a progression record",
    description=(
        "Create a new Parkinson's progression monitoring record "
        "for the authenticated user."
    ),
    response_description="The newly created progression record.",
    responses={
        201: {"description": "Progression record created successfully."},
        400: {"description": "Invalid progression data."},
        401: {"description": "Missing or invalid JWT token."},
    },
)
def create_progression_route(
    payload: ProgressionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProgressionResponse:
    """
    Create a progression monitoring record for the authenticated user.

    SECURITY:
    user_id is always derived from the validated JWT token.
    Clients cannot create progression records for another user.

    VALIDATION:
    Input validation occurs through:
        - Pydantic schema validation
        - service-layer validation

    FUTURE ML:
    This route can later integrate with automated progression
    analysis systems without changing the route contract.
    """
   
    return ProgressionResponse.model_validate(
        create_progression(
            user_id=current_user.id,
            severity_id=payload.severity_id,
            notes=payload.notes,
            db=db,
        )
    )

# ---------------------------------------------------------------------------
# GET /progression/me
# ---------------------------------------------------------------------------
#
# Registered BEFORE /{progression_id}.
#
# Returns all progression records belonging to the authenticated user.
# ---------------------------------------------------------------------------

@router.get(
    "/me",
    response_model=list[ProgressionResponse],
    status_code=status.HTTP_200_OK,
    summary="Get my progression records",
    description=(
        "Return all progression records belonging to the authenticated "
        "user, ordered newest first."
    ),
    response_description=(
        "A list of progression records ordered newest first."
    ),
    responses={
        200: {"description": "Progression records retrieved successfully."},
        401: {"description": "Missing or invalid JWT token."},
    },
)
def get_my_progressions_route(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ProgressionResponse]:
    """
    Return all progression records belonging to the authenticated user.

    OWNERSHIP:
    Ownership filtering is enforced using the authenticated user's ID.

    EMPTY RESULTS:
    Returning an empty list is valid if the user has no progression records.

    FUTURE SCALABILITY:
    Pagination and filtering can later be added without modifying the
    underlying service architecture.
    """
    progressions = get_user_progressions(user_id=current_user.id, db=db)
    return [ProgressionResponse.model_validate(p) for p in progressions]


# ---------------------------------------------------------------------------
# GET /progression/all
# ---------------------------------------------------------------------------
#
# Registered BEFORE /{progression_id}.
#
# DOCTOR-ONLY ENDPOINT
#
# Allows doctors to review progression records across all patients.
# ---------------------------------------------------------------------------

@router.get(
    "/all",
    response_model=list[ProgressionResponse],
    status_code=status.HTTP_200_OK,
    summary="Get all progression records (doctor only)",
    description=(
        "Return all progression records across all users. "
        "Restricted to authenticated doctors."
    ),
    response_description=(
        "A list of all progression records across all users."
    ),
    responses={
        200: {"description": "Progression records retrieved successfully."},
        401: {"description": "Missing or invalid JWT token."},
        403: {"description": "Doctor role required."},
    },
)
def get_all_progressions_route(
    _: User = Depends(require_doctor),
    db: Session = Depends(get_db),
) -> list[ProgressionResponse]:
    """
    Return all progression records across all users.

    ROLE ENFORCEMENT:
    Only authenticated doctors can access this endpoint.

    OWNERSHIP MODEL:
    Ownership filtering is intentionally NOT applied because doctors
    must be able to review records across all patients.

    WHY `_` IS USED:
    The resolved User object is intentionally unused. The dependency
    executes purely for authorization side-effects.

    FUTURE SCALABILITY:
    Pagination and filtering can later be added without modifying
    the route structure.
    """
    progressions = get_all_progressions(db=db)
    return [ProgressionResponse.model_validate(p) for p in progressions]


# ---------------------------------------------------------------------------
# GET /progression/{progression_id}
# ---------------------------------------------------------------------------
#
# Registered AFTER static routes.
#
# SECURITY:
#   Ownership is enforced in the service layer.
#
# WHY 404 INSTEAD OF 403:
#   Returning 404 prevents record enumeration attacks by not revealing
#   whether a progression record exists for another user.
#
# WHY gt=0 VALIDATION EXISTS:
#   Negative and zero IDs are invalid primary keys. Rejecting them at the
#   FastAPI validation layer prevents unnecessary database queries.
# ---------------------------------------------------------------------------

@router.get(
    "/{progression_id}",
    response_model=ProgressionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a progression record by ID",
    description=(
        "Fetch a single progression record by ID. "
        "Users may only access their own progression records."
    ),
    response_description="The requested progression record.",
    responses={
        200: {"description": "Progression record retrieved successfully."},
        401: {"description": "Missing or invalid JWT token."},
        404: {"description": "Progression record not found."},
        422: {"description": "progression_id must be greater than zero."},
    },
)
def get_progression_route(
    progression_id: Annotated[
        int,
        Path(
            ...,
            gt=0,
            description="The ID of the progression record to retrieve.",
        ),
    ],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProgressionResponse:
    """
    Fetch a single progression record.

    PATH VALIDATION:
    gt=0 rejects invalid primary keys before database access.

    OWNERSHIP SECURITY:
    Unauthorized access intentionally returns HTTP 404 instead of
    HTTP 403 to prevent ID enumeration attacks.
    """
    return ProgressionResponse.model_validate(
        get_progression_by_id(
            progression_id=progression_id,
            user_id=current_user.id,
            db=db,
        )
    )


# ---------------------------------------------------------------------------
# PATCH /progression/{progression_id}
# ---------------------------------------------------------------------------
#
# Registered AFTER static routes (/me, /all).
#
# PARTIAL UPDATE SUPPORT
#
# SECURITY:
#   Ownership is enforced in the service layer.
#
# WHY PATCH IS USED:
#   Fields set to None are treated as "leave unchanged" by the
#   service layer, enabling partial updates safely.
# ---------------------------------------------------------------------------

@router.patch(
    "/{progression_id}",
    response_model=ProgressionResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a progression record",
    description=(
        "Update an existing progression record belonging to the "
        "authenticated user."
    ),
    response_description="The updated progression record.",
    responses={
        200: {"description": "Progression updated successfully."},
        400: {"description": "Invalid progression update data."},
        401: {"description": "Missing or invalid JWT token."},
        404: {"description": "Progression record not found."},
        422: {"description": "progression_id must be greater than zero."},
    },
)
def update_progression_route(
    progression_id: Annotated[
        int,
        Path(
            ...,
            gt=0,
            description="The ID of the progression record to update.",
        ),
    ],
    payload: ProgressionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProgressionResponse:
    """
    Update a progression record.

    OWNERSHIP:
    Users may only update their own progression records.

    PARTIAL UPDATE SUPPORT:
    Fields set to None are ignored by the service layer, allowing
    partial updates without overwriting existing values.

    SECURITY:
    Unauthorized access returns HTTP 404 instead of HTTP 403 to
    prevent record enumeration attacks.

    FUTURE ML:
    Future automated progression analysis systems may later update
    progression records programmatically using the same service layer.
    """
    return ProgressionResponse.model_validate(
        update_progression(
            progression_id=progression_id,
            user_id=current_user.id,
            notes=payload.notes,
            db=db,
        )
    )