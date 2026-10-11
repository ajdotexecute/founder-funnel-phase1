from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.db_models import Document, DocumentSlot, Extraction, Founder, Score, Submission
from schemas.submission import DocumentSummary, DimensionScoreSummary, ExtractionSummary, ScoreSummary, SubmissionResponse

# Submission fields a founder can optionally fill in, used by compute_completeness().
COMPLETENESS_OPTIONAL_FIELDS = ("company_name", "companies_house_number", "declared_sector", "notes")


async def get_or_create_founder(db: AsyncSession, email: str) -> Founder:
    """Repeat submissions from the same email (case/whitespace-insensitive) link to one Founder."""
    normalized = email.strip().lower()
    result = await db.execute(select(Founder).where(Founder.email == normalized))
    founder = result.scalar_one_or_none()
    if founder is None:
        founder = Founder(email=normalized)
        db.add(founder)
        await db.flush()  # assigns founder.id without committing the caller's transaction
    return founder


async def next_version_for_founder(db: AsyncSession, founder_id) -> int:
    """1 for a founder's first submission, incrementing per founder thereafter."""
    result = await db.execute(select(func.max(Submission.version)).where(Submission.founder_id == founder_id))
    current_max = result.scalar()
    return (current_max or 0) + 1


def compute_completeness(submission: Submission, documents: list[Document]) -> dict:
    """
    Backend-only signal of founder seriousness — never return this to the founder,
    only to an admin view (Checkpoint 4). Derived on read rather than stored, so it
    can't drift out of sync with the fields/documents it describes.
    """
    filled_slots = {d.slot for d in documents}
    return {
        "optional_fields_filled": {
            field: bool(getattr(submission, field)) for field in COMPLETENESS_OPTIONAL_FIELDS
        },
        "document_slots_filled": {slot.value: slot in filled_slots for slot in DocumentSlot},
    }


def build_submission_response(
    submission: Submission,
    founder: Founder,
    documents: list[Document],
    extraction: Extraction | None,
    score: Score | None,
    processing_error: str | None = None,
) -> SubmissionResponse:
    extraction_summary = None
    if extraction is not None:
        data = extraction.structured_json
        extraction_summary = ExtractionSummary(
            company=data.get("company"),
            extracted_sector=data.get("extracted_sector"),
            stage=data.get("stage"),
            ask_amount=data.get("ask_amount"),
            use_of_funds=data.get("use_of_funds"),
            traction_metrics=data.get("traction_metrics", []),
            team=data.get("team", []),
            market_size_claims=data.get("market_size_claims", []),
            revenue_model=data.get("revenue_model"),
            key_risks=data.get("key_risks", []),
            companies_house=data.get("companies_house"),
        )

    score_summary = None
    if score is not None:
        score_summary = ScoreSummary(
            overall_score=score.overall_score,
            config_id=score.config_id,
            config_version=score.config_version,
            dimensions=[
                DimensionScoreSummary(id=dim_id, **dim_data) for dim_id, dim_data in score.dimension_scores.items()
            ],
        )

    return SubmissionResponse(
        id=submission.id,
        email=founder.email,
        version=submission.version,
        company_name=submission.company_name,
        declared_sector=submission.declared_sector,
        companies_house_number=submission.companies_house_number,
        notes=submission.notes,
        consent_at=submission.consent_at,
        created_at=submission.created_at,
        documents=[
            DocumentSummary(
                slot=d.slot.value, filename=d.original_filename, size=d.size, mime_type=d.mime_type
            )
            for d in documents
        ],
        extraction=extraction_summary,
        score=score_summary,
        report_url=f"/report/{submission.id}" if score is not None else None,
        processing_error=processing_error,
    )
