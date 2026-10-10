import uuid
from datetime import datetime

from pydantic import BaseModel


class DocumentSummary(BaseModel):
    slot: str
    filename: str
    size: int
    mime_type: str

    class Config:
        from_attributes = True


class SubmissionResponse(BaseModel):
    id: uuid.UUID
    email: str
    version: int
    company_name: str | None
    declared_sector: str | None
    companies_house_number: str | None
    notes: str | None
    consent_at: datetime | None
    created_at: datetime
    documents: list[DocumentSummary]

    # Still from the stub extraction (Checkpoint 3 replaces this) — distinct from
    # declared_sector above, see Submission.declared_sector's comment.
    extracted_sector: str | None
    extracted_industry: str | None
    raise_amount: str | None
    gap_flags: list[str]
    raising_raw: str | None

    class Config:
        from_attributes = True
