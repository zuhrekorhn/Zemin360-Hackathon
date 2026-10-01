"""eposta dogrulama: hesap.eposta_dogrulandi_tarihi ve eposta_dogrulama tablosu

Doğrulama iyileştirmesi adım 6 (docs/plans/dogrulama-iyilestirme.md § 6.3,
bulgu 37). Var olan hesaplar doğrulanmamış başlar (NULL); doğrulama girişi
engellemez, yalnızca ad kilidini ve ada dayalı seviye A koşulunu açar.

Revision ID: c2e7a4f9b1d3
Revises: b4f8d2e6a1c9
Create Date: 2026-10-02 10:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c2e7a4f9b1d3"
down_revision: str | None = "b4f8d2e6a1c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "hesap", sa.Column("eposta_dogrulandi_tarihi", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_table(
        "eposta_dogrulama",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "hesap_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("hesap.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_ozeti", sa.String(), nullable=False, unique=True),
        sa.Column("son_gecerlilik", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "olusturma_tarihi",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_eposta_dogrulama_hesap_id", "eposta_dogrulama", ["hesap_id"])


def downgrade() -> None:
    op.drop_index("ix_eposta_dogrulama_hesap_id", table_name="eposta_dogrulama")
    op.drop_table("eposta_dogrulama")
    op.drop_column("hesap", "eposta_dogrulandi_tarihi")
