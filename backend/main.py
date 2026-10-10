"""
Founder Funnel — FastAPI backend (generic assessment engine, Phase A).

Extraction is still STUBBED (Checkpoint 3 replaces this). See
services/stub_extractor.py and CLAUDE.md.
"""
import uuid
from datetime import datetime

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.config import get_settings
from core.database import get_db
from core.sectors import get_sectors
from models.db_models import Document, DocumentSlot, Extraction, Submission
from schemas.submission import SubmissionResponse
from services.file_validation import MIME_TYPES, sniff_kind, validate_companies_house_number
from services.storage import get_storage_backend
from services.stub_extractor import extract_from_deck
from services.submissions import (
    STUB_SCHEMA_VERSION,
    build_submission_response,
    get_or_create_founder,
    next_version_for_founder,
)

settings = get_settings()

app = FastAPI(title=settings.app_name, version=settings.app_version)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_UPLOAD_BYTES = settings.max_upload_size_mb * 1024 * 1024
SLOTS: tuple[tuple[DocumentSlot, bool], ...] = (
    (DocumentSlot.deck, True),
    (DocumentSlot.forecast, False),
    (DocumentSlot.one_pager, False),
)


@app.get("/health")
async def health():
    return {"status": "ok", "version": settings.app_version}


@app.get("/api/config/sectors", response_model=list[str])
async def list_sectors():
    return get_sectors()


def _consent_given(raw: str | None) -> bool:
    return (raw or "").strip().lower() in ("true", "1", "on", "yes")


async def _validate_file(slot: DocumentSlot, file: UploadFile | None, required: bool, errors: dict) -> tuple[bytes, str, str] | None:
    """Returns (contents, filename, sniffed_kind) on success, or None (with `errors` populated) on failure."""
    if file is None or not file.filename:
        if required:
            errors[slot.value] = "This document is required."
        return None

    contents = await file.read()
    if len(contents) > MAX_UPLOAD_BYTES:
        errors[slot.value] = f"File too large. Maximum {settings.max_upload_size_mb}MB."
        return None

    kind = sniff_kind(contents)
    if kind is None:
        errors[slot.value] = "Unrecognised file type. Accepted: PDF, PPTX, XLSX, CSV, DOCX."
        return None

    return contents, file.filename, kind


@app.post("/api/submissions", response_model=SubmissionResponse)
async def create_submission(
    email: str = Form(...),
    company_name: str | None = Form(None),
    declared_sector: str | None = Form(None),
    companies_house_number: str | None = Form(None),
    notes: str | None = Form(None),
    consent: str | None = Form(None),
    deck: UploadFile | None = File(None),
    forecast: UploadFile | None = File(None),
    one_pager: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db),
):
    errors: dict[str, str] = {}

    if not email or "@" not in email:
        errors["email"] = "A valid email is required."

    if not _consent_given(consent):
        errors["consent"] = "You must accept the terms to continue."

    declared_sector_clean = declared_sector.strip() if declared_sector else None
    if declared_sector_clean and declared_sector_clean not in get_sectors():
        errors["declared_sector"] = "Unrecognised sector."

    ch_number_clean: str | None = None
    if companies_house_number and companies_house_number.strip():
        try:
            ch_number_clean = validate_companies_house_number(companies_house_number)
        except ValueError as e:
            errors["companies_house_number"] = str(e)

    files = {DocumentSlot.deck: deck, DocumentSlot.forecast: forecast, DocumentSlot.one_pager: one_pager}
    validated: dict[DocumentSlot, tuple[bytes, str, str]] = {}
    for slot, required in SLOTS:
        result = await _validate_file(slot, files[slot], required, errors)
        if result is not None:
            validated[slot] = result

    if errors:
        raise HTTPException(400, detail={"errors": errors})

    founder = await get_or_create_founder(db, email)
    version = await next_version_for_founder(db, founder.id)

    submission = Submission(
        founder_id=founder.id,
        version=version,
        company_name=company_name,
        declared_sector=declared_sector_clean,
        companies_house_number=ch_number_clean,
        notes=notes,
        consent_at=datetime.utcnow(),
    )
    db.add(submission)
    await db.flush()  # assigns submission.id for the Document/Extraction FKs below

    storage = get_storage_backend()
    documents: list[Document] = []
    for slot, (contents, filename, kind) in validated.items():
        storage_key = f"{submission.id}/{slot.value}/{uuid.uuid4()}_{filename}"
        await storage.save(storage_key, contents)

        document = Document(
            submission_id=submission.id,
            slot=slot,
            original_filename=filename,
            mime_type=MIME_TYPES[kind],
            size=len(contents),
            storage_path=storage_key,
        )
        db.add(document)
        documents.append(document)

    deck_filename = validated[DocumentSlot.deck][1] if DocumentSlot.deck in validated else None
    extracted = extract_from_deck(deck_filename)
    db.add(Extraction(submission_id=submission.id, structured_json=extracted, schema_version=STUB_SCHEMA_VERSION))

    await db.commit()

    return build_submission_response(submission, founder, documents, extracted)


@app.get("/api/submissions/{submission_id}", response_model=SubmissionResponse)
async def get_submission(submission_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Submission)
        .options(
            selectinload(Submission.founder),
            selectinload(Submission.documents),
            selectinload(Submission.extractions),
        )
        .where(Submission.id == submission_id)
    )
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(404, "Submission not found")

    latest_extraction = max(submission.extractions, key=lambda e: e.created_at, default=None)
    extracted = latest_extraction.structured_json if latest_extraction else {}

    return build_submission_response(submission, submission.founder, submission.documents, extracted)
