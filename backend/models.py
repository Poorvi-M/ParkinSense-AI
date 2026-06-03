import enum
from datetime import datetime
from typing import List, Optional

from sqlalchemy import Enum, ForeignKey, String, Text, Float, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class UserRole(str, enum.Enum):
    patient = "patient"
    doctor  = "doctor"


class UploadStatus(str, enum.Enum):
    pending    = "pending"
    processing = "processing"
    completed  = "completed"
    failed     = "failed"


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id:              Mapped[int]      = mapped_column(Integer, primary_key=True, index=True)
    username:        Mapped[str]      = mapped_column(String(50), unique=True, nullable=False, index=True)
    email:           Mapped[str]      = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str]      = mapped_column(String(255), nullable=False)
    role:            Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False, default=UserRole.patient)
    created_at:      Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships — cascade="all, delete-orphan" ensures dependent records
    # are deleted automatically when a User is deleted.
    audio_files:  Mapped[List["AudioFile"]]   = relationship("AudioFile",   back_populates="user", cascade="all, delete-orphan")
    diagnoses:    Mapped[List["Diagnosis"]]   = relationship("Diagnosis",   back_populates="user", cascade="all, delete-orphan")
    severities:   Mapped[List["Severity"]]    = relationship("Severity",    back_populates="user", cascade="all, delete-orphan")
    progressions: Mapped[List["Progression"]] = relationship("Progression", back_populates="user", cascade="all, delete-orphan")
    treatments:   Mapped[List["Treatment"]]   = relationship("Treatment",   back_populates="user", cascade="all, delete-orphan")
    reports:      Mapped[List["Report"]]      = relationship("Report",      back_populates="user", cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# AudioFile
# ---------------------------------------------------------------------------

class AudioFile(Base):
    __tablename__ = "audio_files"

    id:            Mapped[int]          = mapped_column(Integer, primary_key=True, index=True)
    user_id:       Mapped[int]          = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    file_name:     Mapped[str]          = mapped_column(String(255), nullable=False)
    file_path:     Mapped[str]          = mapped_column(String(500), nullable=False)
    upload_status: Mapped[UploadStatus] = mapped_column(Enum(UploadStatus), nullable=False, default=UploadStatus.pending)
    created_at:    Mapped[datetime]     = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="audio_files")


# ---------------------------------------------------------------------------
# Diagnosis
# ---------------------------------------------------------------------------

class Diagnosis(Base):
    __tablename__ = "diagnoses"

    id:               Mapped[int]      = mapped_column(Integer, primary_key=True, index=True)
    user_id:          Mapped[int]      = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    diagnosis_result: Mapped[str]      = mapped_column(Text, nullable=False, default="Pending ML Integration")
    created_at:       Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="diagnoses")


# ---------------------------------------------------------------------------
# Severity
# ---------------------------------------------------------------------------

class Severity(Base):
    __tablename__ = "severities"

    id:             Mapped[int]           = mapped_column(Integer, primary_key=True, index=True)
    user_id:        Mapped[int]           = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    severity_score: Mapped[float]         = mapped_column(Float, nullable=False)
    remarks:        Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at:     Mapped[datetime]      = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="severities")
    # cascade="all, delete-orphan" — deleting a Severity record removes its
    # linked Progression records, enforcing the non-nullable FK constraint.
    progressions: Mapped[List["Progression"]] = relationship("Progression", back_populates="severity", cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# Progression
# ---------------------------------------------------------------------------

class Progression(Base):
    __tablename__ = "progressions"

    id:          Mapped[int]           = mapped_column(Integer, primary_key=True, index=True)
    user_id:     Mapped[int]           = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    severity_id: Mapped[int]           = mapped_column(Integer, ForeignKey("severities.id", ondelete="CASCADE"), nullable=False, index=True)
    notes:       Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at:  Mapped[datetime]      = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Direct relationships to both User and Severity
    user:     Mapped["User"]     = relationship("User",     back_populates="progressions")
    severity: Mapped["Severity"] = relationship("Severity", back_populates="progressions")


# ---------------------------------------------------------------------------
# Treatment
# ---------------------------------------------------------------------------

class Treatment(Base):
    __tablename__ = "treatments"

    id:              Mapped[int]           = mapped_column(Integer, primary_key=True, index=True)
    user_id:         Mapped[int]           = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    medication_name: Mapped[str]           = mapped_column(String(255), nullable=False)
    dosage:          Mapped[str]           = mapped_column(String(100), nullable=False)
    remarks:         Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at:      Mapped[datetime]      = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="treatments")


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

class Report(Base):
    __tablename__ = "reports"

    id:             Mapped[int]      = mapped_column(Integer, primary_key=True, index=True)
    user_id:        Mapped[int]      = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    report_title:   Mapped[str]      = mapped_column(String(255), nullable=False)
    report_content: Mapped[str]      = mapped_column(Text, nullable=False)
    created_at:     Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="reports")