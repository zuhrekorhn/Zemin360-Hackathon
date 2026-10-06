"""eslesme uygunluk karari

Firma–firma eşleşmesinde yapay zekânın gerekçeyle birlikte verdiği uygunluk kararı
(`uygun | kismen | uygun_degil`; docs/matching-algorithm.md § 8). Nullable ve
eklemeli: NULL "bilinmiyor" demek (genç eşleşmeleri, eski kayıtlar, hata alan
çağrılar); öneri bugünkü gibi listelenir, sonraki hesapta yeniden denenir.
Değer kümesi veritabanında kısıtlanmıyor, `durum` alanındaki yaklaşımla aynı;
kural kodda (app/agents/uygunluk.py).

Revision ID: f1c8a3d5e7b9
Revises: c5d8f2a1b7e3
Create Date: 2026-10-06
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'f1c8a3d5e7b9'
down_revision: str | None = 'c5d8f2a1b7e3'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('eslesme', sa.Column('uygunluk', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('eslesme', 'uygunluk')
