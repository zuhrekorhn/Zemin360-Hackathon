"""yetenek karti genc basina tek

Bir gencin tek yetenek kartı olur (madde 7, 1 Eki): genç kartını düzenler ve
çalışma ekleyerek güçlendirir. Kural veritabanında: uygulamadaki kontrol
eşzamanlı iki onayda yarışa açık. Tekillik indeksi aramaları da karşıladığı
için eski `ix_yetenek_karti_kullanici_id` kaldırılır.

Tekrar eden kart varsa migration DURUR, hiçbir veriyi kendisi silmez: kartı
silmek eşleşme, ilgi ve iş birliği kayıtlarını da götürür; hangisinin
kalacağı insanın kararı. Yerelde temiz başlangıç: scripts/yerel_sifirla.py.

Revision ID: a3d7e1c9b5f2
Revises: f7c2a5e9d3b1
Create Date: 2026-10-01 00:30:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a3d7e1c9b5f2"
down_revision: str | None = "f7c2a5e9d3b1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TEKRAR_EDEN_GENCLER = sa.text(
    "SELECT count(*) FROM ("
    "  SELECT kullanici_id FROM yetenek_karti GROUP BY kullanici_id HAVING count(*) > 1"
    ") AS tekrar"
)


def upgrade() -> None:
    tekrar = op.get_bind().execute(TEKRAR_EDEN_GENCLER).scalar_one()
    if tekrar:
        raise RuntimeError(
            f"{tekrar} gencin birden fazla yetenek kartı var; tekillik kuralı kurulamaz. "
            "Migration veri silmez: hangi kartın kalacağına karar verip fazlasını silin "
            "(yerelde: scripts/yerel_sifirla.py), sonra yeniden çalıştırın."
        )
    op.drop_index(op.f("ix_yetenek_karti_kullanici_id"), table_name="yetenek_karti")
    op.create_unique_constraint(
        op.f("uq_yetenek_karti_kullanici_id"), "yetenek_karti", ["kullanici_id"]
    )


def downgrade() -> None:
    op.drop_constraint(op.f("uq_yetenek_karti_kullanici_id"), "yetenek_karti", type_="unique")
    op.create_index(
        op.f("ix_yetenek_karti_kullanici_id"), "yetenek_karti", ["kullanici_id"], unique=False
    )
