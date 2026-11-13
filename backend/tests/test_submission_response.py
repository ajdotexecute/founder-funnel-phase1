import uuid
from datetime import datetime

from models.db_models import Extraction, Founder, Submission
from services.submissions import build_submission_response


def _submission() -> Submission:
    return Submission(
        id=uuid.uuid4(), founder_id=uuid.uuid4(), version=1, company_name="Acme",
        declared_sector=None, companies_house_number="SC123456", notes=None,
        consent_at=datetime.utcnow(), created_at=datetime.utcnow(),
    )


def _founder() -> Founder:
    return Founder(id=uuid.uuid4(), email="test@example.com", created_at=datetime.utcnow())


def test_companies_house_panel_verified_when_lookup_succeeded():
    extraction = Extraction(
        id=uuid.uuid4(), submission_id=uuid.uuid4(), schema_version="2",
        structured_json={"companies_house": {"company_name": "ACME LTD", "status": "active", "incorporation_date": "2020-01-01", "sic_codes": ["62012"]}},
        created_at=datetime.utcnow(),
    )

    response = build_submission_response(_submission(), _founder(), [], extraction, None)

    assert response.companies_house.status == "verified"
    assert response.companies_house.company_name == "ACME LTD"
    assert response.companies_house.sic_codes == ["62012"]


def test_companies_house_panel_not_checked_when_no_lookup_data():
    extraction = Extraction(
        id=uuid.uuid4(), submission_id=uuid.uuid4(), schema_version="2",
        structured_json={"company": "Acme"},  # no "companies_house" key at all
        created_at=datetime.utcnow(),
    )

    response = build_submission_response(_submission(), _founder(), [], extraction, None)

    assert response.companies_house.status == "not_checked"
    assert response.companies_house.company_name is None


def test_companies_house_panel_not_checked_when_extraction_missing():
    response = build_submission_response(_submission(), _founder(), [], None, None, processing_error="API down")

    assert response.companies_house.status == "not_checked"
