import uuid

from models.db_models import Document, DocumentSlot, Submission
from services.submissions import compute_completeness


def _submission(**overrides) -> Submission:
    defaults = dict(
        id=uuid.uuid4(),
        founder_id=uuid.uuid4(),
        version=1,
        company_name=None,
        companies_house_number=None,
        declared_sector=None,
        notes=None,
    )
    defaults.update(overrides)
    return Submission(**defaults)


def _document(slot: DocumentSlot) -> Document:
    return Document(
        id=uuid.uuid4(),
        submission_id=uuid.uuid4(),
        slot=slot,
        original_filename="x.pdf",
        mime_type="application/pdf",
        size=1,
        storage_path="/tmp/x.pdf",
    )


def test_completeness_reflects_filled_and_missing_fields():
    submission = _submission(company_name="Acme", declared_sector="FinTech")
    documents = [_document(DocumentSlot.deck)]

    completeness = compute_completeness(submission, documents)

    assert completeness["optional_fields_filled"] == {
        "company_name": True,
        "companies_house_number": False,
        "declared_sector": True,
        "notes": False,
    }
    assert completeness["document_slots_filled"] == {
        "deck": True,
        "forecast": False,
        "one_pager": False,
    }


def test_completeness_all_empty():
    submission = _submission()
    completeness = compute_completeness(submission, documents=[])

    assert all(v is False for v in completeness["optional_fields_filled"].values())
    assert all(v is False for v in completeness["document_slots_filled"].values())
