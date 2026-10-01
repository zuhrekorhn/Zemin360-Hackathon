"""guven gostergesi: bos baslik NULL ("—")

Doğrulama iyileştirmesi adım 3b (docs/plans/dogrulama-iyilestirme.md § 1 İ4,
bulgu 17 ve 19). Eski kod "değerlendirilmedi" ile "0 puan" arasında ayrım
yapmıyordu; iki tür sahte sıfır kaldı:

  1. Linksiz kaleme referans yanıt verince açılan gösterge: Kanıt, Sonuç, Rol
     hiç değerlendirilmeden 0 yazılıyordu. İmzası: modelin notu yok
     (rubrik her zaman not yazar) ve üç başlık da 0.
  2. Referans başlığı, güncel bir referans yanıtı yokken 0 yazılıyordu.
     Güncel yanıt: puanı var ve iş kalemi o yanıttan sonra değişmedi
     (`icerik_tarihi` boş ya da yanıt ondan sonra; genc-akisi § 0, karar 8).

Her ikisi NULL'a çevrilir. Geri alma tam tersidir (NULL → 0), veri kaybolmaz.

Revision ID: 7c4e2a9d1f63
Revises: 3d998c849bba
Create Date: 2026-10-01 16:00:00.000000
"""
from collections.abc import Sequence

from alembic import op

revision: str = "7c4e2a9d1f63"
down_revision: str | None = "3d998c849bba"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

BASLIKLAR = ("kanit_orijinalligi", "sonuc_olculebilirligi", "rol_netligi", "ucuncu_taraf_onayi")


def upgrade() -> None:
    op.execute(
        "UPDATE guven_skoru SET kanit_orijinalligi = NULL, sonuc_olculebilirligi = NULL, "
        "rol_netligi = NULL "
        "WHERE gerekce_metni IS NULL AND kanit_orijinalligi = 0 "
        "AND sonuc_olculebilirligi = 0 AND rol_netligi = 0"
    )
    op.execute(
        "UPDATE guven_skoru g SET ucuncu_taraf_onayi = NULL "
        "WHERE g.ucuncu_taraf_onayi = 0 AND NOT EXISTS ("
        "  SELECT 1 FROM referans_istegi r JOIN somut_cikti c ON c.id = r.somut_cikti_id"
        "  WHERE r.somut_cikti_id = g.somut_cikti_id AND r.puan IS NOT NULL"
        "  AND (c.icerik_tarihi IS NULL"
        "       OR (r.yanit_tarihi IS NOT NULL AND r.yanit_tarihi >= c.icerik_tarihi))"
        ")"
    )


def downgrade() -> None:
    for kolon in BASLIKLAR:
        op.execute(f"UPDATE guven_skoru SET {kolon} = 0 WHERE {kolon} IS NULL")
