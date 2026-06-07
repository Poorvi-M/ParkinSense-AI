from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..models import Severity


# ---------------------------------------------------------------------------
# Purpose
# ---------------------------------------------------------------------------
#
# Severity records are the clinical core of the monitoring system.
# Each record captures a snapshot of a patient's Parkinson's severity
# at a point in time, expressed as a score from 0.0 (none) to 10.0 (severe).
#
# These records serve two downstream purposes:
#   1. Progression tracking  -- Progression records reference Severity records
#      via a non-nullable FK, building a chronological disease history.
#   2. Future ML integration -- Severity scores could eventually be generated
#      automatically from audio analysis rather than entered manually.
#
# Ownership is enforced on every query: a user can only read or modify
# their own severity records. ID-only 404s (not 403s) prevent enumeration.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _validate_severity_score(score: float) -> None:
    """
    Enforce that a severity score falls within the valid clinical range.

    The 0.0--10.0 range mirrors the schema-level validation in Pydantic,
    but is re-checked here so the service layer is self-contained and safe
    to call from contexts that bypass the HTTP layer (e.g. scripts, tests).

    Args:
        score: The severity score to validate.

    Raises:
        HTTP 400 -- if score is outside [0.0, 10.0].
    """
    if not (0.0 <= score <= 10.0):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"severity_score must be between 0.0 and 10.0. Received: {score}.",
        )


def _get_severity_or_404(severity_id: int, user_id: int, db: Session) -> Severity:
    """
    Fetch a Severity record by ID, enforcing ownership.

    Shared by get_severity_by_id, update_severity, and any future function
    that needs a verified record before acting on it.

    Raises:
        HTTP 404 -- if the record does not exist or belongs to another user.
    """
    severity = (
        db.query(Severity)
        .filter(
            Severity.id      == severity_id,
            Severity.user_id == user_id,
        )
        .first()
    )

    if severity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Severity record with ID {severity_id} was not found.",
        )

    return severity


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------

def create_severity(
    user_id:        int,
    severity_score: float,
    db:             Session,
    remarks:        str | None = None,
    severity_level: str | None = None,
) -> Severity:
    """
    Create and persist a new Severity record for the given user.
    Args:
        user_id:        The ID of the authenticated user.
        severity_score: Clinical severity score in range [0.0, 10.0].
        remarks:        Optional clinician notes (max 500 chars, enforced by schema).
        db:             Active SQLAlchemy database session.
    Returns:
        The newly created and refreshed Severity ORM object.
    Raises:
        HTTP 400 -- if severity_score is outside [0.0, 10.0].
    """
    _validate_severity_score(severity_score)

    severity = Severity(
        user_id        = user_id,
        severity_score = severity_score,
        remarks        = remarks,
    )

    db.add(severity)
    db.commit()
    db.refresh(severity)

    return severity


def get_user_severities(user_id: int, db: Session) -> list[Severity]:
    return get_user_severity_records(user_id, db)


def get_all_severities(db: Session, limit: int = 100, offset: int = 0) -> list[Severity]:
    return (
        db.query(Severity)
        .order_by(Severity.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )


def update_severity(
    severity_id:    int,
    user_id:        int,
    db:             Session,
    severity_score: float | None = None,
    remarks:        str | None = None,
) -> Severity:
    """
    Update an existing Severity record. Only provided fields are changed.

    Partial updates are supported: passing None for a field leaves it
    unchanged in the database. This mirrors PATCH semantics even though
    the route uses PUT, keeping the service flexible for either verb.

    Args:
        severity_id:    Primary key of the record to update.
        user_id:        The ID of the authenticated user (ownership check).
        severity_score: New severity score, or None to leave unchanged.
        remarks:        New remarks string, or None to leave unchanged.
        db:             Active SQLAlchemy database session.
    Returns:
        The updated and refreshed Severity ORM object.
    Raises:
        HTTP 404 -- if the record does not exist or belongs to another user.
        HTTP 400 -- if the new severity_score is outside [0.0, 10.0].
    """
    severity = _get_severity_or_404(severity_id, user_id, db)

    if severity_score is not None:
        _validate_severity_score(severity_score)
        severity.severity_score = severity_score

    if remarks is not None:
        severity.remarks = remarks

    db.commit()
    db.refresh(severity)

    return severity


def get_severity_by_id(
    severity_id: int,
    user_id:     int,
    db:          Session,
) -> Severity:
    """
    Fetch a single Severity record by ID, enforcing ownership.

    Args:
        severity_id: Primary key of the record to fetch.
        user_id:     The ID of the authenticated user.
        db:          Active SQLAlchemy database session.

    Returns:
        The matching Severity ORM object.

    Raises:
        HTTP 404 -- if the record does not exist or belongs to another user.
    """
    return _get_severity_or_404(severity_id, user_id, db)


def get_user_severity_records(user_id: int, db: Session) -> list[Severity]:
    return (
        db.query(Severity)
        .filter(Severity.user_id == user_id)
        .order_by(Severity.created_at.desc())
        .all()
    )
