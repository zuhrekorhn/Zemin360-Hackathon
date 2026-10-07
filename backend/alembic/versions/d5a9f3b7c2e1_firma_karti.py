"""firma karti

Firmanın yetkinlik kartı (docs/kararlar.md F10):
yeni `firma_karti` tablosu, firma başına bir kart (`kurum_id` UNIQUE).
Eklemeli; mevcut tablolara dokunulmaz.

Revision ID: d5a9f3b7c2e1
Revises: c4d8e1f2a9b5
Create Date: 2026-09-30
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = 'd5a9f3b7c2e1'
down_revision: str | None = 'c4d8e1f2a9b5'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'firma_karti',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('kurum_id', sa.UUID(), nullable=False),
        sa.Column('ne_yapiyoruz', sa.Text(), nullable=False),
        sa.Column(
            'yetkinlikler',
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column('onceki_isler', sa.Text(), nullable=True),
        sa.Column('aranan_isbirligi', sa.Text(), nullable=True),
        sa.Column(
            'isbirligi_turleri',
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column('versiyon', sa.Integer(), server_default=sa.text('1'), nullable=False),
        sa.Column('embedding', Vector(dim=1024), nullable=True),
        sa.Column('oturum_id', sa.UUID(), nullable=True),
        sa.Column(
            'olusturma_tarihi',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['kurum_id'], ['kurum.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('kurum_id'),
        sa.UniqueConstraint('oturum_id'),
    )


def downgrade() -> None:
    op.drop_table('firma_karti')
