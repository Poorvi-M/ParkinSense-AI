# Standard library
from typing import Annotated

# FastAPI
from fastapi import APIRouter, Depends, Path, status

# SQLAlchemy
from sqlalchemy.orm import Session

# Internal -- database
from database import get_db

# Internal -- dependencies
from dependencies import get_current_user, require_doctor

# Internal -- models
from models import User

# Internal -- severity service
from services.severity_service import (
    create_severity,
    get_all_severities,
    get_severity_by_id,
    get_user_severities,
    update_severity,
)

# Internal -- schemas
from schemas import (
    SeverityCreate,
    SeverityResponse,
    SeverityUpdate,
)


router = APIRouter(prefix="/severity", tags=["Severity"])


# ---------------------------------------------------------------------------
# ROUTE REGISTRATION ORDER -- DO NOT CHANGE
# ---------------------------------------------------------------------------
#
# Static routes (/me, /all) MUST be registered before parameterised
# routes (/{severity_id}) or FastAPI will attempt to interpret strings
# like "me" or "all" as integer path parameters and return HTTP 422.
#
# This ordering rule applies to all FastAPI routers using dynamic paths.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# POST /severity
# ---------------------------------------------------------------------------
#
# BACKEND RESPONSIBILITIES:
#   - Create severity assessment records
#   - Associate records with authenticated users
#   - Validate input via schemas + service layer
#
# SECURITY NOTES:
#   - user_id is always sourced from JWT identity
#   - ownership cannot be forged from request payloads
#
# FUTURE ML INTEGRATION:
#   # TODO: Integrate automated severity prediction pipeline
# ---------------------------------------------------------------------------

@router.post(
    "/",
    response_model=SeverityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a severity record",
    description=(
        "Create a new Parkinson's severity assessment record "
        "for the authenticated user."
    ),
    response_description="The newly created severity record.",
    responses={
        201: {"description": "Severity record created successfully."},
        400: {"description": "Invalid severity data."},
        401: {"description": "Missing or invalid JWT token."},
    },
)
def create_severity_route(
    payload: SeverityCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SeverityResponse:
    """
    Create a severity assessment record for the authenticated user.

    SECURITY:
    user_id is always derived from the validated JWT token.
    Clients cannot create severity records for another user.

    VALIDATION:
    Input validation occurs through:
        - Pydantic schema validation
        - service-layer validation
    """
    return create_severity(
        user_id=current_user.id,
        severity_score=payload.severity_score,
        severity_level=payload.severity_level,
        remarks=payload.remarks,
        db=db,
    )


# ---------------------------------------------------------------------------
# GET /severity/me
# ---------------------------------------------------------------------------
#
# Registered BEFORE /{severity_id}.
#
# Returns all severity records belonging to the authenticated user.
# ---------------------------------------------------------------------------

@router.get(
    "/me",
    response_model=list[SeverityResponse],
    status_code=status.HTTP_200_OK,
    summary="Get my severity records",
    description=(
        "Return all severity records belonging to the authenticated "
        "user, ordered newest first."
    ),
    response_description=(
        "A list of severity records ordered newest first."
    ),
    responses={
        200: {"description": "Severity records retrieved successfully."},
        401: {"description": "Missing or invalid JWT token."},
    },
)
def get_my_severities_route(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[SeverityResponse]:
    """
    Return all severity records belonging to the authenticated user.

    OWNERSHIP:
    Ownership filtering is enforced using the authenticated user's ID.

    EMPTY RESULTS:
    Returning an empty list is valid if the user has no severity records.
    """
    return get_user_severities(
        user_id=current_user.id,
        db=db,
    )


# ---------------------------------------------------------------------------
# GET /severity/all
# ---------------------------------------------------------------------------
#
# Registered BEFORE /{severity_id}.
#
# DOCTOR-ONLY ENDPOINT
#
# Allows doctors to review severity records across all patients.
# ---------------------------------------------------------------------------

@router.get(
    "/all",
    response_model=list[SeverityResponse],
    status_code=status.HTTP_200_OK,
    summary="Get all severity records (doctor only)",
    description=(
        "Return all severity records across all users. "
        "Restricted to authenticated doctors."
    ),
    response_description=(
        "A list of all severity records across all users."
    ),
    responses={
        200: {"description": "Severity records retrieved successfully."},
        401: {"description": "Missing or invalid JWT token."},
        403: {"description": "Doctor role required."},
    },
)
def get_all_severities_route(
    # `_` signals the dependency result is intentionally unused.
    # The dependency exists purely for authorization enforcement.
    _: User = Depends(require_doctor),
    db: Session = Depends(get_db),
) -> list[SeverityResponse]:
    """
    Return all severity records across all users.

    ROLE ENFORCEMENT:
    Only authenticated doctors can access this endpoint.

    OWNERSHIP MODEL:
    Ownership filtering is intentionally NOT applied because doctors
    must be able to review records across all patients.
    """
    return get_all_severities(db=db)


# ---------------------------------------------------------------------------
# GET /severity/{severity_id}
# ---------------------------------------------------------------------------
#
# Registered AFTER static routes.
#
# SECURITY:
#   Ownership is enforced in the service layer.
#
# WHY 404 INSTEAD OF 403:
#   Returning 404 prevents record enumeration attacks by not revealing
#   whether a severity record exists for another user.
#
# WHY gt=0 VALIDATION EXISTS:
#   Negative and zero IDs are invalid primary keys. Rejecting them at the
#   FastAPI validation layer prevents unnecessary database queries.
# ---------------------------------------------------------------------------

@router.get(
    "/{severity_id}",
    response_model=SeverityResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a severity record by ID",
    description=(
        "Fetch a single severity record by ID. "
        "Users may only access their own severity records."
    ),
    response_description="The requested severity record.",
    responses={
        200: {"description": "Severity record retrieved successfully."},
        401: {"description": "Missing or invalid JWT token."},
        404: {"description": "Severity record not found."},
        422: {"description": "severity_id must be greater than zero."},
    },
)
def get_severity_route(
    severity_id: Annotated[
        int,
        Path(
            ...,
            gt=0,
            description="The ID of the severity record to retrieve.",
        ),
    ],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SeverityResponse:
    """
    Fetch a single severity record.

    PATH VALIDATION:
    gt=0 rejects invalid primary keys before database access.

    OWNERSHIP SECURITY:
    Unauthorized access intentionally returns HTTP 404 instead of
    HTTP 403 to prevent ID enumeration attacks.
    """
    return get_severity_by_id(
        severity_id=severity_id,
        user_id=current_user.id,
        db=db,
    )


# ---------------------------------------------------------------------------
# PATCH /severity/{severity_id}
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
#   PATCH semantically represents partial updates. Fields omitted
#   from the request are treated as "leave unchanged" by the
#   service layer.
#
# FUTURE ML INTEGRATION:
#   # TODO: Allow automated systems to update severity records
# ---------------------------------------------------------------------------

@router.patch(
    "/{severity_id}",
    response_model=SeverityResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a severity record",
    description=(
        "Update an existing severity record belonging to the "
        "authenticated user."
    ),
    response_description="The updated severity record.",
    responses={
        200: {"description": "Severity updated successfully."},
        400: {"description": "Invalid severity update data."},
        401: {"description": "Missing or invalid JWT token."},
        404: {"description": "Severity record not found."},
        422: {"description": "severity_id must be greater than zero."},
    },
)
def update_severity_route(
    severity_id: Annotated[
        int,
        Path(
            ...,
            gt=0,
            description="The ID of the severity record to update.",
        ),
    ],
    payload: SeverityUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SeverityResponse:
    """
    Update a severity record.

    OWNERSHIP:
    Users may only update their own severity records.

    PARTIAL UPDATE SUPPORT:
    Fields omitted from the request are ignored by the service layer,
    allowing partial updates without overwriting existing values.

    SECURITY:
    Unauthorized access returns HTTP 404 instead of HTTP 403 to
    prevent record enumeration attacks.
    """
    return update_severity(
        severity_id=severity_id,
        user_id=current_user.id,
        severity_score=payload.severity_score,
        severity_level=payload.severity_level,
        remarks=payload.remarks,
        db=db,
    )