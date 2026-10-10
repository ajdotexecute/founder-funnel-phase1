import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class Founder(Base):
    """One row per unique email. Repeat submissions from the same email link here."""

    __tablename__ = "founders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    submissions: Mapped[list["Submission"]] = relationship(back_populates="founder")


class Submission(Base):
    """One assessment attempt. `version` increments per founder, oldest first starting at 1."""

    __tablename__ = "submissions"
    __table_args__ = (UniqueConstraint("founder_id", "version", name="uq_submissions_founder_version"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    founder_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("founders.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)

    company_name: Mapped[str | None] = mapped_column(String(255))
    companies_house_number: Mapped[str | None] = mapped_column(String(20))
    # Founder-selected category from core/sectors.py's config list. Distinct from
    # Extraction.structured_json["extracted_sector"], which is whatever sector the AI
    # extraction reads off the deck itself — the two can disagree.
    declared_sector: Mapped[str | None] = mapped_column(String(100))
    notes: Mapped[str | None] = mapped_column(Text)
    consent_at: Mapped[datetime | None] = mapped_column(DateTime)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    founder: Mapped["Founder"] = relationship(back_populates="submissions")
    documents: Mapped[list["Document"]] = relationship(back_populates="submission")
    extractions: Mapped[list["Extraction"]] = relationship(back_populates="submission")
    scores: Mapped[list["Score"]] = relationship(back_populates="submission")


class DocumentSlot(str, enum.Enum):
    deck = "deck"
    forecast = "forecast"
    one_pager = "one_pager"


class Document(Base):
    """One uploaded file per (submission, slot) — at most one deck, one forecast, one one-pager."""

    __tablename__ = "documents"
    __table_args__ = (UniqueConstraint("submission_id", "slot", name="uq_documents_submission_slot"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submission_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("submissions.id"), index=True)
    slot: Mapped[DocumentSlot] = mapped_column(SAEnum(DocumentSlot, name="document_slot"))
    original_filename: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(127))
    size: Mapped[int] = mapped_column(Integer)
    # A storage-backend-relative key (e.g. "<submission_id>/deck/<uuid>_<filename>"), not
    # a filesystem path — see services/storage.py. Resolved via StorageBackend.open().
    storage_path: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    submission: Mapped["Submission"] = relationship(back_populates="documents")


class Extraction(Base):
    """A structured read of a submission's documents. See services/stub_extractor.py — still stubbed."""

    __tablename__ = "extractions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submission_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("submissions.id"), index=True)
    structured_json: Mapped[dict] = mapped_column(JSONB)
    schema_version: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    submission: Mapped["Submission"] = relationship(back_populates="extractions")


class Score(Base):
    """Output of scoring an extraction against a named, versioned config. Not populated until Checkpoint 3."""

    __tablename__ = "scores"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submission_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("submissions.id"), index=True)
    config_id: Mapped[str] = mapped_column(String(100))
    config_version: Mapped[str] = mapped_column(String(20))
    dimension_scores: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    submission: Mapped["Submission"] = relationship(back_populates="scores")
