"""rename submissions.sector to declared_sector

Revision ID: 8491d578be9e
Revises: fe89720bc126
Create Date: 2026-10-10 09:07:15.491316

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8491d578be9e'
down_revision: Union[str, None] = 'fe89720bc126'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # A true rename (not drop+add), so existing values are preserved.
    op.alter_column("submissions", "sector", new_column_name="declared_sector")


def downgrade() -> None:
    op.alter_column("submissions", "declared_sector", new_column_name="sector")
