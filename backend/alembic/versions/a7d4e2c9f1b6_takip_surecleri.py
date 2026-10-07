"""takip surecleri

İş birliğinin süreç şablonu ve erken sonlanması, adımın şablon anahtarı ve
hazırlık önerisi (docs/kararlar.md T1). Hepsi nullable ve eklemeli:
eski kayıtlarda `surec` ve `asama` boş kalır, sayfa onları bugünkü gibi gösterir.
Değer kümeleri veritabanında kısıtlanmıyor, kural kodda
(app/agents/takip_surecleri.py, app/agents/takip_durumu.py).

Revision ID: a7d4e2c9f1b6
Revises: f1c8a3d5e7b9
Create Date: 2026-10-06
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'a7d4e2c9f1b6'
down_revision: str | None = 'f1c8a3d5e7b9'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('isbirligi', sa.Column('surec', sa.String(), nullable=True))
    op.add_column('isbirligi', sa.Column('sonlanma_nedeni', sa.String(), nullable=True))
    op.add_column(
        'isbirligi', sa.Column('sonlanma_tarihi', sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column('milestone', sa.Column('asama', sa.String(), nullable=True))
    op.add_column('milestone', sa.Column('oneri', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('milestone', 'oneri')
    op.drop_column('milestone', 'asama')
    op.drop_column('isbirligi', 'sonlanma_tarihi')
    op.drop_column('isbirligi', 'sonlanma_nedeni')
    op.drop_column('isbirligi', 'surec')
