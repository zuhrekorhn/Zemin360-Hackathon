"""referans formu: 4 soruluk yanit, geri cekme, hatirlatma

Doğrulama iyileştirmesi adım 7 (docs/plans/dogrulama-iyilestirme.md § 7, § 13).
Eski 1-5 yanıtlar `puan`'da kalır ve okunmaya devam eder; yeni yanıt ilişki ve
üç soruyla gelir. Durum CHECK'i `geri_cekildi`'yi de tanır.

Revision ID: e4a9c7b2d5f1
Revises: d8b3f6a2c4e7
Create Date: 2026-10-02 18:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e4a9c7b2d5f1"
down_revision: str | None = "d8b3f6a2c4e7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ILISKILER = ("yonetici", "takim_arkadasi", "ogretmen_danisman", "musteri", "diger")
YANITLAR = ("evet", "kismen", "hayir", "bilmiyorum")
DURUMLAR = ("bekliyor", "yanitlandi", "yanit_yok", "geri_cekildi")


def _liste(degerler: tuple[str, ...]) -> str:
    return ", ".join(f"'{d}'" for d in degerler)


def upgrade() -> None:
    op.add_column("referans_istegi", sa.Column("iliski", sa.String(), nullable=True))
    for alan in ("iddia_dogru", "pay_dogru", "sonuc_dogru"):
        op.add_column("referans_istegi", sa.Column(alan, sa.String(), nullable=True))
        op.create_check_constraint(
            f"{alan}_degeri", "referans_istegi", f"{alan} IN ({_liste(YANITLAR)})"
        )
    op.create_check_constraint(
        "iliski_degeri", "referans_istegi", f"iliski IN ({_liste(ILISKILER)})"
    )
    op.create_check_constraint(
        "durum_degeri", "referans_istegi", f"durum IN ({_liste(DURUMLAR)})"
    )
    op.add_column(
        "referans_istegi",
        sa.Column("gonderim_tarihi", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "referans_istegi",
        sa.Column("hatirlatma_tarihi", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "referans_istegi",
        sa.Column("yanit_isareti", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.execute("UPDATE referans_istegi SET durum = 'yanit_yok' WHERE durum = 'geri_cekildi'")
    for ad in ("durum_degeri", "iliski_degeri", "iddia_dogru_degeri", "pay_dogru_degeri",
               "sonuc_dogru_degeri"):
        op.drop_constraint(ad, "referans_istegi", type_="check")
    for alan in ("yanit_isareti", "hatirlatma_tarihi", "gonderim_tarihi", "sonuc_dogru",
                 "pay_dogru", "iddia_dogru", "iliski"):
        op.drop_column("referans_istegi", alan)
