"""eslesme (ihtiyac_karti_id, yetenek_karti_id) tekil

Arka plan eşleştirmesi ile GET /oneriler aynı anda çalışınca aynı çift için
iki satır açılabiliyordu. Kısıt eklenmeden önce mevcut mükerrerler temizlenir.

Hangi satır kalır (sırayla): iş birliğine dönüşmüş olan, kurumun karar
verdiği (`durum != 'onerildi'`), gerekçesi olan, skoru yüksek olan. Kurumun
verdiği bir karar ya da açılmış bir iş birliği silinmesin diye.

Revision ID: 5b1e8c4d2a70
Revises: 0e3cd1cd3fdf
Create Date: 2026-09-25
"""

from collections.abc import Sequence

from alembic import op

revision: str = "5b1e8c4d2a70"
down_revision: str | None = "0e3cd1cd3fdf"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        DELETE FROM eslesme e
        USING (
            SELECT
                es.id,
                row_number() OVER (
                    PARTITION BY es.ihtiyac_karti_id, es.yetenek_karti_id
                    ORDER BY
                        (ib.id IS NOT NULL) DESC,
                        (es.durum <> 'onerildi') DESC,
                        (es.gerekce_metni IS NOT NULL) DESC,
                        es.skor DESC,
                        es.id
                ) AS sira
            FROM eslesme es
            LEFT JOIN isbirligi ib ON ib.eslesme_id = es.id
        ) s
        WHERE e.id = s.id AND s.sira > 1
        """
    )
    op.create_unique_constraint(
        op.f("uq_eslesme_ihtiyac_karti_id"),
        "eslesme",
        ["ihtiyac_karti_id", "yetenek_karti_id"],
    )


def downgrade() -> None:
    # Silinen mükerrerler geri getirilemez; yalnızca kısıt kalkar.
    op.drop_constraint(op.f("uq_eslesme_ihtiyac_karti_id"), "eslesme", type_="unique")
