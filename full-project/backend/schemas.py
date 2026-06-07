from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, ConfigDict

from .models import UserRole, UploadStatus


# ---------------------------------------------------------------------------
# Shared config — applied to all response schemas
# ---------------------------------------------------------------------------

class ORMBase(BaseModel):
    """Base schema with ORM mode enabled for all response models."""
    model_config = ConfigDict(from_attributes=True)


# ===========================================================================
# AUTH / USER
# ===========================================================================

class UserRegister(BaseModel):
    username: str       = Field(..., min_length=3, max_length=50)
    email:    EmailStr
    password: str       = Field(..., min_length=8)
    role:     UserRole  = UserRole.patient


class UserLogin(BaseModel):
    email:    EmailStr
    password: str = Field(..., min_length=8)


class UserResponse(ORMBase):
    id:         int
    username:   str
    email:      EmailStr
    role:       UserRole
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"


# ===========================================================================
# AUDIO FILES
# ===========================================================================

class AudioFileResponse(ORMBase):
    id:            int
    user_id:       int
    file_name:     str
    # file_path intentionally excluded — internal server path must not be exposed publicly
    upload_status: UploadStatus
    created_at:    datetime


class AudioStatusResponse(BaseModel):
    id:     int
    status: UploadStatus


class AudioStatusUpdate(BaseModel):
    status: UploadStatus


class AudioProcessResponse(BaseModel):
    id:     int
    status: UploadStatus = UploadStatus.processing


# ===========================================================================
# DIAGNOSIS
# ===========================================================================

class DiagnosisResponse(ORMBase):
    id:               int
    user_id:          int
    diagnosis_result: str
    created_at:       datetime


class DiagnosisPlaceholderResponse(BaseModel):
    diagnosis: str = "Pending ML Integration"


# Request/response models used by the Diagnosis routes
class DiagnosisCreate(BaseModel):
    diagnosis_result: str = Field(..., min_length=1)
    confidence_score: Optional[float] = None
    remarks: Optional[str] = Field(None, max_length=1000)


class DiagnosisUpdate(BaseModel):
    diagnosis_result: Optional[str] = Field(None, min_length=1)
    confidence_score: Optional[float] = None
    remarks: Optional[str] = Field(None, max_length=1000)


# ===========================================================================
# SEVERITY
# ===========================================================================

class SeverityCreate(BaseModel):
    severity_score: float        = Field(..., ge=0.0, le=10.0, description="Severity score between 0.0 and 10.0")
    severity_level: Optional[str] = Field(None, max_length=100)
    remarks:        Optional[str] = Field(None, max_length=500)


class SeverityUpdate(BaseModel):
    severity_score: Optional[float] = Field(None, ge=0.0, le=10.0)
    remarks:        Optional[str]   = Field(None, max_length=500)


class SeverityResponse(ORMBase):
    id:             int
    user_id:        int
    severity_score: float
    remarks:        Optional[str]
    created_at:     datetime


# ===========================================================================
# PROGRESSION
# ===========================================================================

class ProgressionCreate(BaseModel):
    severity_id: int
    notes:       Optional[str] = Field(None, max_length=1000)


class ProgressionUpdate(BaseModel):
    severity_id: Optional[int] = None
    notes: Optional[str] = Field(None, max_length=1000)


class ProgressionResponse(ORMBase):
    id:          int
    user_id:     int
    severity_id: int
    notes:       Optional[str]
    created_at:  datetime


# ===========================================================================
# TREATMENT
# ===========================================================================

class TreatmentCreate(BaseModel):
    medication_name: str          = Field(..., min_length=1, max_length=255)
    dosage:          str          = Field(..., min_length=1, max_length=100)
    remarks:         Optional[str] = Field(None, max_length=500)


class TreatmentUpdate(BaseModel):
    medication_name: Optional[str] = Field(None, min_length=1, max_length=255)
    dosage:          Optional[str] = Field(None, min_length=1, max_length=100)
    remarks:         Optional[str] = Field(None, max_length=500)


class TreatmentResponse(ORMBase):
    id:              int
    user_id:         int
    medication_name: str
    dosage:          str
    remarks:         Optional[str]
    created_at:      datetime


# ===========================================================================
# REPORTS
# ===========================================================================

class ReportCreate(BaseModel):
    report_title:   str = Field(..., min_length=1, max_length=255)
    report_content: str = Field(..., min_length=1, max_length=10000)


class ReportResponse(ORMBase):
    id:             int
    user_id:        int
    report_title:   str
    report_content: str
    created_at:     datetime