"""musaitlik degerlerini koda cevir

Eşleştirme'nin müsaitlik filtresi düz eşitlik yapıyor. Tanımlama Ajanı serbest
metin yazabildiği için ("tam zamanlı") ihtiyaç kartı gencin `tam_zamanli`
koduyla eşleşmiyor ve tüm adaylar sessizce eleniyordu. Yeni kayıtlar artık
koda çevriliyor (app/core/musaitlik.py); bu migration eski satırları aynı
biçime çekiyor.

Tanınmayan değer NULL oluyor: NULL "tercih yok" demek, filtre uygulanmaz.
Bu havuzu daraltmaz, genişletir — yanlış bir değerle herkesi elemekten iyi.

Veri migration'ı: şema değişmiyor.

Revision ID: 7c3a9e51b8d4
Revises: e837db70015c
Create Date: 2026-09-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.core.musaitlik import musaitlik_kanonik

revision: str = "7c3a9e51b8d4"
down_revision: str | None = "e837db70015c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

HEDEFLER = (
    ("kullanici", "musaitlik"),
    ("ihtiyac_karti", "musaitlik_tercihi"),
)


def upgrade() -> None:
    baglanti = op.get_bind()
    for tablo, kolon in HEDEFLER:
        satirlar = baglanti.execute(
            sa.text(f"SELECT id, {kolon} FROM {tablo} WHERE {kolon} IS NOT NULL")  # noqa: S608
        ).fetchall()
        for kimlik, deger in satirlar:
            kod = musaitlik_kanonik(deger)
            if kod != deger:
                baglanti.execute(
                    sa.text(f"UPDATE {tablo} SET {kolon} = :yeni WHERE id = :id"),  # noqa: S608
                    {"yeni": kod, "id": kimlik},
                )


def downgrade() -> None:
    # Eski serbest metin geri getirilemez (hangi yazımın kullanıldığı kayıtlı
    # değil) ve kod zaten doğru olan. Geri alma bilinçli olarak boş.
    pass
