import uuid

import pytest
import pytest_asyncio

from models.db_models import Document, DocumentSlot, Submission
from services import claude_client, companies_house, pipeline
from services.storage import LocalStorageBackend


def _submission(**overrides) -> Submission:
    defaults = dict(id=uuid.uuid4(), founder_id=uuid.uuid4(), version=1, companies_house_number=None)
    defaults.update(overrides)
    return Submission(**defaults)


async def _document(storage, slot: DocumentSlot, filename: str, mime_type: str, contents: bytes) -> Document:
    path = f"test/{slot.value}/{filename}"
    await storage.save(path, contents)
    return Document(
        id=uuid.uuid4(), submission_id=uuid.uuid4(), slot=slot, original_filename=filename,
        mime_type=mime_type, size=len(contents), storage_path=path,
    )


async def _async_return(value):
    return value


EXTRACTION_RESULT = claude_client.CallResult(
    data={
        "company": "Acme",
        "sector": "FinTech",
        "stage": "Seed",
        "ask_amount": "£500,000",
        "use_of_funds": "Hiring",
        "traction_metrics": ["10 customers"],
        "team": ["Founder"],
        "market_size_claims": [],
        "revenue_model": "SaaS",
        "key_risks": ["No clear GTM timeline"],
    },
    input_tokens=100, output_tokens=50, latency_ms=500, raw_response={"fake": "extract"},
)

SCORE_RESULT = claude_client.CallResult(
    data={"business_fundamentals": {"score": 7, "evidence": "quote", "feedback": ["do X"]},
          "investment_case": {"score": 5, "evidence": "quote2", "feedback": ["do Y"]},
          "investor_presentation": {"score": 9, "evidence": "quote3", "feedback": ["do Z"]}},
    input_tokens=200, output_tokens=80, latency_ms=700, raw_response={"fake": "score"},
)


@pytest.fixture
def storage(tmp_path):
    return LocalStorageBackend(tmp_path)


@pytest_asyncio.fixture
async def deck_doc(storage):
    return await _document(storage, DocumentSlot.deck, "deck.pdf", "application/pdf", b"%PDF-1.4 fake")


async def test_full_pipeline_success(monkeypatch, storage, deck_doc):
    monkeypatch.setattr(claude_client, "extract_from_documents", lambda docs: _async_return(EXTRACTION_RESULT))
    monkeypatch.setattr(claude_client, "score_extraction", lambda extraction, config: _async_return(SCORE_RESULT))

    submission = _submission()
    result = await pipeline.run_pipeline(submission, [deck_doc], storage)

    assert result.error is None
    assert result.extraction is not None
    assert result.extraction.structured_json["extracted_sector"] == "FinTech"  # promoted from "sector"
    assert "sector" not in result.extraction.structured_json
    assert result.score is not None
    assert 0 <= result.score.overall_score <= 100
    assert len(result.model_calls) == 2
    assert {c.stage.value for c in result.model_calls} == {"extract", "score"}


async def test_no_readable_documents_errors_without_calling_claude(monkeypatch, storage):
    called = False

    def fail_if_called(*a, **kw):
        nonlocal called
        called = True

    monkeypatch.setattr(claude_client, "extract_from_documents", fail_if_called)

    submission = _submission()
    result = await pipeline.run_pipeline(submission, [], storage)

    assert result.error is not None
    assert result.extraction is None
    assert not called


async def test_extraction_failure_is_graceful(monkeypatch, storage, deck_doc):
    async def boom(docs):
        raise RuntimeError("API is down")

    monkeypatch.setattr(claude_client, "extract_from_documents", boom)

    submission = _submission()
    result = await pipeline.run_pipeline(submission, [deck_doc], storage)

    assert result.error is not None
    assert "Extraction failed" in result.error
    assert result.extraction is None
    assert result.score is None
    assert result.model_calls == []


async def test_scoring_failure_keeps_extraction(monkeypatch, storage, deck_doc):
    monkeypatch.setattr(claude_client, "extract_from_documents", lambda docs: _async_return(EXTRACTION_RESULT))

    async def boom(extraction, config):
        raise RuntimeError("scoring blew up")

    monkeypatch.setattr(claude_client, "score_extraction", boom)

    submission = _submission()
    result = await pipeline.run_pipeline(submission, [deck_doc], storage)

    assert result.error is not None
    assert "Scoring failed" in result.error
    assert result.extraction is not None  # extraction still kept and logged
    assert result.score is None
    assert len(result.model_calls) == 1  # only the extract call logged
    assert result.model_calls[0].stage.value == "extract"


async def test_companies_house_merged_when_number_present(monkeypatch, storage, deck_doc):
    monkeypatch.setattr(claude_client, "extract_from_documents", lambda docs: _async_return(EXTRACTION_RESULT))
    monkeypatch.setattr(claude_client, "score_extraction", lambda extraction, config: _async_return(SCORE_RESULT))

    async def fake_lookup(number):
        return companies_house.CompanyInfo(status="active", incorporation_date="2020-01-01", sic_codes=["62012"])

    monkeypatch.setattr(companies_house, "lookup_company", fake_lookup)

    submission = _submission(companies_house_number="SC123456")
    result = await pipeline.run_pipeline(submission, [deck_doc], storage)

    assert result.extraction.structured_json["companies_house"]["status"] == "active"


async def test_companies_house_failure_does_not_block_pipeline(monkeypatch, storage, deck_doc):
    monkeypatch.setattr(claude_client, "extract_from_documents", lambda docs: _async_return(EXTRACTION_RESULT))
    monkeypatch.setattr(claude_client, "score_extraction", lambda extraction, config: _async_return(SCORE_RESULT))

    async def boom(number):
        raise RuntimeError("CH API down")

    monkeypatch.setattr(companies_house, "lookup_company", boom)

    submission = _submission(companies_house_number="SC123456")
    result = await pipeline.run_pipeline(submission, [deck_doc], storage)

    assert result.error is None  # CH failure is logged, doesn't fail the submission
    assert result.score is not None
    assert "companies_house" not in result.extraction.structured_json


async def test_corrupt_document_among_valid_ones_is_skipped_not_fatal(monkeypatch, storage, deck_doc):
    corrupt_forecast = await _document(
        storage, DocumentSlot.forecast, "forecast.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", b"not a real xlsx",
    )

    monkeypatch.setattr(claude_client, "extract_from_documents", lambda docs: _async_return(EXTRACTION_RESULT))
    monkeypatch.setattr(claude_client, "score_extraction", lambda extraction, config: _async_return(SCORE_RESULT))

    submission = _submission()
    result = await pipeline.run_pipeline(submission, [deck_doc, corrupt_forecast], storage)

    # The corrupt forecast is dropped; the good deck still goes through.
    assert result.error is None
    assert result.extraction is not None
