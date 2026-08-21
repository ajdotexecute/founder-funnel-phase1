"""
Founder Funnel — FastAPI backend (Phase 1 discovery prototype).

Extraction is STUBBED. See services/stub_extractor.py and CLAUDE.md.
"""
import uuid
from pathlib import Path

import aiofiles
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from core.database import Base, engine, get_db
from models.db_models import Submission
from schemas.submission import SubmissionResponse
from services.stub_extractor import extract_from_deck

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


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


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

    deck_filename = None
    if deck is not None:
        contents = await deck.read()
        max_size = settings.max_upload_size_mb * 1024 * 1024
        if len(contents) > max_size:
            raise HTTPException(400, f"File too large. Maximum {settings.max_upload_size_mb}MB.")

        deck_filename = deck.filename
        file_path = UPLOAD_DIR / f"{uuid.uuid4()}_{deck_filename}"
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(contents)

    extracted = extract_from_deck(deck_filename)

    submission = Submission(
        email=email,
        company_name=company_name,
        deck_filename=deck_filename,
        sector=extracted["sector"],
        industry=extracted["industry"],
        raise_amount=extracted["raise_amount"],
        gap_flags=extracted["gap_flags"],
        raising_raw=extracted["raising_raw"],
    )
    db.add(submission)
    await db.commit()
    await db.refresh(submission)

    return submission


@app.get("/api/submissions/{submission_id}", response_model=SubmissionResponse)
async def get_submission(submission_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Submission).where(Submission.id == submission_id))
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(404, "Submission not found")
    return submission
