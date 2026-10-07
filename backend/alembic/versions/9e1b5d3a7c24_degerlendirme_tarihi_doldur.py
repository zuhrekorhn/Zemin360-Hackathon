"""guven gostergesi: degerlendirme_tarihi eski kayitlarda doldurulur

Doğrulama (docs/dogrulama.md § 13). "Kalem değerlendirildi mi?" artık
`degerlendirme_tarihi`'ne bakıyor (yalnızca referans yanıtıyla açılmış gösterge
değerlendirilmiş sayılmaz). Bu alandan önce rubrikten geçmiş kayıtların tarihi
boş; doldurulmazsa kart hazırlama onları yeniden puanlamaya kalkar. İmza:
rubrik her zaman not yazar (`gerekce_metni` dolu). Tarih bilinmediği için
migration anı yazılır.

Geri alma no-op: alanı bir önceki revizyon (3d998c849bba) ekledi, onun
geri alması kolonu kaldırır.

Revision ID: 9e1b5d3a7c24
Revises: 7c4e2a9d1f63
Create Date: 2026-10-01 18:00:00.000000
"""
from collections.abc import Sequence

from alembic import op

revision: str = "9e1b5d3a7c24"
down_revision: str | None = "7c4e2a9d1f63"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "UPDATE guven_skoru SET degerlendirme_tarihi = now() "
        "WHERE degerlendirme_tarihi IS NULL AND gerekce_metni IS NOT NULL"
    )


def downgrade() -> None:
    pass
