"""
STUB — no PDF parsing happens here.

This returns the same hardcoded sample critique for any uploaded file. The
upload endpoint never opens or reads the PDF's contents beyond saving it to
disk. Real extraction is out of scope for this prototype; see CLAUDE.md.
"""

SAMPLE_EXTRACTION = {
    "company_name": "Acme Robotics",
    "sector": "Deep Tech",
    "industry": "Industrial Automation",
    "raise_amount": "£750,000",
    "gap_flags": [
        "No clear go-to-market timeline in the deck.",
        "Competitor landscape is mentioned but not detailed.",
        "Team slide is missing a technical co-founder's background.",
        "Unit economics are asserted but not shown.",
    ],
    "raising_raw": "(E) raising",
}


def extract_from_deck(filename: str | None) -> dict:
    """Always returns the same sample data, regardless of the file passed in."""
    return dict(SAMPLE_EXTRACTION)
