"""
Seeds 3-5 synthetic founders for local/demo use. Company names and all content
here are fictional placeholders — no client branding or real data.

Run from backend/ with the venv active:
    python -m scripts.seed
"""
import asyncio
import uuid
from pathlib import Path

from sqlalchemy import select

from core.config import get_settings
from core.database import AsyncSessionLocal
from models.db_models import Document, DocumentSlot, Extraction, Founder, Submission
from services.submissions import STUB_SCHEMA_VERSION

settings = get_settings()
UPLOAD_DIR = Path(settings.upload_dir)


def _placeholder_deck(name: str) -> bytes:
    return f"Synthetic placeholder pitch deck for {name}. Not a real PDF.".encode()


FOUNDERS = [
    {
        "email": "alice@example.com",
        "submissions": [
            {
                "company_name": "Northwind Robotics",
                "sector": "Deep Tech",
                "notes": "Warm intro from an existing portfolio founder.",
                "companies_house_number": None,
                "extraction": {
                    "company_name": "Northwind Robotics",
                    "sector": "Deep Tech",
                    "industry": "Industrial Automation",
                    "raise_amount": "£750,000",
                    "gap_flags": [
                        "No clear go-to-market timeline in the deck.",
                        "Unit economics are asserted but not shown.",
                    ],
                    "raising_raw": "(E) raising",
                },
                "has_deck": True,
            }
        ],
    },
    {
        "email": "bob@example.com",
        "submissions": [
            {
                "company_name": "Bluepeak Analytics",
                "sector": "B2B SaaS",
                "notes": "Pre-seed, second-time founder.",
                "companies_house_number": "09876543",
                "extraction": {
                    "company_name": "Bluepeak Analytics",
                    "sector": "B2B SaaS",
                    "industry": "Data Infrastructure",
                    "raise_amount": "£500,000",
                    "gap_flags": ["Competitor landscape is mentioned but not detailed."],
                    "raising_raw": "(E) raising",
                },
                "has_deck": True,
            }
        ],
    },
    {
        "email": "carol@example.com",
        "submissions": [
            {
                "company_name": "Harvest & Co",
                "sector": None,
                "notes": None,
                "companies_house_number": None,
                "extraction": {
                    "company_name": "Harvest & Co",
                    "sector": "Food & Drink",
                    "industry": "D2C Retail",
                    "raise_amount": "£250,000",
                    "gap_flags": [
                        "Team slide is missing a technical co-founder's background.",
                        "No clear go-to-market timeline in the deck.",
                    ],
                    "raising_raw": "(E) raising",
                },
                "has_deck": True,
            }
        ],
    },
    {
        # Two versions, to prove history: a thinner first attempt, then a resubmission
        # with more fields filled in and an updated raise.
        "email": "dana@example.com",
        "submissions": [
            {
                "company_name": "Meridian HealthTech",
                "sector": "HealthTech",
                "notes": None,
                "companies_house_number": None,
                "extraction": {
                    "company_name": "Meridian HealthTech",
                    "sector": "HealthTech",
                    "industry": "Clinical Software",
                    "raise_amount": "£400,000",
                    "gap_flags": ["Unit economics are asserted but not shown."],
                    "raising_raw": "(E) raising",
                },
                "has_deck": True,
            },
            {
                "company_name": "Meridian HealthTech",
                "sector": "HealthTech",
                "notes": "Resubmission after addressing the unit economics gap.",
                "companies_house_number": "13579246",
                "extraction": {
                    "company_name": "Meridian HealthTech",
                    "sector": "HealthTech",
                    "industry": "Clinical Software",
                    "raise_amount": "£600,000",
                    "gap_flags": ["Competitor landscape is mentioned but not detailed."],
                    "raising_raw": "(E) raising",
                },
                "has_deck": True,
            },
        ],
    },
    {
        "email": "erin@example.com",
        "submissions": [
            {
                "company_name": "Atlas Marketplace",
                "sector": "Marketplace",
                "notes": None,
                "companies_house_number": "11223344",
                "extraction": {
                    "company_name": "Atlas Marketplace",
                    "sector": "Marketplace",
                    "industry": "B2B Procurement",
                    "raise_amount": "£1,200,000",
                    "gap_flags": [
                        "Team slide is missing a technical co-founder's background.",
                        "Unit economics are asserted but not shown.",
                    ],
                    "raising_raw": "(E) raising",
                },
                "has_deck": True,
            }
        ],
    },
]


async def seed() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

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
                    sector=sub_data["sector"],
                    notes=sub_data["notes"],
                    companies_house_number=sub_data["companies_house_number"],
                )
                db.add(submission)
                await db.flush()

                if sub_data["has_deck"]:
                    deck_bytes = _placeholder_deck(sub_data["company_name"])
                    filename = f"{sub_data['company_name'].lower().replace(' ', '-')}-deck.pdf"
                    file_path = UPLOAD_DIR / f"{uuid.uuid4()}_{filename}"
                    file_path.write_bytes(deck_bytes)

                    db.add(
                        Document(
                            submission_id=submission.id,
                            slot=DocumentSlot.deck,
                            original_filename=filename,
                            mime_type="application/pdf",
                            size=len(deck_bytes),
                            storage_path=str(file_path),
                        )
                    )

                db.add(
                    Extraction(
                        submission_id=submission.id,
                        structured_json=sub_data["extraction"],
                        schema_version=STUB_SCHEMA_VERSION,
                    )
                )

            print(f"Seeded {founder_data['email']} with {len(founder_data['submissions'])} submission(s).")

        await db.commit()

    print("Done.")


if __name__ == "__main__":
    asyncio.run(seed())
