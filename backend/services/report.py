"""
Renders a submission's score through the client's report/template.html
(Jinja2) to HTML, and that HTML to PDF via a headless Chromium
(Playwright print-to-PDF) — see CLAUDE.md for why Playwright over WeasyPrint.
"""
from jinja2 import Template
from playwright.async_api import async_playwright

from models.db_models import Extraction, Score, Submission
from services.client_config import load_report_template
from services.scoring_schema import ScoringConfig


def build_report_context(submission: Submission, extraction: Extraction, score: Score, config: ScoringConfig) -> dict:
    dimensions = []
    for dim in config.dimensions:
        entry = score.dimension_scores[dim.id]
        dimensions.append(
            {
                "id": dim.id,
                "name": dim.name,
                "score": entry["score"],
                "scale_max": config.scale.max,
                "label": entry["label"],
                "rag": entry["rag"],
                "evidence": entry["evidence"],
                "feedback": entry["feedback"],
            }
        )

    # "Top 3 actions" and "what's working": pool every dimension's feedback, split by
    # whether that dimension is already Green (working) or not (to fix).
    working = [f"{d['name']}: {pt}" for d in dimensions if d["rag"] == "green" for pt in d["feedback"][:1]]
    to_fix = [f"{d['name']}: {pt}" for d in dimensions if d["rag"] != "green" for pt in d["feedback"]][:3]

    return {
        "company_name": submission.company_name or extraction.structured_json.get("company") or "This company",
        "generated_at": score.created_at,
        "overall_score": score.overall_score,
        "config_name": config.name,
        "dimensions": dimensions,
        "working": working,
        "to_fix": to_fix,
        "data_gaps": [
            risk for risk in extraction.structured_json.get("key_risks", [])
        ],
        "cta_text": config.cta_text,
        "extraction": extraction.structured_json,
    }


def render_report_html(context: dict, client_id: str | None = None) -> str:
    template = Template(load_report_template(client_id))
    return template.render(**context)


async def render_report_pdf(html: str) -> bytes:
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=["--headless=new"])
        try:
            page = await browser.new_page()
            await page.set_content(html, wait_until="load")
            return await page.pdf(format="A4", print_background=True)
        finally:
            await browser.close()
