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

# Internal -- diagnosis service
from services.diagnosis_service import (
    create_diagnosis,
    get_all_diagnoses,
    get_diagnosis_by_id,
    get_user_diagnoses,
    update_diagnosis,
)

# Internal -- schemas
from schemas import (
    DiagnosisCreate,
    DiagnosisResponse,
    DiagnosisUpdate,
)


router = APIRouter(prefix="/diagnosis", tags=["Diagnosis"])


# ---------------------------------------------------------------------------
# ROUTE REGISTRATION ORDER -- DO NOT CHANGE
# ---------------------------------------------------------------------------
#
# Static routes (/me, /all) MUST be registered before parameterised
# routes (/{diagnosis_id}) or FastAPI will attempt to interpret strings
# like "me" or "all" as integer path parameters and return HTTP 422.
#
# This ordering rule applies to all FastAPI routers using dynamic paths.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# POST /diagnosis
# ---------------------------------------------------------------------------
#
# BACKEND RESPONSIBILITIES:
#   - Create diagnosis records
#   - Associate records with authenticated users
#   - Validate input via schemas + service layer
#
# SECURITY NOTES:
#   - user_id is always sourced from JWT identity
#   - ownership cannot be forged from request payloads
#
# FUTURE ML INTEGRATION POINT:
#   A future ML pipeline may automatically generate diagnosis predictions
#   from uploaded audio analysis results.
#
#   Example future integration:
#
#       # TODO: Trigger ML diagnosis pipeline here
#
# ---------------------------------------------------------------------------

@router.post(
    "/",
    response_model=DiagnosisResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a diagnosis record",
    description=(
        "Create a new Parkinson's diagnosis record for the authenticated user."
    ),
    response_description="The newly created diagnosis record.",
    responses={
        201: {"description": "Diagnosis created successfully."},
        400: {"description": "Invalid diagnosis data."},
        401: {"description": "Missing or invalid JWT token."},
    },
)
def create_diagnosis_route(
    payload: DiagnosisCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DiagnosisResponse:
    """
    Create a diagnosis record for the authenticated user.

    SECURITY:
    user_id is always derived from the validated JWT token.
    Clients cannot create diagnosis records for another user.

    VALIDATION:
    Input validation occurs through both:
        - Pydantic schema validation
        - service-layer validation

    FUTURE ML:
    This route can later support automated diagnosis generation from
    audio analysis pipelines without changing the route contract.
    """
    return create_diagnosis(
        user_id=current_user.id,
        diagnosis_result=payload.diagnosis_result,
        confidence_score=payload.confidence_score,
        remarks=payload.remarks,
        db=db,
    )


# ---------------------------------------------------------------------------
# GET /diagnosis/me
# ---------------------------------------------------------------------------
#
# Registered BEFORE /{diagnosis_id}.
#
# Returns all diagnosis records belonging to the authenticated user.
# ---------------------------------------------------------------------------

@router.get(
    "/me",
    response_model=list[DiagnosisResponse],
    status_code=status.HTTP_200_OK,
    summary="Get my diagnosis records",
    description=(
        "Return all diagnosis records belonging to the authenticated user, "
        "ordered newest first."
    ),
    response_description="A list of diagnosis records ordered newest first.",
    responses={
        200: {"description": "Diagnosis records retrieved successfully."},
        401: {"description": "Missing or invalid JWT token."},
    },
)
def get_my_diagnoses_route(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[DiagnosisResponse]:
    """
    Return all diagnosis records belonging to the authenticated user.

    OWNERSHIP:
    Ownership filtering is enforced using the authenticated user's ID.

    EMPTY RESULTS:
    Returning an empty list is valid if the user has no diagnosis records.

    FUTURE SCALABILITY:
    Pagination and filtering can later be added without modifying the
    underlying service architecture.
    """
    return get_user_diagnoses(
        user_id=current_user.id,
        db=db,
    )


# ---------------------------------------------------------------------------
# GET /diagnosis/all
# ---------------------------------------------------------------------------
#
# Registered BEFORE /{diagnosis_id}.
#
# DOCTOR-ONLY ENDPOINT
#
# Allows doctors to review diagnosis records across all patients.
# ---------------------------------------------------------------------------

@router.get(
    "/all",
    response_model=list[DiagnosisResponse],
    status_code=status.HTTP_200_OK,
    summary="Get all diagnosis records (doctor only)",
    description=(
        "Return all diagnosis records across all users. "
        "Restricted to authenticated doctors."
    ),
    response_description="A list of all diagnosis records across all users.",
    responses={
        200: {"description": "Diagnosis records retrieved successfully."},
        401: {"description": "Missing or invalid JWT token."},
        403: {"description": "Doctor role required."},
    },
)
def get_all_diagnoses_route(
    _: User = Depends(require_doctor),
    db: Session = Depends(get_db),
) -> list[DiagnosisResponse]:
    """
    Return all diagnosis records across all users.

    ROLE ENFORCEMENT:
    Only authenticated doctors can access this endpoint.

    OWNERSHIP MODEL:
    Ownership filtering is intentionally NOT applied because doctors
    must be able to review records across all patients.

    WHY `_` IS USED:
    The resolved User object is intentionally unused. The dependency is
    executed purely for its authorization side-effect.
    """
    return get_all_diagnoses(db=db)


# ---------------------------------------------------------------------------
# GET /diagnosis/{diagnosis_id}
# ---------------------------------------------------------------------------
#
# Registered AFTER static routes.
#
# SECURITY:
#   Ownership is enforced in the service layer.
#
# WHY 404 INSTEAD OF 403:
#   Returning 404 prevents record enumeration attacks by not revealing
#   whether a diagnosis record exists for another user.
#
# WHY gt=0 VALIDATION EXISTS:
#   Negative and zero IDs are invalid primary keys. Rejecting them at the
#   FastAPI validation layer prevents unnecessary database queries.
# ---------------------------------------------------------------------------

@router.get(
    "/{diagnosis_id}",
    response_model=DiagnosisResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a diagnosis record by ID",
    description=(
        "Fetch a single diagnosis record by ID. "
        "Users may only access their own diagnosis records."
    ),
    response_description="The requested diagnosis record.",
    responses={
        200: {"description": "Diagnosis record retrieved successfully."},
        401: {"description": "Missing or invalid JWT token."},
        404: {"description": "Diagnosis record not found."},
        422: {"description": "diagnosis_id must be greater than zero."},
    },
)
def get_diagnosis_route(
    diagnosis_id: Annotated[
        int,
        Path(
            ...,
            gt=0,
            description="The ID of the diagnosis record to retrieve.",
        ),
    ],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DiagnosisResponse:
    """
    Fetch a single diagnosis record.

    PATH VALIDATION:
    gt=0 rejects invalid primary keys before database access.

    OWNERSHIP SECURITY:
    Unauthorized access intentionally returns HTTP 404 instead of
    HTTP 403 to prevent ID enumeration attacks.
    """
    return get_diagnosis_by_id(
        diagnosis_id=diagnosis_id,
        user_id=current_user.id,
        db=db,
    )


# ---------------------------------------------------------------------------
# PUT /diagnosis/{diagnosis_id}
# ---------------------------------------------------------------------------
#
# Registered AFTER static routes (/me, /all).
#
# PARTIAL UPDATE SUPPORT
#
# SECURITY:
#   Ownership is enforced in the service layer.
#
# WHY PUT SUPPORTS PARTIAL UPDATES:
#   The service layer treats None values as "leave unchanged",
#   enabling PATCH-like behaviour while preserving a simple API surface.
# ---------------------------------------------------------------------------

@router.patch(
    "/{diagnosis_id}",
    response_model=DiagnosisResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a diagnosis record",
    description=(
        "Update an existing diagnosis record belonging to the "
        "authenticated user."
    ),
    response_description="The updated diagnosis record.",
    responses={
        200: {"description": "Diagnosis updated successfully."},
        400: {"description": "Invalid diagnosis update data."},
        401: {"description": "Missing or invalid JWT token."},
        404: {"description": "Diagnosis record not found."},
        422: {"description": "diagnosis_id must be greater than zero."},
    },
)
def update_diagnosis_route(
    diagnosis_id: Annotated[
        int,
        Path(
            ...,
            gt=0,
            description="The ID of the diagnosis record to update.",
        ),
    ],
    payload: DiagnosisUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DiagnosisResponse:
    """
    Update a diagnosis record.

    OWNERSHIP:
    Users may only update their own diagnosis records.

    PARTIAL UPDATE SUPPORT:
    Fields set to None are ignored by the service layer, allowing
    partial updates without overwriting existing values.

    SECURITY:
    Unauthorized access returns HTTP 404 instead of HTTP 403 to
    prevent record enumeration attacks.

    FUTURE ML:
    Future automated diagnosis pipelines may later update diagnosis
    records programmatically using the same service layer.
    """
    return update_diagnosis(
        diagnosis_id=diagnosis_id,
        user_id=current_user.id,
        diagnosis_result=payload.diagnosis_result,
        confidence_score=payload.confidence_score,
        remarks=payload.remarks,
        db=db,
    )