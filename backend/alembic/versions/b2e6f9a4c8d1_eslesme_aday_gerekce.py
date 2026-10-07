"""eslesme aday gerekcesi

Gerekçeyi yazan çağrının adaya hitaben yazdığı ikinci metin (docs/kararlar.md G9):
firmanın okuduğu gerekçe adaydan üçüncü şahısla bahsediyor ve firmaya yönelik
notlar taşıyor; genç ve aday firma bunu görür. Nullable ve eklemeli: NULL olan
kayıtta aday tarafında "Neden uygun?" gösterilmez.

Revision ID: b2e6f9a4c8d1
Revises: a7d4e2c9f1b6
Create Date: 2026-10-08
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'b2e6f9a4c8d1'
down_revision: str | None = 'a7d4e2c9f1b6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('eslesme', sa.Column('aday_gerekce_metni', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('eslesme', 'aday_gerekce_metni')
