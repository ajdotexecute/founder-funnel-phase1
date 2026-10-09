"""
Founder Funnel — FastAPI backend (generic assessment engine, Phase A).

Extraction is still STUBBED (Checkpoint 3 replaces this). See
services/stub_extractor.py and CLAUDE.md.

Schema is now normalised across founders/submissions/documents/extractions/scores
(see models/db_models.py) and managed by Alembic — see alembic/ and CLAUDE.md for
how to run migrations. These two endpoints keep the Phase 1 response shape so the
current frontend doesn't break; Checkpoint 2 reworks the upload flow and response
properly.
"""
import uuid
from pathlib import Path

import aiofiles
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.config import get_settings
from core.database import get_db
from models.db_models import Document, DocumentSlot, Extraction, Submission
from schemas.submission import SubmissionResponse
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

UPLOAD_DIR = Path(settings.upload_dir)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/health")
async def health():
    return {"status": "ok", "version": settings.app_version}


@app.post("/api/submissions", response_model=SubmissionResponse)
async def create_submission(
    email: str = Form(...),
    company_name: str | None = Form(None),
    deck: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Accepts an optional deck upload plus a required email. Any PDF is
    accepted — its content is never parsed; see services/stub_extractor.py.
    """
    if not email or "@" not in email:
        raise HTTPException(400, "A valid email is required.")

    deck_contents: bytes | None = None
    deck_filename: str | None = None
    if deck is not None:
        deck_contents = await deck.read()
        max_size = settings.max_upload_size_mb * 1024 * 1024
        if len(deck_contents) > max_size:
            raise HTTPException(400, f"File too large. Maximum {settings.max_upload_size_mb}MB.")
        deck_filename = deck.filename

    founder = await get_or_create_founder(db, email)
    version = await next_version_for_founder(db, founder.id)

    submission = Submission(founder_id=founder.id, version=version, company_name=company_name)
    db.add(submission)
    await db.flush()  # assigns submission.id for the Document/Extraction FKs below

    if deck_contents is not None:
        file_path = UPLOAD_DIR / f"{uuid.uuid4()}_{deck_filename}"
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(deck_contents)

        db.add(
            Document(
                submission_id=submission.id,
                slot=DocumentSlot.deck,
                original_filename=deck_filename,
                mime_type=deck.content_type or "application/octet-stream",
                size=len(deck_contents),
                storage_path=str(file_path),
            )
        )

    extracted = extract_from_deck(deck_filename)
    db.add(Extraction(submission_id=submission.id, structured_json=extracted, schema_version=STUB_SCHEMA_VERSION))

    await db.commit()

    return build_submission_response(submission, founder, deck_filename, extracted)


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

    deck_doc = next((d for d in submission.documents if d.slot == DocumentSlot.deck), None)
    latest_extraction = max(submission.extractions, key=lambda e: e.created_at, default=None)
    extracted = latest_extraction.structured_json if latest_extraction else {}

    return build_submission_response(
        submission, submission.founder, deck_doc.original_filename if deck_doc else None, extracted
    )
