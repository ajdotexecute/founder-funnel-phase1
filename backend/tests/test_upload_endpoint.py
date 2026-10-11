"""
Every test that reaches a valid, non-rejected submission mocks services.pipeline
.run_pipeline — none of these tests ever call the real Claude API.
"""
import uuid

import httpx
import pytest
from sqlalchemy import delete, select

import main
from models.db_models import Document, Extraction, Founder, ModelCall, Score, Submission
from services import pipeline
from services.pipeline import PipelineResult
from services.storage import get_storage_backend

PDF_BYTES = b"%PDF-1.4 test deck content"

FAKE_EXTRACTION_DATA = {
    "company": "Test Co",
    "extracted_sector": "Deep Tech",
    "stage": "Seed",
    "ask_amount": "£500,000",
    "use_of_funds": "Hiring",
    "traction_metrics": ["10 customers"],
    "team": ["Founder"],
    "market_size_claims": [],
    "revenue_model": "SaaS",
    "key_risks": ["No clear GTM timeline"],
}


def _fake_pipeline_result(submission_id) -> PipelineResult:
    extraction = Extraction(submission_id=submission_id, structured_json=FAKE_EXTRACTION_DATA, schema_version="2")
    score = Score(
        submission_id=submission_id,
        config_id="demo",
        config_version="1",
        dimension_scores={
            "business_fundamentals": {"name": "Business fundamentals", "score": 7, "label": "Developing", "rag": "amber", "evidence": "x", "feedback": ["y"]},
            "investment_case": {"name": "Investment case", "score": 5, "label": "Developing", "rag": "amber", "evidence": "x", "feedback": ["y"]},
            "investor_presentation": {"name": "Investor presentation", "score": 9, "label": "Strong", "rag": "green", "evidence": "x", "feedback": ["y"]},
        },
        overall_score=55.6,
    )
    return PipelineResult(extraction=extraction, score=score, model_calls=[])


@pytest.fixture
async def client():
    transport = httpx.ASGITransport(app=main.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture(autouse=True)
def mock_pipeline(monkeypatch):
    """
    Safety net as much as convenience: every test in this file gets a mocked
    pipeline by default, so a new test can't accidentally reach the real Claude
    API just by forgetting to mock it. Tests that want pipeline failure behaviour
    override this via monkeypatch within the test itself.
    """
    async def fake_run_pipeline(submission, documents, storage):
        return _fake_pipeline_result(submission.id)

    monkeypatch.setattr(pipeline, "run_pipeline", fake_run_pipeline)
    monkeypatch.setattr(main, "run_pipeline", fake_run_pipeline)


async def _cleanup(db_session, founder_id):
    sub_ids = (
        await db_session.execute(select(Submission.id).where(Submission.founder_id == founder_id))
    ).scalars().all()
    if sub_ids:
        await db_session.execute(delete(Document).where(Document.submission_id.in_(sub_ids)))
        await db_session.execute(delete(Extraction).where(Extraction.submission_id.in_(sub_ids)))
        await db_session.execute(delete(Score).where(Score.submission_id.in_(sub_ids)))
        await db_session.execute(delete(ModelCall).where(ModelCall.submission_id.in_(sub_ids)))
        await db_session.execute(delete(Submission).where(Submission.id.in_(sub_ids)))
    await db_session.execute(delete(Founder).where(Founder.id == founder_id))
    await db_session.commit()

    storage = get_storage_backend()
    for sub_id in sub_ids:
        for key in await storage.list(f"{sub_id}/"):
            await storage.delete(key)


async def test_missing_deck_and_consent_reports_both_errors(client):
    res = await client.post("/api/submissions", data={"email": "cp3-missing@example.com"})
    assert res.status_code == 400
    errors = res.json()["detail"]["errors"]
    assert "deck" in errors
    assert "consent" in errors


async def test_invalid_companies_house_number_rejected(client):
    res = await client.post(
        "/api/submissions",
        data={"email": "cp3-ch@example.com", "consent": "true", "companies_house_number": "NOTVALID"},
        files={"deck": ("deck.pdf", PDF_BYTES, "application/pdf")},
    )
    assert res.status_code == 400
    assert "companies_house_number" in res.json()["detail"]["errors"]


async def test_unrecognised_declared_sector_rejected(client):
    res = await client.post(
        "/api/submissions",
        data={"email": "cp3-sector@example.com", "consent": "true", "declared_sector": "Not A Real Sector"},
        files={"deck": ("deck.pdf", PDF_BYTES, "application/pdf")},
    )
    assert res.status_code == 400
    assert "declared_sector" in res.json()["detail"]["errors"]


async def test_deck_content_mismatch_rejected(client):
    res = await client.post(
        "/api/submissions",
        data={"email": "cp3-mismatch@example.com", "consent": "true"},
        files={"deck": ("deck.pdf", b"not actually a pdf", "application/pdf")},
    )
    assert res.status_code == 400
    assert "deck" in res.json()["detail"]["errors"]


async def test_full_submission_and_get_round_trip(client, db_session):
    email = f"cp3-{uuid.uuid4().hex[:8]}@example.com"
    try:
        res = await client.post(
            "/api/submissions",
            data={
                "email": email,
                "company_name": "Test Co",
                "declared_sector": "FinTech",
                "companies_house_number": "sc123456",
                "notes": "hello",
                "consent": "true",
            },
            files={"deck": ("deck.pdf", PDF_BYTES, "application/pdf")},
        )
        assert res.status_code == 200
        body = res.json()
        assert body["email"] == email
        assert body["version"] == 1
        assert body["declared_sector"] == "FinTech"
        assert body["companies_house_number"] == "SC123456"
        assert body["consent_at"] is not None
        assert [d["slot"] for d in body["documents"]] == ["deck"]
        # extraction-derived field, distinct from declared_sector (mocked pipeline result)
        assert body["extraction"]["extracted_sector"] == "Deep Tech"
        assert body["score"]["overall_score"] == 55.6
        assert body["report_url"] == f"/report/{body['id']}"
        assert body["processing_error"] is None

        get_res = await client.get(f"/api/submissions/{body['id']}")
        assert get_res.status_code == 200
        assert get_res.json()["id"] == body["id"]
    finally:
        result = await db_session.execute(select(Founder).where(Founder.email == email))
        founder = result.scalar_one_or_none()
        if founder:
            await _cleanup(db_session, founder.id)


async def test_pipeline_failure_still_returns_the_submission(client, db_session, monkeypatch):
    """A Claude/AI failure must not 500 the whole request — the submission itself succeeded."""
    email = f"cp3-pipefail-{uuid.uuid4().hex[:8]}@example.com"

    async def failing_pipeline(submission, documents, storage):
        return PipelineResult(error="Extraction failed: simulated outage")

    monkeypatch.setattr(main, "run_pipeline", failing_pipeline)

    try:
        res = await client.post(
            "/api/submissions",
            data={"email": email, "consent": "true"},
            files={"deck": ("deck.pdf", PDF_BYTES, "application/pdf")},
        )
        assert res.status_code == 200
        body = res.json()
        assert body["extraction"] is None
        assert body["score"] is None
        assert body["report_url"] is None
        assert "simulated outage" in body["processing_error"]
    finally:
        result = await db_session.execute(select(Founder).where(Founder.email == email))
        founder = result.scalar_one_or_none()
        if founder:
            await _cleanup(db_session, founder.id)


async def test_get_nonexistent_uuid_is_404(client):
    res = await client.get(f"/api/submissions/{uuid.uuid4()}")
    assert res.status_code == 404


async def test_get_malformed_id_is_422(client):
    res = await client.get("/api/submissions/not-a-uuid")
    assert res.status_code == 422


async def test_report_html_renders_for_scored_submission(client, db_session):
    email = f"cp3-report-{uuid.uuid4().hex[:8]}@example.com"
    try:
        res = await client.post(
            "/api/submissions",
            data={"email": email, "company_name": "Report Co", "consent": "true"},
            files={"deck": ("deck.pdf", PDF_BYTES, "application/pdf")},
        )
        submission_id = res.json()["id"]

        report_res = await client.get(f"/report/{submission_id}")
        assert report_res.status_code == 200
        assert "Report Co" in report_res.text
        assert "55.6" in report_res.text
    finally:
        result = await db_session.execute(select(Founder).where(Founder.email == email))
        founder = result.scalar_one_or_none()
        if founder:
            await _cleanup(db_session, founder.id)


async def test_report_html_404s_when_no_score_exists(client, db_session, monkeypatch):
    email = f"cp3-noreport-{uuid.uuid4().hex[:8]}@example.com"

    async def no_score_pipeline(submission, documents, storage):
        return PipelineResult(error="no key configured")

    monkeypatch.setattr(main, "run_pipeline", no_score_pipeline)

    try:
        res = await client.post(
            "/api/submissions",
            data={"email": email, "consent": "true"},
            files={"deck": ("deck.pdf", PDF_BYTES, "application/pdf")},
        )
        submission_id = res.json()["id"]

        report_res = await client.get(f"/report/{submission_id}")
        assert report_res.status_code == 404
    finally:
        result = await db_session.execute(select(Founder).where(Founder.email == email))
        founder = result.scalar_one_or_none()
        if founder:
            await _cleanup(db_session, founder.id)
