import io
import zipfile

import pytest

from services.file_validation import sniff_kind, validate_companies_house_number


def _zip_with(entry: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(entry, "x")
    return buf.getvalue()


def test_sniff_pdf():
    assert sniff_kind(b"%PDF-1.4 rest of file") == "pdf"


def test_sniff_pptx():
    assert sniff_kind(_zip_with("ppt/presentation.xml")) == "pptx"


def test_sniff_xlsx():
    assert sniff_kind(_zip_with("xl/workbook.xml")) == "xlsx"


def test_sniff_docx():
    assert sniff_kind(_zip_with("word/document.xml")) == "docx"


def test_sniff_csv():
    assert sniff_kind(b"name,sector,raise\nAcme,FinTech,500000\n") == "csv"


def test_sniff_rejects_renamed_text_file():
    # Extension lying ("this is a .pdf") shouldn't matter — content does. No
    # delimiter-like characters here, so it shouldn't pass as CSV either.
    assert sniff_kind(b"just plain text with no structure to speak of at all") is None


def test_sniff_rejects_zip_without_a_known_marker():
    assert sniff_kind(_zip_with("some/other/file.xml")) is None


def test_sniff_rejects_empty_content():
    assert sniff_kind(b"") is None


@pytest.mark.parametrize("value", ["01234567", "SC123456", "ni123456", " 01234567 "])
def test_companies_house_number_accepts_valid_formats(value):
    result = validate_companies_house_number(value)
    assert result in ("01234567", "SC123456", "NI123456")


@pytest.mark.parametrize("value", ["1234567", "123456789", "ABCDEFGH", "SC12345", "SC1234567"])
def test_companies_house_number_rejects_invalid_formats(value):
    with pytest.raises(ValueError):
        validate_companies_house_number(value)
