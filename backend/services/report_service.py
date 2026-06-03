from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from models import Report, User


# ---------------------------------------------------------------------------
# Purpose
# ---------------------------------------------------------------------------
#
# Report records provide a structured clinical summary for a patient's
# Parkinson's monitoring history. Each report has a title and free-form
# content, allowing clinicians or patients to document assessments,
# consultation outcomes, or periodic reviews in a retrievable format.
#
# All reports are currently created manually via the API. No automated
# report generation logic exists at this stage.
#
# Architectural constraints enforced in this service:
#
#   1. Ownership is enforced on every query -- users can only read their
#      own reports. Queries filter on both Report.id and Report.user_id
#      in a single operation to prevent timing side-channels.
#
#   2. HTTP 404 is returned for all ownership violations -- returning 403
#      would confirm that a record with the given ID exists, enabling
#      enumeration attacks. A consistent 404 reveals nothing to the caller.
#
#   3. Service-layer validation duplicates Pydantic schema validation --
#      this is intentional. Services must be self-contained and safe to call
#      from contexts that bypass the HTTP layer (scripts, tests, pipelines).
#      Pydantic guards the HTTP boundary; the service guards the data layer.
#
# Future ML integration:
#   A future ML pipeline could automatically generate clinical reports by
#   aggregating a patient's diagnosis results, severity scores, progression
#   history, and treatment records into a structured narrative. When that
#   happens, create_report() can be called programmatically by the pipeline
#   without any modification to this service -- only the caller changes.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _validate_report_fields(
    report_title:   str | None = None,
    report_content: str | None = None,
) -> None:
    """
    Validate report fields at the service layer.

    Ensures report_title and report_content are non-empty, non-whitespace
    strings when provided. Called on create -- both fields are always
    required. None values mean "skip validation for this field" to keep
    the helper reusable if partial update support is added in the future.

    Args:
        report_title:   Report title to validate, or None to skip.
        report_content: Report body content to validate, or None to skip.

    Raises:
        HTTP 400 -- if report_title is an empty or whitespace-only string.
        HTTP 400 -- if report_content is an empty or whitespace-only string.
    """
    if report_title is not None and not report_title.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="report_title must not be empty.",
        )

    if report_content is not None and not report_content.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="report_content must not be empty.",
        )


def _get_report_or_404(
    report_id: int,
    user_id:   int,
    db:        Session,
) -> Report:
    """
    Fetch a Report record by ID, enforcing ownership.

    Filters on both Report.id and Report.user_id in a single query
    to avoid a two-step fetch-then-check pattern that could leak timing
    information about record existence.

    Args:
        report_id: Primary key of the Report record to fetch.
        user_id:   The ID of the authenticated user (ownership check).
        db:        Active SQLAlchemy database session.

    Returns:
        The matching Report ORM object.

    Raises:
        HTTP 404 -- if the record does not exist or belongs to another user.
                    404 is used (not 403) so the caller cannot determine
                    whether the record exists at all.
    """
    report = (
        db.query(Report)
        .filter(
            Report.id      == report_id,
            Report.user_id == user_id,
        )
        .first()
    )

    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report with ID {report_id} was not found.",
        )

    return report


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------

def create_report(
    user_id:        int,
    report_title:   str,
    report_content: str,
    db:             Session,
) -> Report:
    """
    Create and persist a new Report record for the given user.

    Validates that report_title and report_content are non-empty before
    any database interaction.

    Args:
        user_id:        The ID of the authenticated user.
        report_title:   Title of the report (max 255 chars, enforced by schema).
        report_content: Full body content of the report (max 10000 chars,
                        enforced by schema).
        db:             Active SQLAlchemy database session.

    Returns:
        The newly created and refreshed Report ORM object.

    Raises:
        HTTP 400 -- if report_title or report_content is empty or whitespace-only.
    """
    _validate_report_fields(report_title=report_title, report_content=report_content)

    # Fix 2: verify the user exists before inserting -- guards against stale or
    # fabricated user_id values that bypass JWT validation (e.g. pipeline calls)
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    report = Report(
        user_id        = user_id,
        report_title   = report_title,
        report_content = report_content,
    )

    # Fix 1: wrap DB operations in try/except -- rolls back on any SQLAlchemy
    # error to prevent a broken session from contaminating the connection pool
    try:
        db.add(report)
        db.commit()
        db.refresh(report)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create report.",
        )

    return report


def get_report_by_id(
    report_id: int,
    user_id:   int,
    db:        Session,
) -> Report:
    """
    Fetch a single Report record by ID, enforcing ownership.

    Delegates to the shared helper to keep query logic in one place.

    Args:
        report_id: Primary key of the report to fetch.
        user_id:   The ID of the authenticated user.
        db:        Active SQLAlchemy database session.

    Returns:
        The matching Report ORM object.

    Raises:
        HTTP 404 -- if the record does not exist or belongs to another user.
    """
    return _get_report_or_404(report_id, user_id, db)


def get_all_reports(db: Session, limit: int = 50, offset: int = 0) -> list[Report]:
    """
    Return all Report records across all users, ordered newest first.

    This function is intended for administrative or doctor-level access only.
    Role enforcement is the responsibility of the route layer -- this service
    function performs no ownership filtering by design.

    Args:
        db: Active SQLAlchemy database session.

    Returns:
        A list of all Report ORM objects ordered by created_at descending.
        Returns an empty list if no reports exist.
    """
    # Fix 3: limit/offset prevent unbounded result sets on large datasets
    return (
        db.query(Report)
        .order_by(Report.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )


def get_user_reports(
    user_id: int,
    db:      Session,
    limit:   int = 50,
    offset:  int = 0,
) -> list[Report]:
    """
    Return all Report records for a given user, ordered newest first.

    Ordering by created_at DESC surfaces the most recently created report
    at index 0 -- the expected default when a patient or clinician reviews
    a patient's reporting history.

    Args:
        user_id: The ID of the authenticated user.
        db:      Active SQLAlchemy database session.

    Returns:
        A list of Report ORM objects ordered by created_at descending.
        Returns an empty list if the user has no reports yet.
    """
    # Fix 3: limit/offset prevent unbounded result sets on large datasets
    return (
        db.query(Report)
        .filter(Report.user_id == user_id)
        .order_by(Report.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )