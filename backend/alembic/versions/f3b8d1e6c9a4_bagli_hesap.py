"""bagli hesap ve profil kodu

Doğrulama iyileştirmesi adım 8 (docs/plans/dogrulama-iyilestirme.md § 6, § 13).
Bağlı hesaptaki çalışma seviye B'dir. Bir platform hesabı iki gence bağlanamaz.

Revision ID: f3b8d1e6c9a4
Revises: e4a9c7b2d5f1
Create Date: 2026-10-02 22:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f3b8d1e6c9a4"
down_revision: str | None = "e4a9c7b2d5f1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Migration kendi listesini taşır: uygulama sabitleri değişse de geçmiş aynı kalır.
SAGLAYICILAR = (
    "github",
    "gitlab",
    "orcid",
    "youtube",
    "kaggle",
    "behance",
    "dribbble",
    "medium",
    "vimeo",
    "soundcloud",
    "kisisel_site",
)
YONTEMLER = ("oauth", "profil_kodu", "elle")


def _liste(degerler: tuple[str, ...]) -> str:
    return ", ".join(f"'{d}'" for d in degerler)


def _kimlik() -> sa.Column:
    return sa.Column(
        "id",
        postgresql.UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )


def _kullanici() -> sa.Column:
    return sa.Column(
        "kullanici_id",
        postgresql.UUID(as_uuid=True),
        sa.ForeignKey("kullanici.id", ondelete="CASCADE"),
        nullable=False,
    )


def upgrade() -> None:
    op.create_table(
        "bagli_hesap",
        _kimlik(),
        _kullanici(),
        sa.Column("saglayici", sa.String(), nullable=False),
        sa.Column("kullanici_adi", sa.String(), nullable=False),
        sa.Column("dis_kimlik", sa.String(), nullable=False),
        sa.Column("yontem", sa.String(), nullable=False),
        sa.Column(
            "baglanma_tarihi",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("saglayici", "dis_kimlik", name="uq_bagli_hesap_dis_kimlik"),
        sa.CheckConstraint(f"saglayici IN ({_liste(SAGLAYICILAR)})", name="saglayici_gecerli"),
        sa.CheckConstraint(f"yontem IN ({_liste(YONTEMLER)})", name="yontem_gecerli"),
    )
    op.create_index("ix_bagli_hesap_kullanici_id", "bagli_hesap", ["kullanici_id"])
    op.create_table(
        "profil_kodu",
        _kimlik(),
        _kullanici(),
        sa.Column("platform", sa.String(), nullable=False),
        sa.Column("kod", sa.String(), nullable=False),
        sa.Column("profil_adresi", sa.String(), nullable=False),
        sa.Column("son_gecerlilik", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("kullanici_id", "platform", name="uq_profil_kodu_platform"),
        sa.CheckConstraint(f"platform IN ({_liste(SAGLAYICILAR)})", name="platform_gecerli"),
    )


def downgrade() -> None:
    op.drop_table("profil_kodu")
    op.drop_index("ix_bagli_hesap_kullanici_id", table_name="bagli_hesap")
    op.drop_table("bagli_hesap")
