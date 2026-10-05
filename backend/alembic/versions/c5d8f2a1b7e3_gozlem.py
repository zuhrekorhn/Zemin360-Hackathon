"""gozlem: kanit_gozlemi, degerlendirme_gozlemi, servis_gunlugu

Doğrulama iyileştirmesi adım 12 (docs/plans/dogrulama-iyilestirme.md § 10.3, § 14.4).
Erişim dağılımı, değerlendirme süresi / token kullanımı ve dış servis sağlığı kalıcı.

Revision ID: c5d8f2a1b7e3
Revises: b7e3a1c9d2f5
Create Date: 2026-10-05 15:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c5d8f2a1b7e3"
down_revision: str | None = "b7e3a1c9d2f5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "kanit_gozlemi",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "tarih", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("kaynak", sa.String(), nullable=False),
        sa.Column("platform", sa.String(), nullable=False),
        sa.Column("okuyucu", sa.String(), nullable=False),
        sa.Column("erisim", sa.String(), nullable=False),
        sa.Column("seviye", sa.String(), nullable=True),
        sa.Column("sure_ms", sa.Integer(), nullable=True),
        sa.Column("girdi_ozeti", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_kanit_gozlemi")),
    )
    op.create_index("ix_kanit_gozlemi_tarih", "kanit_gozlemi", ["tarih"])
    op.create_table(
        "degerlendirme_gozlemi",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "tarih", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("girdi_ozeti", sa.String(), nullable=True),
        sa.Column("parca_sayisi", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("sure_ms", sa.Integer(), nullable=False),
        sa.Column("model_cagrisi", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("girdi_token", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("cikti_token", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_degerlendirme_gozlemi")),
    )
    op.create_index("ix_degerlendirme_gozlemi_tarih", "degerlendirme_gozlemi", ["tarih"])
    op.create_table(
        "servis_gunlugu",
        sa.Column("servis", sa.String(), nullable=False),
        sa.Column("gun", sa.Date(), nullable=False),
        sa.Column("basari_sayisi", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("hata_sayisi", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("son_basari", sa.DateTime(timezone=True), nullable=True),
        sa.Column("son_hata", sa.DateTime(timezone=True), nullable=True),
        sa.Column("son_hata_turu", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("servis", "gun", name=op.f("pk_servis_gunlugu")),
    )


def downgrade() -> None:
    op.drop_table("servis_gunlugu")
    op.drop_index("ix_degerlendirme_gozlemi_tarih", table_name="degerlendirme_gozlemi")
    op.drop_table("degerlendirme_gozlemi")
    op.drop_index("ix_kanit_gozlemi_tarih", table_name="kanit_gozlemi")
    op.drop_table("kanit_gozlemi")
