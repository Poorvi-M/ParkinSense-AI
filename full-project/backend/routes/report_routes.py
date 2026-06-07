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

# Internal -- services (named imports preferred over `import report_service` --
# explicit names improve IDE resolution, Swagger dependency graphs, and grep-ability)
from ..services.report_service import (
    create_report,
    get_all_reports,
    get_report_by_id,
    get_user_reports,
)

# Internal -- schemas
from ..schemas import ReportCreate, ReportResponse


router = APIRouter(prefix="/reports", tags=["Reports"])


# ---------------------------------------------------------------------------
# ROUTE REGISTRATION ORDER -- DO NOT CHANGE
# ---------------------------------------------------------------------------
# FastAPI resolves path parameters top-to-bottom at router registration time.
# Static paths (/me, /all) MUST be registered before parameterised paths
# (/{report_id}). If the order is reversed, FastAPI will attempt to cast the
# string "me" or "all" as an integer report_id and return a 422 error.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# POST /reports
# ---------------------------------------------------------------------------

@router.post(
    "/",
    response_model=ReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a report",
    description="Create a new clinical report for the authenticated user.",
    response_description="The newly created report record.",
)
def create_report_route(
    payload:      ReportCreate,
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db),
) -> ReportResponse:
    """
    Create a new clinical report for the authenticated user.

    The user_id is extracted from the validated JWT token and injected by
    get_current_user -- it is never read from the request body. This prevents
    a user from creating a report on behalf of another user by supplying a
    different user_id in the JSON payload.

    Returns the newly created ReportResponse with HTTP 201.
    """
    # Security: user_id sourced from JWT only -- payload.user_id is intentionally ignored
    return ReportResponse.model_validate(
        create_report(
            user_id=current_user.id,
            report_title=payload.report_title,
            report_content=payload.report_content,
            db=db,
        )
    )
# GET /reports/me  -- registered BEFORE /{report_id} (see ordering note above)

@router.get(
    "/me",
    response_model=list[ReportResponse],
    status_code=status.HTTP_200_OK,
    summary="Get my reports",
    description="Return all reports belonging to the authenticated user, ordered newest first.",
    response_description="A list of the authenticated user's reports, newest first.",
)
def get_my_reports_route(
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db),
) -> list[ReportResponse]:
    """
    Return all reports belonging to the authenticated user.

    Ownership is implicit -- the user_id filter is applied using the
    identity from the JWT, so users can only ever retrieve their own reports.
    Returns an empty list if the user has no reports yet.

    Future scalability: pagination (skip/limit query params) can be added
    to this route without changing the service layer.
    """
    reports = get_user_reports(user_id=current_user.id, db=db)
    return [ReportResponse.model_validate(r) for r in reports]

# GET /reports/all  -- registered BEFORE /{report_id} (see ordering note above)

@router.get(
    "/all",
    response_model=list[ReportResponse],
    status_code=status.HTTP_200_OK,
    summary="Get all reports (doctor only)",
    description="Return all reports across all users. Restricted to authenticated doctors.",
    response_description="A list of all reports across all users, newest first.",
)
def get_all_reports_route(
    # `_` signals this dependency is injected for its side-effect (role enforcement)
    # only -- require_doctor raises HTTP 403 before this function body runs if the
    # user is not a doctor. The resolved User object is not needed by the route itself.
    _:  User    = Depends(require_doctor),
    db: Session = Depends(get_db),
) -> list[ReportResponse]:
    """
    Return all reports across all users. Restricted to doctors.

    Access control: require_doctor raises HTTP 403 if the authenticated user's
    role is not 'doctor'. Patients calling this endpoint will never reach the
    service layer.

    The service function (get_all_reports) applies no ownership filter by
    design -- all access control for this route is handled here via require_doctor.

    Future scalability: filtering by user_id, date range, or report_title
    can be added as optional query parameters without modifying the route
    structure or service layer.
    """
    reports = get_all_reports(db=db)
    return [ReportResponse.model_validate(r) for r in reports]

# GET /reports/{report_id}  -- registered AFTER static paths (see ordering note above)

@router.get(
    "/{report_id}",
    response_model=ReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a report by ID",
    description="Fetch a single report by ID. Users may only access their own reports.",
    response_description="The requested report record.",
)
def get_report_route(
    report_id:    Annotated[int, Path(..., gt=0, description="The ID of the report to retrieve")],
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db),
) -> ReportResponse:
    """
    Fetch a single report by its ID.

    Path validation: report_id must be a positive integer (gt=0). FastAPI
    rejects zero or negative values with HTTP 422 before the service is called.

    Ownership: the service layer filters on both report_id and current_user.id
    in a single query. A user requesting a report that belongs to another user
    receives HTTP 404 -- not 403 -- to prevent confirming the record exists.
    """
    # Security: ownership enforced in get_report_by_id via user_id filter
    return ReportResponse.model_validate(
        get_report_by_id(report_id=report_id, user_id=current_user.id, db=db)
    )