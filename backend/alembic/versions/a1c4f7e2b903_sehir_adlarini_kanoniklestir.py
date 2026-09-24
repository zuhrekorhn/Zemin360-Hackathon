"""sehir adlarini kanonik yazima cevir

Eşleştirme'nin sert şehir filtresi düz string karşılaştırması yapıyor ve
Türkçe'de "istanbul" ile "İstanbul" eşleşmiyor (`lower()` ve `ILIKE` de
çözmüyor — ayrıntı app/core/sehir.py). Yeni kayıtlar `sehir_kanonik()`
üzerinden geçiyor; bu migration eski kayıtları aynı biçime çekiyor.

Veri migration'ı: şema değişmiyor.

Revision ID: a1c4f7e2b903
Revises: b4612ec38a95
Create Date: 2026-09-24
"""

from collections.abc import Sequence

import pgvector.sqlalchemy  # noqa: F401  (Vector kolonları için)
import sqlalchemy as sa
from alembic import op

from app.core.sehir import sehir_kanonik

revision: str = "a1c4f7e2b903"
down_revision: str | None = "b4612ec38a95"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (tablo, kolon) — şehir tutan her yer
HEDEFLER = (
    ("kullanici", "sehir"),
    ("kurum", "sehir"),
    ("ihtiyac_karti", "sehir_tercihi"),
)


def upgrade() -> None:
    baglanti = op.get_bind()
    for tablo, kolon in HEDEFLER:
        satirlar = baglanti.execute(
            sa.text(f"SELECT id, {kolon} FROM {tablo} WHERE {kolon} IS NOT NULL")  # noqa: S608
        ).fetchall()
        for kimlik, deger in satirlar:
            kanonik = sehir_kanonik(deger)
            if kanonik != deger:
                baglanti.execute(
                    sa.text(f"UPDATE {tablo} SET {kolon} = :yeni WHERE id = :id"),  # noqa: S608
                    {"yeni": kanonik, "id": kimlik},
                )


def downgrade() -> None:
    # Eski yazımlar geri alınamaz (hangi kaydın nasıl yazıldığı bilgisi yok)
    # ve kanonik yazım zaten doğru olan. Geri alma bilinçli olarak boş.
    pass
