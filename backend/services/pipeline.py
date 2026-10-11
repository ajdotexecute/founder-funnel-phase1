"""
Orchestrates the two-stage extract-then-score pipeline for one submission:
load documents -> convert non-PDF ones to text -> extract -> (optional
Companies House lookup, merged into the extraction) -> score -> build
Extraction + Score + ModelCall rows for the caller to persist.

Never raises past run_pipeline() for an AI/network failure — "no crash on
unreadable files" extends to "no crash on a flaky model call." Returns a
PipelineResult whose `error` field tells the caller what (if anything) went
wrong; `model_calls` includes whatever calls succeeded even on partial
failure (e.g. extraction succeeded but scoring didn't), so that spend is
still logged.
"""
import logging
from dataclasses import dataclass, field

from core.config import get_settings
from models.db_models import Document, Extraction, ModelCall, ModelCallStage, Score, Submission
from services import claude_client, companies_house, document_text
from services.client_config import load_scoring_config
from services.file_validation import MIME_TYPES
from services.scoring_schema import ScoringConfig
from services.storage import StorageBackend

logger = logging.getLogger("founder_funnel.pipeline")

EXTRACTION_SCHEMA_VERSION = "2"
MIME_TO_KIND = {v: k for k, v in MIME_TYPES.items()}


@dataclass
class PipelineResult:
    extraction: Extraction | None = None
    score: Score | None = None
    config: ScoringConfig | None = None
    model_calls: list[ModelCall] = field(default_factory=list)
    error: str | None = None


async def _load_doc_blocks(documents: list[Document], storage: StorageBackend) -> list[claude_client.DocBlock]:
    blocks = []
    for doc in documents:
        try:
            contents = await storage.open(doc.storage_path)
            kind = MIME_TO_KIND.get(doc.mime_type)
            if kind == "pdf":
                blocks.append(claude_client.DocBlock(slot=doc.slot.value, filename=doc.original_filename, kind="pdf", content=contents))
            elif kind in document_text.CONVERTERS:
                text = document_text.to_text(kind, contents)
                blocks.append(claude_client.DocBlock(slot=doc.slot.value, filename=doc.original_filename, kind="text", content=text))
            else:
                logger.warning("Skipping document with unrecognised mime_type: %s", doc.mime_type)
        except Exception:
            # A single corrupt/unreadable file shouldn't sink the whole submission.
            logger.exception("Failed to load/convert document %s (slot=%s)", doc.id, doc.slot.value)
    return blocks


def _promote_sector_key(raw: dict) -> dict:
    """sector -> extracted_sector, so it can't be confused with Submission.declared_sector."""
    data = dict(raw)
    if "sector" in data:
        data["extracted_sector"] = data.pop("sector")
    return data


def _model_call(stage: ModelCallStage, submission_id, result: claude_client.CallResult) -> ModelCall:
    return ModelCall(
        submission_id=submission_id,
        stage=stage,
        model=get_settings().ai_model,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        latency_ms=result.latency_ms,
        raw_response=result.raw_response,
    )


async def run_pipeline(submission: Submission, documents: list[Document], storage: StorageBackend) -> PipelineResult:
    doc_blocks = await _load_doc_blocks(documents, storage)
    if not doc_blocks:
        return PipelineResult(error="No readable documents to extract from.")

    try:
        config = load_scoring_config()
    except Exception as e:
        logger.exception("Failed to load scoring config")
        return PipelineResult(error=f"Scoring config error: {e}")

    try:
        extract_result = await claude_client.extract_from_documents(doc_blocks)
    except Exception as e:
        logger.exception("Extraction call failed for submission %s", submission.id)
        return PipelineResult(config=config, error=f"Extraction failed: {e}")

    extraction_data = _promote_sector_key(extract_result.data)

    if submission.companies_house_number:
        try:
            company_info = await companies_house.lookup_company(submission.companies_house_number)
            if company_info is not None:
                extraction_data["companies_house"] = {
                    "status": company_info.status,
                    "incorporation_date": company_info.incorporation_date,
                    "sic_codes": company_info.sic_codes,
                }
        except Exception:
            logger.exception("Companies House lookup failed for submission %s", submission.id)

    extraction = Extraction(
        submission_id=submission.id,
        structured_json=extraction_data,
        schema_version=EXTRACTION_SCHEMA_VERSION,
    )
    model_calls = [_model_call(ModelCallStage.extract, submission.id, extract_result)]

    try:
        score_result = await claude_client.score_extraction(extraction_data, config)
    except Exception as e:
        logger.exception("Scoring call failed for submission %s", submission.id)
        return PipelineResult(
            extraction=extraction, config=config, model_calls=model_calls, error=f"Scoring failed: {e}"
        )

    model_calls.append(_model_call(ModelCallStage.score, submission.id, score_result))

    dimension_scores = {}
    for dim in config.dimensions:
        entry = score_result.data[dim.id]
        dimension_scores[dim.id] = {
            "name": dim.name,
            "score": entry["score"],
            "label": next(b.label for b in dim.rubric if b.min_score <= entry["score"] <= b.max_score),
            "rag": config.rag_band(dim.id, entry["score"]),
            "evidence": entry["evidence"],
            "feedback": entry["feedback"],
        }

    overall = config.overall_score({dim_id: v["score"] for dim_id, v in dimension_scores.items()})

    score = Score(
        submission_id=submission.id,
        config_id=config.id,
        config_version=config.version,
        dimension_scores=dimension_scores,
        overall_score=overall,
    )

    return PipelineResult(extraction=extraction, score=score, config=config, model_calls=model_calls)
