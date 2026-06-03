from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from models import Treatment


# ---------------------------------------------------------------------------
# Purpose
# ---------------------------------------------------------------------------
#
# Treatment records capture the medication history of a Parkinson's patient.
# Each record stores a medication name, dosage, and optional clinical remarks,
# providing a longitudinal view of the treatment plan over time.
#
# All treatment entries are currently manual -- a clinician or patient logs
# each record explicitly via the API. No automated treatment logic exists.
#
# Architectural constraints enforced in this service:
#
#   1. Ownership is enforced on every query -- users can only read or modify
#      their own treatment records. Queries filter on both Treatment.id and
#      Treatment.user_id in a single operation to prevent timing side-channels.
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
# Future ML / recommendation integration:
#   A future ML pipeline could suggest treatment plans automatically based
#   on a patient's audio analysis and severity history. When that happens,
#   create_treatment() can be called programmatically by the pipeline without
#   any changes to this service -- only the caller changes.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _validate_treatment_fields(
    medication_name: str | None = None,
    dosage:          str | None = None,
) -> None:
    """
    Validate treatment fields at the service layer.

    Ensures medication_name and dosage are non-empty strings when provided.
    Called on both create and update paths -- on update, only supplied fields
    are validated; None values mean "leave unchanged" and are skipped.

    Args:
        medication_name: Medication name to validate, or None to skip.
        dosage:          Dosage string to validate, or None to skip.

    Raises:
        HTTP 400 -- if medication_name is an empty or whitespace-only string.
        HTTP 400 -- if dosage is an empty or whitespace-only string.
    """
    if medication_name is not None and not medication_name.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="medication_name must not be empty.",
        )

    if dosage is not None and not dosage.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="dosage must not be empty.",
        )


def _get_treatment_or_404(
    treatment_id: int,
    user_id:      int,
    db:           Session,
) -> Treatment:
    """
    Fetch a Treatment record by ID, enforcing ownership.

    Filters on both Treatment.id and Treatment.user_id in a single query
    to avoid a two-step fetch-then-check pattern that could leak timing
    information about record existence.

    Args:
        treatment_id: Primary key of the Treatment record to fetch.
        user_id:      The ID of the authenticated user (ownership check).
        db:           Active SQLAlchemy database session.

    Returns:
        The matching Treatment ORM object.

    Raises:
        HTTP 404 -- if the record does not exist or belongs to another user.
                    404 is used (not 403) so the caller cannot determine
                    whether the record exists at all.
    """
    treatment = (
        db.query(Treatment)
        .filter(
            Treatment.id      == treatment_id,
            Treatment.user_id == user_id,
        )
        .first()
    )

    if treatment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Treatment record with ID {treatment_id} was not found.",
        )

    return treatment


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------

def create_treatment(
    user_id:         int,
    medication_name: str,
    dosage:          str,
    db:              Session,
    remarks:         str | None = None,
) -> Treatment:
    """
    Create and persist a new Treatment record for the given user.

    Validates that medication_name and dosage are non-empty before
    any database interaction. remarks is optional and may be omitted.

    Args:
        user_id:         The ID of the authenticated user.
        medication_name: Name of the prescribed medication (max 255 chars,
                         enforced by schema).
        dosage:          Dosage instructions (max 100 chars, enforced by schema).
        db:              Active SQLAlchemy database session.
        remarks:         Optional clinical notes (max 500 chars, enforced by schema).

    Returns:
        The newly created and refreshed Treatment ORM object.

    Raises:
        HTTP 400 -- if medication_name or dosage is empty or whitespace-only.
    """
    _validate_treatment_fields(medication_name=medication_name, dosage=dosage)

    treatment = Treatment(
        user_id         = user_id,
        medication_name = medication_name,
        dosage          = dosage,
        remarks         = remarks,
    )

    db.add(treatment)
    db.commit()
    db.refresh(treatment)

    return treatment


def update_treatment(
    treatment_id:    int,
    user_id:         int,
    db:              Session,
    medication_name: str | None = None,
    dosage:          str | None = None,
    remarks:         str | None = None,
) -> Treatment:
    """
    Update an existing Treatment record. Only provided fields are changed.

    Partial updates are supported: passing None for a field leaves it
    unchanged in the database. This mirrors PATCH semantics even though
    the route uses PUT, keeping the service flexible for either verb.

    Args:
        treatment_id:    Primary key of the record to update.
        user_id:         The ID of the authenticated user (ownership check).
        db:              Active SQLAlchemy database session.
        medication_name: New medication name, or None to leave unchanged.
        dosage:          New dosage string, or None to leave unchanged.
        remarks:         New remarks string, or None to leave unchanged.

    Returns:
        The updated and refreshed Treatment ORM object.

    Raises:
        HTTP 404 -- if the record does not exist or belongs to another user.
        HTTP 400 -- if medication_name or dosage is empty or whitespace-only.
    """
    treatment = _get_treatment_or_404(treatment_id, user_id, db)

    # Validate only the fields being updated -- None means "leave unchanged"
    _validate_treatment_fields(medication_name=medication_name, dosage=dosage)

    if medication_name is not None:
        treatment.medication_name = medication_name

    if dosage is not None:
        treatment.dosage = dosage

    if remarks is not None:
        treatment.remarks = remarks

    db.commit()
    db.refresh(treatment)

    return treatment


def get_treatment_by_id(
    treatment_id: int,
    user_id:      int,
    db:           Session,
) -> Treatment:
    """
    Fetch a single Treatment record by ID, enforcing ownership.

    Delegates to the shared helper to keep query logic in one place.

    Args:
        treatment_id: Primary key of the record to fetch.
        user_id:      The ID of the authenticated user.
        db:           Active SQLAlchemy database session.

    Returns:
        The matching Treatment ORM object.

    Raises:
        HTTP 404 -- if the record does not exist or belongs to another user.
    """
    return _get_treatment_or_404(treatment_id, user_id, db)


def get_user_treatments(
    user_id: int,
    db:      Session,
) -> list[Treatment]:
    """
    Return all Treatment records for a given user, ordered newest first.

    Ordering by created_at DESC surfaces the most recent treatment entry
    at index 0 -- the clinically expected default when reviewing a
    patient's active medication history.

    Args:
        user_id: The ID of the authenticated user.
        db:      Active SQLAlchemy database session.

    Returns:
        A list of Treatment ORM objects ordered by created_at descending.
        Returns an empty list if the user has no treatment records yet.
    """
    return (
        db.query(Treatment)
        .filter(Treatment.user_id == user_id)
        .order_by(Treatment.created_at.desc())
        .all()
    )