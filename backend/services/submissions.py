from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.db_models import Document, DocumentSlot, Founder, Submission
from schemas.submission import DocumentSummary, SubmissionResponse

# Identifies the shape of Extraction.structured_json. "1" is the Phase 1/Checkpoint 2
# stub shape (company_name, extracted_sector, industry, raise_amount, gap_flags,
# raising_raw) — see services/stub_extractor.py. Checkpoint 3's real extraction
# schema is a different shape and should bump this.
STUB_SCHEMA_VERSION = "1"

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
    submission: Submission, founder: Founder, documents: list[Document], extracted: dict
) -> SubmissionResponse:
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
        extracted_sector=extracted.get("extracted_sector"),
        extracted_industry=extracted.get("industry"),
        raise_amount=extracted.get("raise_amount"),
        gap_flags=extracted.get("gap_flags", []),
        raising_raw=extracted.get("raising_raw"),
    )
