from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..models import Progression, Severity


# ---------------------------------------------------------------------------
# Purpose
# ---------------------------------------------------------------------------
#
# Progression records form the chronological disease history of a patient.
# Each record is a timestamped entry that links a user to a specific Severity
# snapshot, building an auditable timeline of Parkinson's progression over time.
#
# Architectural constraints enforced in this service:
#
#   1. Progression.severity_id is NON-NULLABLE -- every Progression record
#      must reference an existing Severity record. This is enforced at the
#      PostgreSQL level (FK + NOT NULL) and at the service level by
#      _validate_severity_ownership() before any INSERT is attempted.
#
#   2. Severity ownership is validated before Progression creation -- a user
#      cannot attach a Progression to a Severity record that belongs to
#      another user. This prevents cross-user data contamination even if
#      a valid severity_id is supplied by a malicious client.
#
#   3. HTTP 404 is returned instead of 403 for all ownership violations --
#      returning 403 would confirm that a record with that ID exists,
#      enabling enumeration attacks. A consistent 404 reveals nothing.
#
# Future ML integration:
#   Progression records could be auto-generated as part of an ML analysis
#   pipeline -- after audio processing produces a Severity score, the
#   pipeline creates both a Severity record and a linked Progression record
#   in a single transaction. The service functions below are ready for
#   that workflow without modification.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_progression_or_404(
    progression_id: int,
    user_id:        int,
    db:             Session,
) -> Progression:
    """
    Fetch a Progression record by ID, enforcing ownership.

    Filters on both Progression.id and Progression.user_id in a single query
    to avoid a two-step fetch-then-check pattern that could leak timing
    information about record existence.

    Args:
        progression_id: Primary key of the Progression record to fetch.
        user_id:        The ID of the authenticated user (ownership check).
        db:             Active SQLAlchemy database session.

    Returns:
        The matching Progression ORM object.

    Raises:
        HTTP 404 -- if the record does not exist or belongs to another user.
                    404 is used (not 403) so the caller cannot determine
                    whether the record exists at all.
    """
    progression = (
        db.query(Progression)
        .filter(
            Progression.id      == progression_id,
            Progression.user_id == user_id,
        )
        .first()
    )

    if progression is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Progression record with ID {progression_id} was not found.",
        )

    return progression


def _validate_severity_ownership(
    severity_id: int,
    user_id:     int,
    db:          Session,
) -> Severity:
    """
    Confirm that a Severity record exists and belongs to the requesting user.

    Called before creating a Progression record to enforce the invariant:
    a user can only reference their own Severity records in their own
    Progression records. Without this check, a user could supply any valid
    severity_id and attach it to their Progression -- corrupting another
    user's clinical data linkage.

    Args:
        severity_id: The FK value the caller wants to assign to Progression.severity_id.
        user_id:     The ID of the authenticated user (ownership check).
        db:          Active SQLAlchemy database session.

    Returns:
        The validated Severity ORM object (available to the caller if needed).

    Raises:
        HTTP 404 -- if the Severity record does not exist or belongs to
                    another user. 404 is used (not 403) to prevent
                    confirmation that the severity_id belongs to someone else.
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
# Public service functions
def create_progression(
    user_id:     int,
    severity_id: int,
    db:          Session,
    notes:       str | None = None,
) -> Progression:
    """
    Create and persist a new Progression record for the given user.

    Validates that the referenced Severity record exists and belongs to the
    same user before creating the Progression. This enforces the non-nullable
    FK constraint at the application layer before the DB layer can reject it,
    resulting in a meaningful 404 rather than a raw integrity error.

    Args:
        user_id:     The ID of the authenticated user.
        severity_id: FK reference to the Severity record this progression is based on.
        db:          Active SQLAlchemy database session.
        notes:       Optional clinical notes for this progression entry (max 1000 chars,
                     enforced by schema).

    Returns:
        The newly created and refreshed Progression ORM object.

    Raises:
        HTTP 404 -- if the referenced Severity record does not exist or
                    belongs to another user.
    """
    # Validate severity ownership before any INSERT -- raises 404 if invalid
    _validate_severity_ownership(severity_id, user_id, db)

    progression = Progression(
        user_id     = user_id,
        severity_id = severity_id,
        notes       = notes,
    )

    db.add(progression)
    db.commit()
    db.refresh(progression)

    return progression


def get_progression_by_id(
    progression_id: int,
    user_id:        int,
    db:             Session,
) -> Progression:
    """
    Fetch a single Progression record by ID, enforcing ownership.

    Delegates to the shared helper to keep query logic in one place.

    Args:
        progression_id: Primary key of the record to fetch.
        user_id:        The ID of the authenticated user.
        db:             Active SQLAlchemy database session.

    Returns:
        The matching Progression ORM object.

    Raises:
        HTTP 404 -- if the record does not exist or belongs to another user.
    """
    return _get_progression_or_404(progression_id, user_id, db)


def get_user_progressions(
    user_id: int,
    db:      Session,
) -> list[Progression]:
    """
    Return all Progression records for a given user, ordered newest first.

    Ordering by created_at DESC presents the most recent disease progression
    entry at index 0 -- the clinically expected default for a monitoring
    timeline view.

    Args:
        user_id: The ID of the authenticated user.
        db:      Active SQLAlchemy database session.

    Returns:
        A list of Progression ORM objects ordered by created_at descending.
        Returns an empty list if the user has no progression records yet.
    """
    return (
        db.query(Progression)
        .filter(Progression.user_id == user_id)
        .order_by(Progression.created_at.desc())
        .all()
    )


def get_all_progressions(db: Session, limit: int = 100, offset: int = 0) -> list[Progression]:
    return (
        db.query(Progression)
        .order_by(Progression.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )


def update_progression(
    progression_id: int,
    user_id: int,
    db: Session,
    severity_id: int | None = None,
    notes: str | None = None,
) -> Progression:
    progression = _get_progression_or_404(progression_id, user_id, db)

    if severity_id is not None:
        # Validate ownership of the new severity
        _validate_severity_ownership(severity_id, user_id, db)
        progression.severity_id = severity_id

    if notes is not None:
        progression.notes = notes

    db.commit()
    db.refresh(progression)

    return progression
    db.commit()
    db.refresh(progression)

    return progression