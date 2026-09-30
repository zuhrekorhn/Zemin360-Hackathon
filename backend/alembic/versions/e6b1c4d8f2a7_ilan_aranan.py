"""ilan aranan

İlanın kimi aradığı (docs/plans/firma-akisi.md § 0 kararlar 4-5, § 2):
`ihtiyac_karti.aranan` (`genc | firma`, varsayılan `genc`; mevcut ilanlar genç
ilanı), `aranan_firma_turleri` (boş = hepsi; yalnızca ortak ilanında) ve
`isbirligi_turu` (ortak ilanında, isteğe bağlı). Eklemeli.

Revision ID: e6b1c4d8f2a7
Revises: d5a9f3b7c2e1
Create Date: 2026-09-30
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = 'e6b1c4d8f2a7'
down_revision: str | None = 'd5a9f3b7c2e1'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'ihtiyac_karti',
        sa.Column('aranan', sa.String(), server_default=sa.text("'genc'"), nullable=False),
    )
    op.add_column(
        'ihtiyac_karti',
        sa.Column(
            'aranan_firma_turleri',
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
    )
    op.add_column('ihtiyac_karti', sa.Column('isbirligi_turu', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('ihtiyac_karti', 'isbirligi_turu')
    op.drop_column('ihtiyac_karti', 'aranan_firma_turleri')
    op.drop_column('ihtiyac_karti', 'aranan')
