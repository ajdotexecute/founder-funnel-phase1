import uuid
from datetime import datetime
from typing import Literal

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


class CompaniesHousePanel(BaseModel):
    """
    Always present on the response, never an error state — "not_checked" covers
    no number given, no API key configured, and a failed/not-found lookup alike,
    per the brief: never show an error, just a friendly not-checked state.
    """

    status: Literal["verified", "not_checked"] = "not_checked"
    company_name: str | None = None
    company_status: str | None = None
    incorporation_date: str | None = None
    sic_codes: list[str] = []


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
    companies_house: CompaniesHousePanel = CompaniesHousePanel()
    report_url: str | None = None
    processing_error: str | None = None

    class Config:
        from_attributes = True
