import uuid

from sqlalchemy import delete

from models.db_models import Founder, Submission
from services.submissions import get_or_create_founder, next_version_for_founder


async def test_same_email_reuses_founder_and_increments_version(db_session):
    email = f"pytest-{uuid.uuid4().hex[:8]}@example.com"

    try:
        founder_a = await get_or_create_founder(db_session, email)
        await db_session.commit()
        version_1 = await next_version_for_founder(db_session, founder_a.id)
        db_session.add(Submission(founder_id=founder_a.id, version=version_1))
        await db_session.commit()

        # Different case and surrounding whitespace — should still resolve to the same founder.
        founder_b = await get_or_create_founder(db_session, f"  {email.upper()}  ")
        await db_session.commit()
        version_2 = await next_version_for_founder(db_session, founder_b.id)
        db_session.add(Submission(founder_id=founder_b.id, version=version_2))
        await db_session.commit()

        assert founder_a.id == founder_b.id
        assert version_1 == 1
        assert version_2 == 2
    finally:
        await db_session.execute(delete(Submission).where(Submission.founder_id == founder_a.id))
        await db_session.execute(delete(Founder).where(Founder.id == founder_a.id))
        await db_session.commit()


async def test_different_emails_get_different_founders(db_session):
    email_a = f"pytest-{uuid.uuid4().hex[:8]}@example.com"
    email_b = f"pytest-{uuid.uuid4().hex[:8]}@example.com"

    try:
        founder_a = await get_or_create_founder(db_session, email_a)
        founder_b = await get_or_create_founder(db_session, email_b)
        await db_session.commit()

        assert founder_a.id != founder_b.id
        assert await next_version_for_founder(db_session, founder_a.id) == 1
        assert await next_version_for_founder(db_session, founder_b.id) == 1
    finally:
        await db_session.execute(delete(Founder).where(Founder.id.in_([founder_a.id, founder_b.id])))
        await db_session.commit()
