"""
Seeds 3-5 synthetic founders for local/demo use. Company names and all content
here are fictional placeholders — no client branding or real data. Extraction
and score data is hand-authored here (schema_version "2", matching the real
pipeline's shape) rather than produced by a live Claude call, so this script
never needs an API key.

Run from backend/ with the venv active:
    python -m scripts.seed
"""
import asyncio
import io
import zipfile
from datetime import datetime

from sqlalchemy import select

from core.database import AsyncSessionLocal
from models.db_models import Document, DocumentSlot, Extraction, Founder, Score, Submission
from services.client_config import load_scoring_config
from services.pipeline import EXTRACTION_SCHEMA_VERSION
from services.storage import get_storage_backend


def _placeholder_pdf(name: str) -> bytes:
    # A real %PDF- magic number, so this passes the same content-sniffing the real
    # upload endpoint applies, even though it isn't a fully valid PDF.
    return f"%PDF-1.4\n% Synthetic placeholder pitch deck for {name}. Not a real PDF.".encode()


def _placeholder_xlsx(name: str) -> bytes:
    # A minimal zip with the one marker file sniff_kind() looks for — enough to be
    # recognised as XLSX, not a fully valid workbook.
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("xl/workbook.xml", f"<!-- synthetic placeholder forecast for {name} -->")
    return buf.getvalue()


def _placeholder_docx(name: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("word/document.xml", f"<!-- synthetic placeholder one-pager for {name} -->")
    return buf.getvalue()


SLOT_CONTENT = {
    DocumentSlot.deck: ("deck.pdf", "application/pdf", _placeholder_pdf),
    DocumentSlot.forecast: ("forecast.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", _placeholder_xlsx),
    DocumentSlot.one_pager: ("one-pager.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", _placeholder_docx),
}

FOUNDERS = [
    {
        "email": "alice@example.com",
        "submissions": [
            {
                "company_name": "Northwind Robotics",
                "declared_sector": "Deep Tech",
                "notes": "Warm intro from an existing portfolio founder.",
                "companies_house_number": None,
                "slots": [DocumentSlot.deck],
                "extraction": {
                    "company": "Northwind Robotics",
                    "extracted_sector": "Deep Tech",
                    "stage": "Seed",
                    "ask_amount": "£750,000",
                    "use_of_funds": "Hiring two robotics engineers and a pilot with an existing customer.",
                    "traction_metrics": ["2 paid pilots", "£40k ARR"],
                    "team": ["Founder: ex-Dyson robotics lead", "CTO: PhD in controls systems"],
                    "market_size_claims": [{"claim": "£2bn UK industrial automation market", "stated_basis": "Analyst report, no citation given"}],
                    "revenue_model": "Hardware + annual service contract",
                    "key_risks": ["No clear go-to-market timeline in the deck.", "Unit economics are asserted but not shown."],
                },
                "scores": {
                    "business_fundamentals": {"score": 7, "evidence": "2 paid pilots and £40k ARR cited in traction.", "feedback": ["Show unit economics per pilot", "Clarify path from pilot to scaled contract"]},
                    "investment_case": {"score": 6, "evidence": "Use of funds given as hiring + one pilot, no milestone-by-spend breakdown.", "feedback": ["Tie the £750k ask to specific milestones"]},
                    "investor_presentation": {"score": 8, "evidence": "Clear structure across problem, team, and traction sections.", "feedback": ["Add a slide on competitive landscape"]},
                },
            }
        ],
    },
    {
        "email": "bob@example.com",
        "submissions": [
            {
                "company_name": "Bluepeak Analytics",
                "declared_sector": "B2B SaaS",
                "notes": "Pre-seed, second-time founder.",
                "companies_house_number": "09876543",
                "slots": [DocumentSlot.deck, DocumentSlot.forecast],
                "extraction": {
                    "company": "Bluepeak Analytics",
                    "extracted_sector": "B2B SaaS",
                    "stage": "Pre-seed",
                    "ask_amount": "£500,000",
                    "use_of_funds": "18 months runway for a 3-person engineering team.",
                    "traction_metrics": ["4 design partners", "no paying customers yet"],
                    "team": ["Founder: second-time, prior exit in adjacent space"],
                    "market_size_claims": [{"claim": "$12bn data infrastructure market", "stated_basis": "Gartner, cited"}],
                    "revenue_model": "Usage-based SaaS",
                    "key_risks": ["Competitor landscape is mentioned but not detailed."],
                },
                "scores": {
                    "business_fundamentals": {"score": 5, "evidence": "4 design partners, no paying customers yet.", "feedback": ["Convert at least one design partner to paid before next raise"]},
                    "investment_case": {"score": 6, "evidence": "18 months runway stated, team size and cost not broken down.", "feedback": ["Break down the £500k by headcount and timeline"]},
                    "investor_presentation": {"score": 7, "evidence": "Market size claim is sourced, most other claims are not.", "feedback": ["Source the remaining market and competitor claims"]},
                },
            }
        ],
    },
    {
        "email": "carol@example.com",
        "submissions": [
            {
                "company_name": "Harvest & Co",
                "declared_sector": None,
                "notes": None,
                "companies_house_number": None,
                "slots": [DocumentSlot.deck],
                "extraction": {
                    "company": "Harvest & Co",
                    "extracted_sector": "Food & Drink",
                    "stage": "Pre-seed",
                    "ask_amount": "£250,000",
                    "use_of_funds": "Not broken down in the deck.",
                    "traction_metrics": ["Farmers market sales only"],
                    "team": ["Solo founder"],
                    "market_size_claims": [{"claim": "£8bn UK artisanal food market", "stated_basis": "Not stated"}],
                    "revenue_model": "D2C retail",
                    "key_risks": ["Team slide is missing a technical co-founder's background.", "No clear go-to-market timeline in the deck."],
                },
                "scores": {
                    "business_fundamentals": {"score": 3, "evidence": "Traction limited to farmers market sales; no online or retail channel yet.", "feedback": ["Show a path beyond farmers markets", "Add any repeat-purchase data available"]},
                    "investment_case": {"score": 3, "evidence": "Use of funds not broken down anywhere in the deck.", "feedback": ["Add a basic use-of-funds breakdown", "State a specific ask-to-milestone link"]},
                    "investor_presentation": {"score": 5, "evidence": "Market size claim has no stated basis.", "feedback": ["Source the £8bn market claim", "Add a team slide"]},
                },
            }
        ],
    },
    {
        # Two versions, to prove history: a thinner first attempt, then a resubmission
        # with more fields and documents filled in and an improved score.
        "email": "dana@example.com",
        "submissions": [
            {
                "company_name": "Meridian HealthTech",
                "declared_sector": "HealthTech",
                "notes": None,
                "companies_house_number": None,
                "slots": [DocumentSlot.deck],
                "extraction": {
                    "company": "Meridian HealthTech",
                    "extracted_sector": "HealthTech",
                    "stage": "Seed",
                    "ask_amount": "£400,000",
                    "use_of_funds": "Not clearly broken down.",
                    "traction_metrics": ["1 NHS trust pilot, results pending"],
                    "team": ["Founder: clinician", "CTO: ex-Babylon Health"],
                    "market_size_claims": [{"claim": "£5bn NHS digital health spend", "stated_basis": "NHS England report, cited"}],
                    "revenue_model": "Per-trust annual licence",
                    "key_risks": ["Unit economics are asserted but not shown."],
                },
                "scores": {
                    "business_fundamentals": {"score": 6, "evidence": "1 NHS trust pilot with results still pending.", "feedback": ["Share pilot results once available", "Clarify sales cycle length to next trust"]},
                    "investment_case": {"score": 5, "evidence": "Use of funds not clearly broken down.", "feedback": ["Add a use-of-funds breakdown"]},
                    "investor_presentation": {"score": 7, "evidence": "Market size is sourced to an NHS England report.", "feedback": ["Add a slide on regulatory pathway"]},
                },
            },
            {
                "company_name": "Meridian HealthTech",
                "declared_sector": "HealthTech",
                "notes": "Resubmission after addressing the unit economics gap.",
                "companies_house_number": "13579246",
                "slots": [DocumentSlot.deck, DocumentSlot.forecast, DocumentSlot.one_pager],
                "extraction": {
                    "company": "Meridian HealthTech",
                    "extracted_sector": "HealthTech",
                    "stage": "Seed",
                    "ask_amount": "£600,000",
                    "use_of_funds": "60% engineering hires, 40% clinical validation studies.",
                    "traction_metrics": ["1 NHS trust pilot complete, 15% efficiency gain reported", "2 trusts in pipeline"],
                    "team": ["Founder: clinician", "CTO: ex-Babylon Health", "Added: Head of Regulatory"],
                    "market_size_claims": [{"claim": "£5bn NHS digital health spend", "stated_basis": "NHS England report, cited"}],
                    "revenue_model": "Per-trust annual licence",
                    "key_risks": ["Competitor landscape is mentioned but not detailed."],
                },
                "scores": {
                    "business_fundamentals": {"score": 8, "evidence": "Completed pilot reports a 15% efficiency gain, two more trusts in pipeline.", "feedback": ["Name the two pipeline trusts if NDA allows"]},
                    "investment_case": {"score": 7, "evidence": "Use of funds now split 60/40 between engineering and clinical validation.", "feedback": ["Attach a date to each clinical validation milestone"]},
                    "investor_presentation": {"score": 8, "evidence": "Pilot results and team addition both clearly called out.", "feedback": ["Add a competitor comparison table"]},
                },
            },
        ],
    },
    {
        "email": "erin@example.com",
        "submissions": [
            {
                "company_name": "Atlas Marketplace",
                "declared_sector": "Marketplace",
                "notes": None,
                "companies_house_number": "11223344",
                "slots": [DocumentSlot.deck, DocumentSlot.one_pager],
                "extraction": {
                    "company": "Atlas Marketplace",
                    "extracted_sector": "Marketplace",
                    "stage": "Series A",
                    "ask_amount": "£1,200,000",
                    "use_of_funds": "Sales team expansion and supply-side liquidity incentives.",
                    "traction_metrics": ["£180k GMV/month", "22% MoM growth"],
                    "team": ["Founder + 2 co-founders, prior startup experience"],
                    "market_size_claims": [{"claim": "£3bn UK B2B procurement market", "stated_basis": "Internal estimate, methodology not shown"}],
                    "revenue_model": "Take rate on GMV",
                    "key_risks": ["Team slide is missing a technical co-founder's background.", "Unit economics are asserted but not shown."],
                },
                "scores": {
                    "business_fundamentals": {"score": 7, "evidence": "£180k GMV/month with 22% MoM growth cited.", "feedback": ["Show CAC and take-rate margin per transaction"]},
                    "investment_case": {"score": 6, "evidence": "Use of funds split between sales and liquidity incentives, no split ratio given.", "feedback": ["Give the sales vs incentives split as a percentage"]},
                    "investor_presentation": {"score": 6, "evidence": "Market size claim has no stated methodology.", "feedback": ["Show the methodology behind the £3bn estimate", "Add technical co-founder background"]},
                },
            }
        ],
    },
]


async def seed() -> None:
    storage = get_storage_backend()
    config = load_scoring_config()

    async with AsyncSessionLocal() as db:
        existing = await db.execute(select(Founder.id).limit(1))
        if existing.scalar_one_or_none() is not None:
            print("Founders already exist — skipping seed (delete rows first if you want to reseed).")
            return

        for founder_data in FOUNDERS:
            founder = Founder(email=founder_data["email"])
            db.add(founder)
            await db.flush()

            for version, sub_data in enumerate(founder_data["submissions"], start=1):
                submission = Submission(
                    founder_id=founder.id,
                    version=version,
                    company_name=sub_data["company_name"],
                    declared_sector=sub_data["declared_sector"],
                    notes=sub_data["notes"],
                    companies_house_number=sub_data["companies_house_number"],
                    consent_at=datetime.utcnow(),
                )
                db.add(submission)
                await db.flush()

                for slot in sub_data["slots"]:
                    suffix, mime_type, make_bytes = SLOT_CONTENT[slot]
                    contents = make_bytes(sub_data["company_name"])
                    filename = f"{sub_data['company_name'].lower().replace(' ', '-')}-{suffix}"
                    storage_key = f"{submission.id}/{slot.value}/{filename}"
                    await storage.save(storage_key, contents)

                    db.add(
                        Document(
                            submission_id=submission.id,
                            slot=slot,
                            original_filename=filename,
                            mime_type=mime_type,
                            size=len(contents),
                            storage_path=storage_key,
                        )
                    )

                db.add(
                    Extraction(
                        submission_id=submission.id,
                        structured_json=sub_data["extraction"],
                        schema_version=EXTRACTION_SCHEMA_VERSION,
                    )
                )

                dimension_scores = {}
                for dim in config.dimensions:
                    raw = sub_data["scores"][dim.id]
                    label = next(b.label for b in dim.rubric if b.min_score <= raw["score"] <= b.max_score)
                    dimension_scores[dim.id] = {
                        "name": dim.name,
                        "score": raw["score"],
                        "label": label,
                        "rag": config.rag_band(dim.id, raw["score"]),
                        "evidence": raw["evidence"],
                        "feedback": raw["feedback"],
                    }
                overall = config.overall_score({dim_id: v["score"] for dim_id, v in dimension_scores.items()})

                db.add(
                    Score(
                        submission_id=submission.id,
                        config_id=config.id,
                        config_version=config.version,
                        dimension_scores=dimension_scores,
                        overall_score=overall,
                    )
                )

            print(f"Seeded {founder_data['email']} with {len(founder_data['submissions'])} submission(s).")

        await db.commit()

    print("Done.")


if __name__ == "__main__":
    asyncio.run(seed())
