import os
import re
import uuid

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from config import settings
from models import AudioFile, UploadStatus


# ---------------------------------------------------------------------------
# Allowed file types
# ---------------------------------------------------------------------------

ALLOWED_EXTENSIONS = {".wav", ".mp3"}
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB hard limit


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _validate_audio_file(file: UploadFile) -> str:
    """
    Validate file extension and return the lowercased extension.

    Raises:
        HTTP 400 -- if the file extension is not .wav or .mp3
    """
    filename = file.filename or ""
    _, ext = os.path.splitext(filename.lower())

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type '{ext}'. Only .wav and .mp3 files are accepted.",
        )

    return ext


def _sanitize_filename(filename: str) -> str:
    """
    Sanitize an uploaded filename for safe storage on disk.

    Steps:
        1. Strip directory components -- prevents path traversal attacks
           e.g. "../../etc/passwd.wav" becomes "passwd.wav"
        2. Replace spaces with underscores -- avoids shell/URL edge cases
        3. Strip characters outside [a-zA-Z0-9._-] -- removes shell
           metacharacters, null bytes, and other dangerous sequences
        4. Fall back to "upload" if sanitization leaves an empty stem

    Returns:
        A safe, normalized filename string (extension preserved).
    """
    # 1. Strip any directory components (path traversal defence)
    filename = os.path.basename(filename)

    # 2. Replace spaces with underscores
    filename = filename.replace(" ", "_")

    # 3. Strip characters outside the safe set
    filename = re.sub(r"[^\w.\-]", "", filename)

    # 4. Guard against an empty result after sanitization
    stem, ext = os.path.splitext(filename)
    if not stem:
        stem = "upload"

    return f"{stem}{ext}"


def _build_unique_filename(user_id: int, original_filename: str) -> str:
    """
    Build a collision-resistant filename using a UUID.

    Format: {user_id}_{uuid4}_{safe_filename}

    Example: 42_3f2a1b4c-..._voice_sample.wav

    - user_id prefix    -- groups files by user for easy inspection
    - uuid4 segment     -- guarantees global uniqueness (no DB lookup needed)
    - safe_filename     -- human-readable, sanitized original name
    """
    safe_filename  = _sanitize_filename(original_filename)
    unique_segment = uuid.uuid4()
    return f"{user_id}_{unique_segment}_{safe_filename}"


def _ensure_upload_dir() -> str:
    """
    Ensure the upload directory exists, creating it if necessary.
    Returns the absolute path to the upload directory.
    """
    upload_dir = os.path.abspath(settings.UPLOAD_DIR)
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir

def _save_file_to_disk(file: UploadFile, dest_path: str) -> int:
    """
    Stream the uploaded file to disk and return the number of bytes written.

    Raises:
        HTTP 400 -- if the file exceeds MAX_FILE_SIZE_BYTES
        HTTP 500 -- if the file cannot be written to disk
    """
    bytes_written = 0

    try:
        with open(dest_path, "wb") as buffer:
            while True:
                chunk = file.file.read(1024 * 64)  # 64 KB chunks

                if not chunk:
                    break

                bytes_written += len(chunk)

                if bytes_written > MAX_FILE_SIZE_BYTES:
                    buffer.close()

                    if os.path.exists(dest_path):
                        os.remove(dest_path)

                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            "File exceeds the maximum allowed size "
                            f"of {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB."
                        ),
                    )

                buffer.write(chunk)

    except HTTPException:
        raise

    except Exception:
        # Clean up partial file on unexpected write failure
        if os.path.exists(dest_path):
            os.remove(dest_path)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save the uploaded file. Please try again.",
        )

    finally:
        # Prevent file descriptor leaks
        file.file.close()

    return bytes_written



# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------

def upload_audio(
    file:    UploadFile,
    user_id: int,
    db:      Session,
) -> AudioFile:
    """
    Validate, save, and register an audio file upload.

    Steps:
        1. Validate file extension (.wav / .mp3 only)
        2. Ensure upload directory exists
        3. Sanitize filename and generate a UUID-based unique name
           Format: {user_id}_{uuid4}_{safe_filename}
        4. Stream file to disk with size enforcement (50 MB max)
        5. Persist metadata to the database
        6. Return the saved AudioFile ORM object

    Raises:
        HTTP 400 -- invalid file type or file too large
        HTTP 500 -- disk write failure
    """
    _validate_audio_file(file)

    upload_dir = _ensure_upload_dir()

    # Build a secure, unique filename -- safe against path traversal and collisions
    original_filename = _sanitize_filename(file.filename or "upload")

    stored_filename = _build_unique_filename(
    user_id,
    original_filename,
)
    dest_path= os.path.join(upload_dir, stored_filename)

    _save_file_to_disk(file, dest_path)

    audio_record = AudioFile(
        user_id       = user_id,
        file_name=original_filename,      # Original name preserved for display
        file_path     = dest_path,          # Stored internally; never exposed via API
        upload_status = UploadStatus.pending,
    )

    db.add(audio_record)
    db.commit()
    db.refresh(audio_record)

    return audio_record


def get_audio_by_id(audio_id: int, user_id: int, db: Session) -> AudioFile:
    """
    Fetch a single AudioFile record by ID.

    Enforces ownership -- a user can only retrieve their own audio files.

    Raises:
        HTTP 404 -- if the record does not exist or belongs to another user
    """
    audio = (
        db.query(AudioFile)
        .filter(AudioFile.id == audio_id, AudioFile.user_id == user_id)
        .first()
    )

    if audio is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audio file with ID {audio_id} was not found.",
        )

    return audio


def process_audio(audio_id: int, user_id: int, db: Session) -> AudioFile:
    """
    ML processing placeholder.

    Marks the audio file status as 'processing' and saves it to the database.
    No actual ML is performed -- this is a stub for future ML integration.

    Raises:
        HTTP 404 -- if the audio record does not exist or belongs to another user
        HTTP 400 -- if the file is already processing or completed
    """
    audio = get_audio_by_id(audio_id, user_id, db)

    if audio.upload_status in (UploadStatus.processing, UploadStatus.completed):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Audio file is already in '{audio.upload_status.value}' status.",
        )

    audio.upload_status = UploadStatus.processing
    db.commit()
    db.refresh(audio)

    return audio


def get_audio_status(audio_id: int, user_id: int, db: Session) -> AudioFile:
    """
    Return the current processing status of an audio file.

    Enforces ownership -- a user can only check status of their own files.

    Raises:
        HTTP 404 -- if the record does not exist or belongs to another user
    """
    return get_audio_by_id(audio_id, user_id, db)