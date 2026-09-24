"""referans_istegi puan

Revision ID: b4612ec38a95
Revises: 2d69c67aa540
Create Date: 2026-09-24 11:25:53.781694
"""
from collections.abc import Sequence

import pgvector.sqlalchemy  # noqa: F401  (Vector kolonları için)
import sqlalchemy as sa
from alembic import op


revision: str = 'b4612ec38a95'
down_revision: str | None = '2d69c67aa540'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("referans_istegi", sa.Column("puan", sa.Integer(), nullable=True))
    # CHECK kısıtını alembic autogenerate üretmiyor, elle ekleniyor.
    op.create_check_constraint("puan_araligi", "referans_istegi", "puan BETWEEN 1 AND 5")


def downgrade() -> None:
    op.drop_constraint("ck_referans_istegi_puan_araligi", "referans_istegi", type_="check")
    op.drop_column("referans_istegi", "puan")
