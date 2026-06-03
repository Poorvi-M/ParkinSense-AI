from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from models import Diagnosis


# ---------------------------------------------------------------------------
# Future ML integration point
# ---------------------------------------------------------------------------
#
# Currently all diagnosis records are created as placeholders.
# When ML is ready, diagnosis_result will be generated dynamically
# using externally extracted voice features passed into this service.
#
# Expected future signature:
#   create_diagnosis(user_id: int, audio_features: dict, db: Session) -> Diagnosis
#
# The route layer and DB persistence logic remain unchanged -- only the
# value assigned to diagnosis_result will come from the ML model instead
# of the static placeholder string.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------

def create_placeholder_diagnosis(user_id: int, db: Session) -> Diagnosis:
    """
    Create a placeholder Diagnosis record for the given user.

    Stores a static result string signalling that ML has not yet been
    integrated. The record is persisted immediately so it can be retrieved
    and updated once real ML output is available.

    Args:
        user_id: The ID of the authenticated user requesting diagnosis.
        db:      Active SQLAlchemy database session.

    Returns:
        The newly created and refreshed Diagnosis ORM object.
    """
    diagnosis = Diagnosis(
        user_id          = user_id,
        diagnosis_result = "Pending ML Integration",
    )

    db.add(diagnosis)
    db.commit()
    db.refresh(diagnosis)

    return diagnosis


def get_diagnosis_by_id(
    diagnosis_id: int,
    user_id:      int,
    db:           Session,
) -> Diagnosis:
    """
    Fetch a single Diagnosis record by ID, enforcing ownership.

    A user may only access their own diagnosis records. Returning HTTP 404
    (rather than 403) is intentional -- it avoids confirming that a record
    with that ID exists at all, preventing enumeration attacks.

    Args:
        diagnosis_id: The primary key of the Diagnosis record to fetch.
        user_id:      The ID of the authenticated user making the request.
        db:           Active SQLAlchemy database session.

    Returns:
        The matching Diagnosis ORM object.

    Raises:
        HTTP 404 -- if the record does not exist or belongs to another user.
    """
    diagnosis = (
        db.query(Diagnosis)
        .filter(
            Diagnosis.id      == diagnosis_id,
            Diagnosis.user_id == user_id,
        )
        .first()
    )

    if diagnosis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Diagnosis record with ID {diagnosis_id} was not found.",
        )

    return diagnosis


def get_user_diagnoses(user_id: int, db: Session) -> list[Diagnosis]:
    """
    Return all Diagnosis records for a given user, newest first.

    Ordering by created_at DESC ensures the most recent diagnosis is
    always at index 0, which is the clinically relevant default view.

    Args:
        user_id: The ID of the authenticated user.
        db:      Active SQLAlchemy database session.

    Returns:
        A list of Diagnosis ORM objects ordered by created_at descending.
        Returns an empty list if the user has no diagnosis records.
    """
    return (
        db.query(Diagnosis)
        .filter(Diagnosis.user_id == user_id)
        .order_by(Diagnosis.created_at.desc())
        .all()
    )