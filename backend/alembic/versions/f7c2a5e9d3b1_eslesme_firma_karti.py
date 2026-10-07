"""eslesme firma karti

Firma–firma eşleşme (docs/kararlar.md F11): aynı `eslesme`
tablosu. `yetenek_karti_id` nullable olur, yanına nullable `firma_karti_id`
gelir; bir satırda **tam biri** dolu (CHECK). Ayrı UNIQUE
`(ihtiyac_karti_id, firma_karti_id)`: pipeline'ın ON CONFLICT'i firma
adayında buna dayanır. Mevcut satırların hepsinde yetenek kartı dolu, CHECK'i
geçer; veri değişmez.

Geri alma firma eşleşmelerini siler (yetenek kartı olmadan NOT NULL'a dönülemez).

Revision ID: f7c2a5e9d3b1
Revises: e6b1c4d8f2a7
Create Date: 2026-09-30
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'f7c2a5e9d3b1'
down_revision: str | None = 'e6b1c4d8f2a7'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column('eslesme', 'yetenek_karti_id', existing_type=sa.UUID(), nullable=True)
    op.add_column('eslesme', sa.Column('firma_karti_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'eslesme_firma_karti_id_fkey',
        'eslesme',
        'firma_karti',
        ['firma_karti_id'],
        ['id'],
        ondelete='CASCADE',
    )
    op.create_index('ix_eslesme_firma_karti_id', 'eslesme', ['firma_karti_id'])
    op.create_unique_constraint(
        'eslesme_ihtiyac_karti_id_firma_karti_id_key',
        'eslesme',
        ['ihtiyac_karti_id', 'firma_karti_id'],
    )
    op.create_check_constraint(
        'eslesme_tek_aday',
        'eslesme',
        'num_nonnulls(yetenek_karti_id, firma_karti_id) = 1',
    )


def downgrade() -> None:
    op.drop_constraint('eslesme_tek_aday', 'eslesme', type_='check')
    op.drop_constraint('eslesme_ihtiyac_karti_id_firma_karti_id_key', 'eslesme', type_='unique')
    op.drop_index('ix_eslesme_firma_karti_id', table_name='eslesme')
    op.drop_constraint('eslesme_firma_karti_id_fkey', 'eslesme', type_='foreignkey')
    op.execute('DELETE FROM eslesme WHERE yetenek_karti_id IS NULL')
    op.drop_column('eslesme', 'firma_karti_id')
    op.alter_column('eslesme', 'yetenek_karti_id', existing_type=sa.UUID(), nullable=False)
