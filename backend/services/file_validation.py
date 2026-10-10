"""
File type validation by content, not extension — a browser-supplied filename or
Content-Type header is never trusted. PDF and the three OOXML formats (PPTX, XLSX,
DOCX) all have unambiguous content signatures; CSV doesn't (it's just text), so it
gets a best-effort structural heuristic instead of a true magic number.

No python-magic/libmagic dependency: the three OOXML formats share one outer ZIP
signature, so a generic "what MIME type is this" sniffer still needs to look inside
the zip to tell them apart — which is all this module does directly, with stdlib
`zipfile`, for exactly the five formats this app accepts.
"""
import csv
import io
import re
import zipfile

PDF_MAGIC = b"%PDF-"

# Each OOXML format has one file inside its zip that only it has.
_OOXML_MARKERS = {
    "ppt/presentation.xml": "pptx",
    "xl/workbook.xml": "xlsx",
    "word/document.xml": "docx",
}

MIME_TYPES = {
    "pdf": "application/pdf",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "csv": "text/csv",
}

ALLOWED_KINDS = frozenset(MIME_TYPES)

# UK Companies House numbers: 8 digits, or 2 letters (jurisdiction/type prefix,
# e.g. SC, NI, OC) followed by 6 digits.
_COMPANIES_HOUSE_RE = re.compile(r"^(?:\d{8}|[A-Z]{2}\d{6})$")


def sniff_kind(contents: bytes) -> str | None:
    """Returns one of ALLOWED_KINDS, or None if the content isn't recognised."""
    if contents.startswith(PDF_MAGIC):
        return "pdf"

    if contents[:2] == b"PK":
        try:
            with zipfile.ZipFile(io.BytesIO(contents)) as zf:
                names = set(zf.namelist())
        except zipfile.BadZipFile:
            return None
        for marker, kind in _OOXML_MARKERS.items():
            if marker in names:
                return kind
        return None

    if _looks_like_csv(contents):
        return "csv"

    return None


def _looks_like_csv(contents: bytes) -> bool:
    try:
        text = contents[:8192].decode("utf-8")
    except UnicodeDecodeError:
        return False
    if not text.strip():
        return False
    try:
        csv.Sniffer().sniff(text, delimiters=",;\t")
    except csv.Error:
        return False
    return True


def validate_companies_house_number(raw: str) -> str:
    """Normalises and validates a UK Companies House number. Raises ValueError if invalid."""
    cleaned = raw.strip().upper()
    if not _COMPANIES_HOUSE_RE.match(cleaned):
        raise ValueError("Companies House numbers are 8 digits, or 2 letters followed by 6 digits.")
    return cleaned
