import uuid
from datetime import datetime

from pydantic import BaseModel


class SubmissionResponse(BaseModel):
    id: uuid.UUID
    email: str
    company_name: str | None
    deck_filename: str | None
    sector: str | None
    industry: str | None
    raise_amount: str | None
    gap_flags: list[str]
    raising_raw: str | None
    created_at: datetime

    class Config:
        from_attributes = True
