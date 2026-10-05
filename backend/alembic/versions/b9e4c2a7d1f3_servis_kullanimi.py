"""servis_kullanimi: dış servislerin aylık kullanım sayacı

Doğrulama iyileştirmesi adım 11 (docs/plans/dogrulama-iyilestirme.md § 14.4).
Cloud Vision kaynak aramasının aylık tavanı kalıcı sayaçla denetlenir.

Revision ID: b9e4c2a7d1f3
Revises: a6d2e9f4b7c1
Create Date: 2026-10-05 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b9e4c2a7d1f3"
down_revision: str | None = "a6d2e9f4b7c1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "servis_kullanimi",
        sa.Column("servis", sa.String(), nullable=False),
        sa.Column("donem", sa.String(), nullable=False),
        sa.Column("sayi", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.PrimaryKeyConstraint("servis", "donem", name=op.f("pk_servis_kullanimi")),
    )


def downgrade() -> None:
    op.drop_table("servis_kullanimi")
