"""kurum iletisim_email

Revision ID: cab64a993783
Revises: 0001
Create Date: 2026-09-24 09:40:47.718779
"""
from collections.abc import Sequence

import pgvector.sqlalchemy  # noqa: F401  (Vector kolonları için)
import sqlalchemy as sa
from alembic import op

revision: str = 'cab64a993783'
down_revision: str | None = '0001'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('kurum', sa.Column('iletisim_email', sa.String(), nullable=True))
    op.create_index(op.f('ix_kurum_iletisim_email'), 'kurum', ['iletisim_email'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_kurum_iletisim_email'), table_name='kurum')
    op.drop_column('kurum', 'iletisim_email')
