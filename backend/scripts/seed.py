"""
Seeds 3-5 synthetic founders for local/demo use. Company names and all content
here are fictional placeholders — no client branding or real data.

Run from backend/ with the venv active:
    python -m scripts.seed
"""
import asyncio
import io
import zipfile
from datetime import datetime

from sqlalchemy import select

from core.database import AsyncSessionLocal
from models.db_models import Document, DocumentSlot, Extraction, Founder, Submission
from services.storage import get_storage_backend
from services.submissions import STUB_SCHEMA_VERSION


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
                    "company_name": "Northwind Robotics",
                    "extracted_sector": "Deep Tech",
                    "industry": "Industrial Automation",
                    "raise_amount": "£750,000",
                    "gap_flags": [
                        "No clear go-to-market timeline in the deck.",
                        "Unit economics are asserted but not shown.",
                    ],
                    "raising_raw": "(E) raising",
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
                    "company_name": "Bluepeak Analytics",
                    "extracted_sector": "B2B SaaS",
                    "industry": "Data Infrastructure",
                    "raise_amount": "£500,000",
                    "gap_flags": ["Competitor landscape is mentioned but not detailed."],
                    "raising_raw": "(E) raising",
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
                    "company_name": "Harvest & Co",
                    "extracted_sector": "Food & Drink",
                    "industry": "D2C Retail",
                    "raise_amount": "£250,000",
                    "gap_flags": [
                        "Team slide is missing a technical co-founder's background.",
                        "No clear go-to-market timeline in the deck.",
                    ],
                    "raising_raw": "(E) raising",
                },
            }
        ],
    },
    {
        # Two versions, to prove history: a thinner first attempt, then a resubmission
        # with more fields and documents filled in and an updated raise.
        "email": "dana@example.com",
        "submissions": [
            {
                "company_name": "Meridian HealthTech",
                "declared_sector": "HealthTech",
                "notes": None,
                "companies_house_number": None,
                "slots": [DocumentSlot.deck],
                "extraction": {
                    "company_name": "Meridian HealthTech",
                    "extracted_sector": "HealthTech",
                    "industry": "Clinical Software",
                    "raise_amount": "£400,000",
                    "gap_flags": ["Unit economics are asserted but not shown."],
                    "raising_raw": "(E) raising",
                },
            },
            {
                "company_name": "Meridian HealthTech",
                "declared_sector": "HealthTech",
                "notes": "Resubmission after addressing the unit economics gap.",
                "companies_house_number": "13579246",
                "slots": [DocumentSlot.deck, DocumentSlot.forecast, DocumentSlot.one_pager],
                "extraction": {
                    "company_name": "Meridian HealthTech",
                    "extracted_sector": "HealthTech",
                    "industry": "Clinical Software",
                    "raise_amount": "£600,000",
                    "gap_flags": ["Competitor landscape is mentioned but not detailed."],
                    "raising_raw": "(E) raising",
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
                    "company_name": "Atlas Marketplace",
                    "extracted_sector": "Marketplace",
                    "industry": "B2B Procurement",
                    "raise_amount": "£1,200,000",
                    "gap_flags": [
                        "Team slide is missing a technical co-founder's background.",
                        "Unit economics are asserted but not shown.",
                    ],
                    "raising_raw": "(E) raising",
                },
            }
        ],
    },
]


async def seed() -> None:
    storage = get_storage_backend()

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
                        schema_version=STUB_SCHEMA_VERSION,
                    )
                )

            print(f"Seeded {founder_data['email']} with {len(founder_data['submissions'])} submission(s).")

        await db.commit()

    print("Done.")


if __name__ == "__main__":
    asyncio.run(seed())
