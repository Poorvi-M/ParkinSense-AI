
# Standard library
from typing import Annotated

# FastAPI
from fastapi import APIRouter, Depends, File, Path, status, UploadFile

# SQLAlchemy
from sqlalchemy.orm import Session

# Internal -- audio service
from services.audio_service import (
    get_audio_by_id,
    get_user_audio_files,
    update_audio_status,
    upload_audio,
)

# Internal -- database
from database import get_db

# Internal -- dependencies
from dependencies import get_current_user, require_doctor

# Internal -- models
from models import User

# Internal -- schemas
from schemas import AudioFileResponse, AudioStatusResponse


router = APIRouter(prefix="/audio", tags=["Audio"])


# ---------------------------------------------------------------------------
# ROUTE REGISTRATION ORDER -- DO NOT CHANGE
# ---------------------------------------------------------------------------
#
# Static routes (/me, /upload) must be registered BEFORE parameterised
# routes (/{audio_id}) or FastAPI will attempt to interpret strings like
# "me" as integer path parameters and return HTTP 422.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# POST /audio/upload
# ---------------------------------------------------------------------------
#
# BACKEND RESPONSIBILITIES:
#   - Validate file type and size
#   - Persist metadata
#   - Store uploaded file safely
#   - Associate upload with authenticated user
#
# SECURITY NOTES:
#   - user_id is always sourced from JWT identity
#   - client filenames are never trusted directly
#   - internal filesystem paths are hidden from API responses
#
# FUTURE ML INTEGRATION POINT:
#   After successful upload, this route/service can later trigger:
#       - audio preprocessing
#       - voice feature extraction
#       - Parkinson's severity prediction
#       - asynchronous background analysis pipeline
#
#   Example future integration:
#
#       # TODO: Trigger ML audio analysis pipeline here
#
# ---------------------------------------------------------------------------

@router.post(
    "/upload",
    response_model=AudioFileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload an audio file",
    description=(
        "Upload a .wav or .mp3 audio file. "
        "Maximum file size: 50 MB."
    ),
    response_description="Metadata for the uploaded audio file.",
    responses={
        201: {"description": "Audio file uploaded successfully."},
        400: {"description": "Invalid file type or file exceeds size limit."},
        401: {"description": "Missing or invalid JWT token."},
        500: {"description": "File storage failure."},
    },
)
def upload_audio_route(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AudioFileResponse:
    """
    Upload an audio file for the authenticated user.

    SECURITY:
    Ownership is always derived from the validated JWT token.
    Clients cannot upload files for another user.

    VALIDATION:
    File validation occurs in the service layer before persistence.
    """
    return upload_audio(
        file=file,
        user_id=current_user.id,
        db=db,
    )


# ---------------------------------------------------------------------------
# GET /audio/me
# ---------------------------------------------------------------------------
#
# Registered BEFORE /{audio_id}.
#
# Returns all audio uploads belonging to the authenticated user.
# ---------------------------------------------------------------------------

@router.get(
    "/me",
    response_model=list[AudioFileResponse],
    status_code=status.HTTP_200_OK,
    summary="Get my audio files",
    description="Return all audio files uploaded by the authenticated user.",
    response_description="A list of uploaded audio files.",
    responses={
        200: {"description": "Audio files retrieved successfully."},
        401: {"description": "Missing or invalid JWT token."},
    },
)
def get_my_audio_route(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AudioFileResponse]:
    """
    Return all audio files belonging to the authenticated user.

    Ownership filtering is enforced using the authenticated user's ID.
    """
    return get_user_audio_files(
        user_id=current_user.id,
        db=db,
    )


# ---------------------------------------------------------------------------
# GET /audio/{audio_id}
# ---------------------------------------------------------------------------
#
# Registered AFTER static routes.
#
# SECURITY:
#   Ownership is enforced in the service layer.
#
# WHY 404 INSTEAD OF 403:
#   Returning 404 prevents record ID enumeration attacks by not revealing
#   whether a resource exists for another user.
# ---------------------------------------------------------------------------

@router.get(
    "/{audio_id}",
    response_model=AudioFileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get an audio file by ID",
    description="Fetch a single audio file belonging to the authenticated user.",
    response_description="Metadata for the requested audio file.",
    responses={
        200: {"description": "Audio file retrieved successfully."},
        401: {"description": "Missing or invalid JWT token."},
        404: {"description": "Audio file not found."},
        422: {"description": "audio_id must be greater than zero."},
    },
)
def get_audio_route(
    audio_id: Annotated[
        int,
        Path(
            ...,
            gt=0,
            description="The ID of the audio file to retrieve.",
        ),
    ],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AudioFileResponse:
    """
    Fetch metadata for a single audio file.

    Path validation rejects invalid primary keys before DB access.
    """
    return get_audio_by_id(
        audio_id=audio_id,
        user_id=current_user.id,
        db=db,
    )


# ---------------------------------------------------------------------------
# PATCH /audio/{audio_id}/status
# ---------------------------------------------------------------------------
#
# DOCTOR-ONLY ENDPOINT
#
# BACKEND RESPONSIBILITY:
#   Allows doctors/admin workflows to update upload processing state.
#
# FUTURE ML INTEGRATION POINT:
#   ML services/background workers may later update statuses automatically:
#
#       pending -> processing -> completed/failed
#
#   Example future integration:
#
#       # TODO: ML worker updates upload status automatically
#
# ---------------------------------------------------------------------------

@router.patch(
    "/{audio_id}/status",
    response_model=AudioFileResponse,
    status_code=status.HTTP_200_OK,
    summary="Update audio file status (doctor only)",
    description="Update the processing status of an audio upload.",
    response_description="The updated audio file metadata.",
    responses={
        200: {"description": "Audio status updated successfully."},
        401: {"description": "Missing or invalid JWT token."},
        403: {"description": "Doctor role required."},
        404: {"description": "Audio file not found."},
        422: {"description": "audio_id must be greater than zero."},
    },
)
def update_audio_status_route(
    audio_id: Annotated[
        int,
        Path(
            ...,
            gt=0,
            description="The ID of the audio file to update.",
        ),
    ],
    payload: AudioStatusResponse,
    _: User = Depends(require_doctor),
    db: Session = Depends(get_db),
) -> AudioFileResponse:
    """
    Update the processing status of an audio file.

    ROLE ENFORCEMENT:
    Only authenticated doctors can access this endpoint.
    """
    return update_audio_status(
        audio_id=audio_id,
        new_status=payload.status,
        db=db,
    )

