"""
Every test here mocks services.claude_client._create_message directly — no
network call to Anthropic ever happens. Per the brief: build and test
everything with the Claude call mocked; the one live run is the user's own,
on their own machine, with their own key.
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock

import anthropic
import httpx
import pytest

from services import claude_client
from services.claude_client import DocBlock
from services.scoring_schema import ScoringConfig

DEMO_CONFIG = ScoringConfig.model_validate(
    {
        "id": "demo",
        "version": "1",
        "name": "Demo",
        "scale": {"min": 1, "max": 10},
        "dimensions": [
            {
                "id": "business_fundamentals",
                "name": "Business fundamentals",
                "description": "x",
                "weight": 1,
                "rubric": [{"min_score": 1, "max_score": 10, "label": "Any", "description": "x"}],
                "rag_thresholds": {"red_max": 4, "amber_max": 7},
            }
        ],
        "cta_text": "Talk to us.",
    }
)


def _fake_response(tool_input: dict, input_tokens=100, output_tokens=50):
    return SimpleNamespace(
        content=[SimpleNamespace(type="tool_use", input=tool_input)],
        usage=SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens),
        model_dump=lambda mode="json": {"fake": "response"},
    )


@pytest.fixture(autouse=True)
def no_real_sleep(monkeypatch):
    # Retry backoff uses real seconds (2s, 4s...) — don't actually wait in tests.
    async def instant_sleep(_seconds):
        return None

    monkeypatch.setattr(claude_client.asyncio, "sleep", instant_sleep)


@pytest.fixture(autouse=True)
def fake_api_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-not-a-real-key")
    claude_client.get_settings.cache_clear()
    yield
    claude_client.get_settings.cache_clear()


async def test_extract_from_documents_parses_tool_result(monkeypatch):
    expected = {
        "company": "Acme",
        "sector": "FinTech",
        "stage": "Seed",
        "ask_amount": "£500,000",
        "use_of_funds": "Hiring",
        "traction_metrics": ["10 customers"],
        "team": ["Founder"],
        "market_size_claims": [],
        "revenue_model": "SaaS",
        "key_risks": [],
    }
    mock_create = AsyncMock(return_value=_fake_response(expected))
    monkeypatch.setattr(claude_client, "_create_message", mock_create)

    result = await claude_client.extract_from_documents([DocBlock(slot="deck", filename="d.pdf", kind="pdf", content=b"%PDF-1.4")])

    assert result.data == expected
    assert result.input_tokens == 100
    assert result.output_tokens == 50
    mock_create.assert_awaited_once()
    call_kwargs = mock_create.await_args.kwargs
    assert call_kwargs["tool_choice"] == {"type": "tool", "name": claude_client.EXTRACTION_TOOL_NAME}


async def test_extract_from_documents_requires_at_least_one_doc():
    with pytest.raises(ValueError):
        await claude_client.extract_from_documents([])


async def test_score_extraction_parses_tool_result(monkeypatch):
    expected = {"business_fundamentals": {"score": 7, "evidence": "quote", "feedback": ["do X"]}}
    mock_create = AsyncMock(return_value=_fake_response(expected))
    monkeypatch.setattr(claude_client, "_create_message", mock_create)

    result = await claude_client.score_extraction({"company": "Acme"}, DEMO_CONFIG)

    assert result.data == expected
    call_kwargs = mock_create.await_args.kwargs
    schema = call_kwargs["tools"][0]["input_schema"]
    assert "business_fundamentals" in schema["properties"]


async def test_retries_on_retryable_error_then_succeeds(monkeypatch):
    fake_request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    calls = [
        anthropic.APIConnectionError(message="boom", request=fake_request),
        _fake_response({"ok": True}),
    ]

    async def flaky_create(client, **kwargs):
        result = calls.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(claude_client, "_create_message", flaky_create)

    result = await claude_client.extract_from_documents([DocBlock(slot="deck", filename="d.pdf", kind="pdf", content=b"%PDF-1.4")])
    assert result.data == {"ok": True}


async def test_gives_up_after_max_retries(monkeypatch):
    fake_request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")

    async def always_fails(client, **kwargs):
        raise anthropic.APIConnectionError(message="boom", request=fake_request)

    monkeypatch.setattr(claude_client, "_create_message", always_fails)

    with pytest.raises(anthropic.APIConnectionError):
        await claude_client.extract_from_documents([DocBlock(slot="deck", filename="d.pdf", kind="pdf", content=b"%PDF-1.4")])


async def test_non_retryable_error_propagates_immediately(monkeypatch):
    call_count = 0

    async def bad_request(client, **kwargs):
        nonlocal call_count
        call_count += 1
        fake_request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
        fake_response = httpx.Response(400, request=fake_request, json={"error": "bad"})
        raise anthropic.BadRequestError(message="bad", response=fake_response, body=None)

    monkeypatch.setattr(claude_client, "_create_message", bad_request)

    with pytest.raises(anthropic.BadRequestError):
        await claude_client.extract_from_documents([DocBlock(slot="deck", filename="d.pdf", kind="pdf", content=b"%PDF-1.4")])
    assert call_count == 1  # no retries for a non-retryable error


async def test_response_with_no_tool_use_block_raises(monkeypatch):
    no_tool_response = SimpleNamespace(
        content=[SimpleNamespace(type="text", text="I refuse to use the tool.")],
        usage=SimpleNamespace(input_tokens=1, output_tokens=1),
        model_dump=lambda mode="json": {},
    )
    monkeypatch.setattr(claude_client, "_create_message", AsyncMock(return_value=no_tool_response))

    with pytest.raises(ValueError):
        await claude_client.extract_from_documents([DocBlock(slot="deck", filename="d.pdf", kind="pdf", content=b"%PDF-1.4")])


def test_pdf_doc_sent_as_native_document_block():
    blocks = claude_client._doc_content_blocks(
        [DocBlock(slot="deck", filename="d.pdf", kind="pdf", content=b"%PDF-1.4 fake")]
    )
    doc_blocks = [b for b in blocks if b.get("type") == "document"]
    assert len(doc_blocks) == 1
    assert doc_blocks[0]["source"]["media_type"] == "application/pdf"


def test_text_doc_sent_as_text_block():
    blocks = claude_client._doc_content_blocks(
        [DocBlock(slot="forecast", filename="f.xlsx", kind="text", content="Month | Revenue")]
    )
    assert any(b.get("type") == "text" and "Month | Revenue" in b.get("text", "") for b in blocks)
