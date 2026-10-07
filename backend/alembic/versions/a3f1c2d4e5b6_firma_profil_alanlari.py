"""firma profil alanlari

Firma kayıt formunun alanları (docs/kararlar.md F1-F2, § 2):
tür, web sitesi, çalışan sayısı aralığı, kuruluş yılı, tanıtım, formu
dolduranın adı ve görevi. Hepsi nullable ve eklemeli: eski firma satırları
değişmez, panel onlara "Profilinizi tamamlayın" bandı gösterir (karar 9).

Revision ID: a3f1c2d4e5b6
Revises: 76b95c6a1658
Create Date: 2026-09-30
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'a3f1c2d4e5b6'
down_revision: str | None = '76b95c6a1658'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ALANLAR = (
    ('tur', sa.String()),
    ('web_sitesi', sa.String()),
    ('calisan_araligi', sa.String()),
    ('kurulus_yili', sa.Integer()),
    ('tanitim', sa.Text()),
    ('yetkili_ad', sa.String()),
    ('yetkili_gorev', sa.String()),
)


def upgrade() -> None:
    for ad, tur in ALANLAR:
        op.add_column('kurum', sa.Column(ad, tur, nullable=True))


def downgrade() -> None:
    for ad, _ in reversed(ALANLAR):
        op.drop_column('kurum', ad)
