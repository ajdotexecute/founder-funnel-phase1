import uuid

import httpx
import pytest
from sqlalchemy import delete, select

import main
from models.db_models import Document, Extraction, Founder, Submission
from services.storage import get_storage_backend

PDF_BYTES = b"%PDF-1.4 test deck content"


@pytest.fixture
async def client():
    transport = httpx.ASGITransport(app=main.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _cleanup(db_session, founder_id):
    sub_ids = (
        await db_session.execute(select(Submission.id).where(Submission.founder_id == founder_id))
    ).scalars().all()
    if sub_ids:
        await db_session.execute(delete(Document).where(Document.submission_id.in_(sub_ids)))
        await db_session.execute(delete(Extraction).where(Extraction.submission_id.in_(sub_ids)))
        await db_session.execute(delete(Submission).where(Submission.id.in_(sub_ids)))
    await db_session.execute(delete(Founder).where(Founder.id == founder_id))
    await db_session.commit()

    storage = get_storage_backend()
    for sub_id in sub_ids:
        for key in await storage.list(f"{sub_id}/"):
            await storage.delete(key)


async def test_missing_deck_and_consent_reports_both_errors(client):
    res = await client.post("/api/submissions", data={"email": "cp2-missing@example.com"})
    assert res.status_code == 400
    errors = res.json()["detail"]["errors"]
    assert "deck" in errors
    assert "consent" in errors


async def test_invalid_companies_house_number_rejected(client):
    res = await client.post(
        "/api/submissions",
        data={"email": "cp2-ch@example.com", "consent": "true", "companies_house_number": "NOTVALID"},
        files={"deck": ("deck.pdf", PDF_BYTES, "application/pdf")},
    )
    assert res.status_code == 400
    assert "companies_house_number" in res.json()["detail"]["errors"]


async def test_unrecognised_declared_sector_rejected(client):
    res = await client.post(
        "/api/submissions",
        data={"email": "cp2-sector@example.com", "consent": "true", "declared_sector": "Not A Real Sector"},
        files={"deck": ("deck.pdf", PDF_BYTES, "application/pdf")},
    )
    assert res.status_code == 400
    assert "declared_sector" in res.json()["detail"]["errors"]


async def test_deck_content_mismatch_rejected(client):
    res = await client.post(
        "/api/submissions",
        data={"email": "cp2-mismatch@example.com", "consent": "true"},
        files={"deck": ("deck.pdf", b"not actually a pdf", "application/pdf")},
    )
    assert res.status_code == 400
    assert "deck" in res.json()["detail"]["errors"]


async def test_full_submission_and_get_round_trip(client, db_session):
    email = f"cp2-{uuid.uuid4().hex[:8]}@example.com"
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
        # extraction-derived field, distinct from declared_sector
        assert body["extracted_sector"] == "Deep Tech"

        get_res = await client.get(f"/api/submissions/{body['id']}")
        assert get_res.status_code == 200
        assert get_res.json()["id"] == body["id"]
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
