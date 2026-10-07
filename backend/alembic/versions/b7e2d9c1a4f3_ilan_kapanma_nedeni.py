"""ilan kapanma nedeni

İlan kapatma düğmesi (docs/kararlar.md F7):
`ihtiyac_karti.kapanma_nedeni` (`platformda_bulundu | baska_yoldan_bulundu |
vazgecildi`) ve `kapanma_tarihi`. İkisi de nullable ve eklemeli; açık ilanlarda
boş. Kural kodda (app/core/ilan.py); değer kümesi veritabanında kısıtlanmıyor,
`durum` alanındaki yaklaşımla aynı.

Revision ID: b7e2d9c1a4f3
Revises: a3f1c2d4e5b6
Create Date: 2026-09-30
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'b7e2d9c1a4f3'
down_revision: str | None = 'a3f1c2d4e5b6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('ihtiyac_karti', sa.Column('kapanma_nedeni', sa.String(), nullable=True))
    op.add_column(
        'ihtiyac_karti', sa.Column('kapanma_tarihi', sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('ihtiyac_karti', 'kapanma_tarihi')
    op.drop_column('ihtiyac_karti', 'kapanma_nedeni')
