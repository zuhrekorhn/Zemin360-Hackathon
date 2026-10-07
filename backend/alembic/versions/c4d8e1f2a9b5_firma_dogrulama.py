"""firma dogrulama

Firma doğrulaması (docs/kararlar.md F6):
`kurum.dogrulama_durumu` (`bekliyor | dogrulandi | simdilik_degil`, varsayılan
`bekliyor`) ve GİRVAK'ın karar anı `dogrulama_tarihi`. Mevcut firmalar
`bekliyor` olur: hiçbiri henüz doğrulanmadı. Alan adı ipucu saklanmaz.

Revision ID: c4d8e1f2a9b5
Revises: b7e2d9c1a4f3
Create Date: 2026-09-30
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'c4d8e1f2a9b5'
down_revision: str | None = 'b7e2d9c1a4f3'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'kurum',
        sa.Column(
            'dogrulama_durumu',
            sa.String(),
            server_default=sa.text("'bekliyor'"),
            nullable=False,
        ),
    )
    op.add_column(
        'kurum', sa.Column('dogrulama_tarihi', sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('kurum', 'dogrulama_tarihi')
    op.drop_column('kurum', 'dogrulama_durumu')
