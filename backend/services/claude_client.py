"""
Thin wrapper around the Anthropic SDK: two structured calls (extract, score),
both via forced tool-use so the response is always parseable JSON matching a
known schema, never free-text to regex out.

Tests mock `_create_message` directly (monkeypatch), never hit the network.
"""
import asyncio
import base64
import time
from dataclasses import dataclass
from typing import Any

import anthropic

from core.config import get_settings
from services.scoring_schema import ScoringConfig

RETRYABLE_ERRORS = (
    anthropic.APIConnectionError,
    anthropic.APITimeoutError,
    anthropic.RateLimitError,
    anthropic.InternalServerError,
)

EXTRACTION_TOOL_NAME = "record_extraction"
EXTRACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "company": {"type": "string"},
        "sector": {"type": "string"},
        "stage": {"type": "string"},
        "ask_amount": {"type": "string"},
        "use_of_funds": {"type": "string"},
        "traction_metrics": {"type": "array", "items": {"type": "string"}},
        "team": {"type": "array", "items": {"type": "string"}},
        "market_size_claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "claim": {"type": "string"},
                    "stated_basis": {"type": "string"},
                },
                "required": ["claim", "stated_basis"],
            },
        },
        "revenue_model": {"type": "string"},
        "key_risks": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "company",
        "sector",
        "stage",
        "ask_amount",
        "use_of_funds",
        "traction_metrics",
        "team",
        "market_size_claims",
        "revenue_model",
        "key_risks",
    ],
}

SCORING_TOOL_NAME = "record_scores"


@dataclass
class DocBlock:
    slot: str
    filename: str
    kind: str  # "pdf" or "text" — already converted by services/document_text.py for non-PDF kinds
    content: bytes | str


@dataclass
class CallResult:
    data: dict
    input_tokens: int
    output_tokens: int
    latency_ms: int
    raw_response: dict


def _client() -> anthropic.AsyncAnthropic:
    settings = get_settings()
    return anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key, timeout=settings.ai_timeout_seconds)


async def _create_message(client: anthropic.AsyncAnthropic, **kwargs):
    """The one place that actually calls the API — the sole target for test mocking."""
    return await client.messages.create(**kwargs)


async def _call_with_retries(client: anthropic.AsyncAnthropic, **kwargs) -> tuple[Any, int]:
    settings = get_settings()
    attempt = 0
    while True:
        start = time.monotonic()
        try:
            response = await _create_message(client, **kwargs)
            latency_ms = int((time.monotonic() - start) * 1000)
            return response, latency_ms
        except RETRYABLE_ERRORS:
            attempt += 1
            if attempt > settings.ai_max_retries:
                raise
            await asyncio.sleep(2**attempt)  # 2s, 4s, 8s...


def _doc_content_blocks(docs: list[DocBlock]) -> list[dict]:
    blocks = []
    for doc in docs:
        blocks.append({"type": "text", "text": f"--- Document: {doc.filename} (slot: {doc.slot}) ---"})
        if doc.kind == "pdf":
            blocks.append(
                {
                    "type": "document",
                    "source": {
                        "type": "base64",
                        "media_type": "application/pdf",
                        "data": base64.standard_b64encode(doc.content).decode("ascii"),
                    },
                }
            )
        else:
            blocks.append({"type": "text", "text": doc.content})
    return blocks


def _tool_result(response) -> dict:
    for block in response.content:
        if block.type == "tool_use":
            return block.input
    raise ValueError("Model response had no tool_use block — nothing to parse.")


async def extract_from_documents(docs: list[DocBlock]) -> CallResult:
    if not docs:
        raise ValueError("extract_from_documents needs at least one document.")

    settings = get_settings()
    client = _client()
    content = _doc_content_blocks(docs) + [
        {
            "type": "text",
            "text": (
                "Extract the fields defined by the record_extraction tool from the documents "
                "above. If a field isn't present in the documents, use an empty string or empty "
                "list as appropriate — never invent information that isn't there."
            ),
        }
    ]

    response, latency_ms = await _call_with_retries(
        client,
        model=settings.ai_model,
        max_tokens=4096,
        tools=[{"name": EXTRACTION_TOOL_NAME, "input_schema": EXTRACTION_SCHEMA, "description": "Record the extracted fields."}],
        tool_choice={"type": "tool", "name": EXTRACTION_TOOL_NAME},
        messages=[{"role": "user", "content": content}],
    )

    return CallResult(
        data=_tool_result(response),
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        latency_ms=latency_ms,
        raw_response=response.model_dump(mode="json"),
    )


def _scoring_schema(config: ScoringConfig) -> dict:
    dim_props = {}
    for dim in config.dimensions:
        dim_props[dim.id] = {
            "type": "object",
            "properties": {
                "score": {"type": "integer", "minimum": config.scale.min, "maximum": config.scale.max},
                "evidence": {
                    "type": "string",
                    "description": "A short quote or field reference from the extraction that supports this score.",
                },
                "feedback": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["score", "evidence", "feedback"],
        }
    return {
        "type": "object",
        "properties": dim_props,
        "required": [d.id for d in config.dimensions],
    }


async def score_extraction(extraction: dict, config: ScoringConfig) -> CallResult:
    settings = get_settings()
    client = _client()

    dimension_brief = "\n\n".join(
        f"- {d.id} ({d.name}, weight {d.weight}): {d.description}\n  Rubric: "
        + "; ".join(f"{b.min_score}-{b.max_score}={b.label}: {b.description}" for b in d.rubric)
        for d in config.dimensions
    )

    prompt = (
        f"Score this extracted pitch deck data against the following framework. "
        f"Each dimension is scored {config.scale.min}-{config.scale.max}. "
        f"Every dimension needs a short evidence quote or field reference from the extraction "
        f"below, and 2-3 short feedback points.\n\n"
        f"Framework dimensions:\n{dimension_brief}\n\n"
        f"Extracted data:\n{extraction}"
    )

    response, latency_ms = await _call_with_retries(
        client,
        model=settings.ai_model,
        max_tokens=4096,
        tools=[{"name": SCORING_TOOL_NAME, "input_schema": _scoring_schema(config), "description": "Record the per-dimension scores."}],
        tool_choice={"type": "tool", "name": SCORING_TOOL_NAME},
        messages=[{"role": "user", "content": prompt}],
    )

    return CallResult(
        data=_tool_result(response),
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        latency_ms=latency_ms,
        raw_response=response.model_dump(mode="json"),
    )
