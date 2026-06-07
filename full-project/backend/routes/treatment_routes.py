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

# Internal -- treatment service
from ..services.treatment_service import (
    create_treatment,
    get_all_treatments,
    get_treatment_by_id,
    get_user_treatments,
    update_treatment,
)

# Internal -- schemas
from ..schemas import (
    TreatmentCreate,
    TreatmentResponse,
    TreatmentUpdate,
)


router = APIRouter(prefix="/treatment", tags=["Treatment"])


# ---------------------------------------------------------------------------
# ROUTE REGISTRATION ORDER -- DO NOT CHANGE
# ---------------------------------------------------------------------------
#
# Static routes (/me, /all) MUST be registered before parameterised
# routes (/{treatment_id}) or FastAPI will attempt to interpret strings
# like "me" or "all" as integer path parameters and return HTTP 422.
#
# This ordering rule applies to all FastAPI routers using dynamic paths.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# POST /treatment
# ---------------------------------------------------------------------------
#
# BACKEND RESPONSIBILITIES:
#   - Create treatment records
#   - Associate records with authenticated users
#   - Validate input via schemas + service layer
#
# SECURITY NOTES:
#   - user_id is always sourced from JWT identity
#   - ownership cannot be forged from request payloads
#
# FUTURE ML INTEGRATION POINT:
#
#   # TODO: Integrate ML-assisted treatment recommendation pipeline here
#
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=TreatmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a treatment record",
    description=(
        "Create a new Parkinson's treatment record "
        "for the authenticated user."
    ),
    response_description="The newly created treatment record.",
    responses={
        201: {"description": "Treatment record created successfully."},
        400: {"description": "Invalid treatment data."},
        401: {"description": "Missing or invalid JWT token."},
    },
)
def create_treatment_route(
    payload: TreatmentCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TreatmentResponse:
    """
    Create a treatment record for the authenticated user.
    SECURITY:
    user_id is always derived from the validated JWT token.
    Clients cannot create treatment records for another user.
    VALIDATION:
    Input validation occurs through:
        - Pydantic schema validation
        - service-layer validation
    """
    return TreatmentResponse.model_validate(
        create_treatment(
            user_id=current_user.id,
            medication_name=payload.medication_name,
            dosage=payload.dosage,
            remarks=payload.remarks,
            db=db,
        )
    )


# ---------------------------------------------------------------------------
# GET /treatment/me
# ---------------------------------------------------------------------------
#
# Registered BEFORE /{treatment_id}.
#
# Returns all treatment records belonging to the authenticated user.
# ---------------------------------------------------------------------------

@router.get(
    "/me",
    response_model=list[TreatmentResponse],
    status_code=status.HTTP_200_OK,
    summary="Get my treatment records",
    description=(
        "Return all treatment records belonging to the authenticated "
        "user, ordered newest first."
    ),
    response_description=(
        "A list of treatment records ordered newest first."
    ),
    responses={
        200: {"description": "Treatment records retrieved successfully."},
        401: {"description": "Missing or invalid JWT token."},
    },
)
def get_my_treatments_route(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[TreatmentResponse]:
    """
    Return all treatment records belonging to the authenticated user.
    OWNERSHIP:
    Ownership filtering is enforced using the authenticated user's ID.
    EMPTY RESULTS:
    Returning an empty list is valid if the user has no treatment records.
    FUTURE SCALABILITY:
    Pagination and filtering can later be added without modifying the
    underlying service architecture.
    """
    treatments = get_user_treatments(user_id=current_user.id, db=db)
    return [TreatmentResponse.model_validate(t) for t in treatments]


# ---------------------------------------------------------------------------
# GET /treatment/all
# ---------------------------------------------------------------------------
#
# Registered BEFORE /{treatment_id}.
#
# DOCTOR-ONLY ENDPOINT
#
# Allows doctors to review treatment records across all patients.
# ---------------------------------------------------------------------------

@router.get(
    "/all",
    response_model=list[TreatmentResponse],
    status_code=status.HTTP_200_OK,
    summary="Get all treatment records (doctor only)",
    description=(
        "Return all treatment records across all users. "
        "Restricted to authenticated doctors."
    ),
    response_description=(
        "A list of all treatment records across all users."
    ),
    responses={
        200: {"description": "Treatment records retrieved successfully."},
        401: {"description": "Missing or invalid JWT token."},
        403: {"description": "Doctor role required."},
    },
)
def get_all_treatments_route(
    _: Annotated[User, Depends(require_doctor)],
    db: Annotated[Session, Depends(get_db)],
) -> list[TreatmentResponse]:
    """
    Return all treatment records across all users.
    ROLE ENFORCEMENT:
    Only authenticated doctors can access this endpoint.
    OWNERSHIP MODEL:
    Ownership filtering is intentionally NOT applied because doctors
    must be able to review records across all patients.
    WHY `_` IS USED:
    The resolved User object is intentionally unused. The dependency
    executes purely for authorization side-effects.
    FUTURE SCALABILITY:
    Pagination should be added before deploying to large-scale
    production datasets to avoid returning excessively large
    result sets.
    """
    treatments = get_all_treatments(db=db)
    return [TreatmentResponse.model_validate(t) for t in treatments]


# ---------------------------------------------------------------------------
# GET /treatment/{treatment_id}
# ---------------------------------------------------------------------------
#
# Registered AFTER static routes.
#
# SECURITY:
#   Ownership is enforced in the service layer.
#
# WHY 404 INSTEAD OF 403:
#   Returning 404 prevents record enumeration attacks by not revealing
#   whether a treatment record exists for another user.
#
# WHY gt=0 VALIDATION EXISTS:
#   Negative and zero IDs are invalid primary keys. Rejecting them at the
#   FastAPI validation layer prevents unnecessary database queries.
# ---------------------------------------------------------------------------

@router.get(
    "/{treatment_id}",
    response_model=TreatmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a treatment record by ID",
    description=(
        "Fetch a single treatment record by ID. "
        "Users may only access their own treatment records."
    ),
    response_description="The requested treatment record.",
    responses={
        200: {"description": "Treatment record retrieved successfully."},
        401: {"description": "Missing or invalid JWT token."},
        404: {"description": "Treatment record not found."},
        422: {"description": "treatment_id must be greater than zero."},
    },
)
def get_treatment_route(
    treatment_id: Annotated[
        int,
        Path(
            ...,
            gt=0,
            description="The ID of the treatment record to retrieve.",
        ),
    ],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TreatmentResponse:
    """
    Fetch a single treatment record.

    PATH VALIDATION:
    gt=0 rejects invalid primary keys before database access.

    OWNERSHIP:
    The service layer validates both:
        - treatment_id
        - authenticated user ownership

    OWNERSHIP SECURITY:
    Unauthorized access intentionally returns HTTP 404 instead of
    HTTP 403 to prevent ID enumeration attacks.
    """
    return TreatmentResponse.model_validate(
        get_treatment_by_id(
            treatment_id=treatment_id,
            user_id=current_user.id,
            db=db,
        )
    )


# ---------------------------------------------------------------------------
# PATCH /treatment/{treatment_id}
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
# ---------------------------------------------------------------------------

@router.patch(
    "/{treatment_id}",
    response_model=TreatmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a treatment record",
    description=(
        "Update an existing treatment record belonging to the "
        "authenticated user."
    ),
    response_description="The updated treatment record.",
    responses={
        200: {"description": "Treatment updated successfully."},
        400: {"description": "Invalid treatment update data."},
        401: {"description": "Missing or invalid JWT token."},
        404: {"description": "Treatment record not found."},
        422: {"description": "treatment_id must be greater than zero."},
    },
)
def update_treatment_route(
    treatment_id: Annotated[
        int,
        Path(
            ...,
            gt=0,
            description="The ID of the treatment record to update.",
        ),
    ],
    payload: TreatmentUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TreatmentResponse:
    """
    Update a treatment record.

    OWNERSHIP:
    Users may only update their own treatment records.

    PARTIAL UPDATE SUPPORT:
    Fields omitted from the request are ignored by the service layer,
    allowing partial updates without overwriting existing values.

    SECURITY:
    Unauthorized access returns HTTP 404 instead of HTTP 403 to
    prevent record enumeration attacks.
    """
    return TreatmentResponse.model_validate(
        update_treatment(
            treatment_id=treatment_id,
            user_id=current_user.id,
            medication_name=payload.medication_name,
            dosage=payload.dosage,
            remarks=payload.remarks,
            db=db,
        )
    )