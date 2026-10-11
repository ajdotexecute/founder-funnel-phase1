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


class MarketSizeClaim(BaseModel):
    claim: str
    stated_basis: str


class ExtractionSummary(BaseModel):
    company: str | None = None
    extracted_sector: str | None = None
    stage: str | None = None
    ask_amount: str | None = None
    use_of_funds: str | None = None
    traction_metrics: list[str] = []
    team: list[str] = []
    market_size_claims: list[MarketSizeClaim] = []
    revenue_model: str | None = None
    key_risks: list[str] = []
    companies_house: dict | None = None


class DimensionScoreSummary(BaseModel):
    id: str
    name: str
    score: int
    label: str
    rag: str
    evidence: str
    feedback: list[str]


class ScoreSummary(BaseModel):
    overall_score: float
    config_id: str
    config_version: str
    dimensions: list[DimensionScoreSummary]


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

    extraction: ExtractionSummary | None = None
    score: ScoreSummary | None = None
    report_url: str | None = None
    processing_error: str | None = None

    class Config:
        from_attributes = True
