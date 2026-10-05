"""ihtiyac_karti.basari_olcutu (JSONB, nullable)

Tanımlama iyileştirmesi B: başarı kriterinin yapılandırılmış parçaları
(metrik, mevcut_deger, hedef_deger, sure, olcum_bilinmiyor). Eski kartlara
dokunulmaz: NULL kalır ve "ölçüm yöntemi belirlenecek" işareti almaz.

Revision ID: b7e3a1c9d2f5
Revises: b9e4c2a7d1f3
Create Date: 2026-10-05 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b7e3a1c9d2f5"
down_revision: str | None = "b9e4c2a7d1f3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ihtiyac_karti",
        sa.Column("basari_olcutu", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("ihtiyac_karti", "basari_olcutu")
