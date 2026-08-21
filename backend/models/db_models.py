import uuid
from datetime import datetime

from sqlalchemy import ARRAY, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class Submission(Base):
    """A deck upload. All extracted fields are STUBBED — see services/stub_extractor.py."""

    __tablename__ = "submissions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255))
    company_name: Mapped[str | None] = mapped_column(String(255))
    deck_filename: Mapped[str | None] = mapped_column(String(255))

    sector: Mapped[str | None] = mapped_column(String(120))
    industry: Mapped[str | None] = mapped_column(String(120))
    raise_amount: Mapped[str | None] = mapped_column(String(120))
    gap_flags: Mapped[list] = mapped_column(ARRAY(String), default=list)

    # "(E) raising" from the notes — unresolved meaning, stored raw, no logic built against it.
    raising_raw: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
