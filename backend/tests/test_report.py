import uuid
from datetime import datetime

import pytest
from playwright.async_api import Error as PlaywrightError

from models.db_models import Extraction, Score, Submission
from services.client_config import load_scoring_config
from services.report import build_report_context, render_report_html, render_report_pdf

CONFIG = load_scoring_config("demo", "demo")

DIMENSION_SCORES = {
    "business_fundamentals": {"name": "Business fundamentals", "score": 7, "label": "Developing", "rag": "amber", "evidence": "3 pilots running.", "feedback": ["Add churn data"]},
    "investment_case": {"name": "Investment case", "score": 4, "label": "Weak", "rag": "red", "evidence": "No use-of-funds breakdown.", "feedback": ["Break down use of funds", "Justify the ask"]},
    "investor_presentation": {"name": "Investor presentation", "score": 9, "label": "Strong", "rag": "green", "evidence": "Clear and consistent.", "feedback": ["Tighten slide 4"]},
}


def _submission() -> Submission:
    return Submission(id=uuid.uuid4(), founder_id=uuid.uuid4(), version=1, company_name="Acme Robotics")


def _extraction() -> Extraction:
    return Extraction(
        id=uuid.uuid4(), submission_id=uuid.uuid4(), schema_version="2",
        structured_json={"company": "Acme Robotics", "key_risks": ["Supplier dependency not mitigated."]},
    )


def _score() -> Score:
    return Score(
        id=uuid.uuid4(), submission_id=uuid.uuid4(), config_id="demo", config_version="1",
        dimension_scores=DIMENSION_SCORES, overall_score=66.7, created_at=datetime.utcnow(),
    )


def test_build_report_context_includes_all_sections():
    context = build_report_context(_submission(), _extraction(), _score(), CONFIG)

    assert context["company_name"] == "Acme Robotics"
    assert context["overall_score"] == 66.7
    assert len(context["dimensions"]) == 3
    assert context["working"]  # investor_presentation is green
    assert context["to_fix"]  # investment_case and business_fundamentals aren't
    assert "Supplier dependency not mitigated." in context["data_gaps"]
    assert context["cta_text"]


def test_build_report_context_top_to_fix_capped_at_three():
    context = build_report_context(_submission(), _extraction(), _score(), CONFIG)
    assert len(context["to_fix"]) <= 3


def test_render_report_html_includes_key_content():
    context = build_report_context(_submission(), _extraction(), _score(), CONFIG)
    html = render_report_html(context, client_id="demo")

    assert "Acme Robotics" in html
    assert "66.7" in html
    assert "Business fundamentals" in html
    assert "rag-red" in html and "rag-amber" in html and "rag-green" in html


async def test_render_report_pdf_produces_a_real_pdf():
    context = build_report_context(_submission(), _extraction(), _score(), CONFIG)
    html = render_report_html(context, client_id="demo")

    try:
        pdf_bytes = await render_report_pdf(html)
    except PlaywrightError as e:
        if "Executable doesn't exist" in str(e):
            pytest.skip(
                "No Chromium build matching the pinned playwright version in this "
                "environment — run `playwright install --with-deps chromium` (the "
                "Dockerfile already does this for the real container)."
            )
        raise

    assert pdf_bytes[:4] == b"%PDF"
    assert len(pdf_bytes) > 1000
