"""inceleme isareti: GIRVAK inceleme kuyrugu

Doğrulama (docs/dogrulama.md § 9, § 13).
Plan § 9'daki on türün hepsi CHECK'te baştan tanımlı. Aynı (tür, genç, kalem)
için tek açık işaret: kısmi tekil indeks, kalemsiz işaretlerde NULL'lar eşit
sayılır (NULLS NOT DISTINCT, PostgreSQL 15+).

Revision ID: d8b3f6a2c4e7
Revises: c2e7a4f9b1d3
Create Date: 2026-10-02 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d8b3f6a2c4e7"
down_revision: str | None = "c2e7a4f9b1d3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TURLER = (
    "ayni_iddia_cok_hesapta",
    "ayni_belge_iki_hesapta",
    "gorsel_baskasinda",
    "referans_supheli",
    "belge_tutarsiz",
    "kanit_celisiyor",
    "itiraz_siniri",
    "ad_degisikligi",
    "profil_kodu_elle",
    "eposta_barkodu",
)


def upgrade() -> None:
    turler = ", ".join(f"'{t}'" for t in TURLER)
    op.create_table(
        "inceleme_isareti",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("tur", sa.String(), nullable=False),
        sa.Column(
            "kullanici_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("kullanici.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "somut_cikti_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("somut_cikti.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "ayrinti", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False
        ),
        sa.Column("durum", sa.String(), server_default="acik", nullable=False),
        sa.Column("girvak_notu", sa.Text(), nullable=True),
        sa.Column(
            "olusturma_tarihi",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("kapanma_tarihi", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(f"tur IN ({turler})", name="tur_gecerli"),
        sa.CheckConstraint("durum IN ('acik', 'kapandi', 'dogrulanamadi')", name="durum_gecerli"),
    )
    op.create_index("ix_inceleme_isareti_kullanici_id", "inceleme_isareti", ["kullanici_id"])
    op.create_index(
        "uq_inceleme_isareti_acik",
        "inceleme_isareti",
        ["tur", "kullanici_id", "somut_cikti_id"],
        unique=True,
        postgresql_where=sa.text("durum = 'acik'"),
        postgresql_nulls_not_distinct=True,
    )


def downgrade() -> None:
    op.drop_index("uq_inceleme_isareti_acik", table_name="inceleme_isareti")
    op.drop_index("ix_inceleme_isareti_kullanici_id", table_name="inceleme_isareti")
    op.drop_table("inceleme_isareti")
