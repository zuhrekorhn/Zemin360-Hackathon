"""musaitlik coklu secim

Gencin müsaitliği tek değerden çoklu seçime döner (docs/plans/genc-akisi.md
§ 0, karar 2): `kullanici.musaitlik` → `kullanici.musaitlikler text[]`.

Veri geçişi: dolu tekil değer tek elemanlı listeye taşınır, NULL boş liste
olur. Davranış değişikliği (onaylı): eskiden NULL müsaitlikli genç, tercihi
olan ihtiyaçta düz eşitlikle eleniyordu; boş liste artık "belirtilmedi"
sayılır ve elenmez (çalışma modelindeki kural).
Değerler zaten kanonik kod (7c3a9e51b8d4). Geri alma listenin ilk elemanını
tekil alana yazar; ikinci ve sonraki seçimler kaybolur.

Revision ID: 76b95c6a1658
Revises: 1542a11a35a5
Create Date: 2026-09-28
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '76b95c6a1658'
down_revision: str | None = '1542a11a35a5'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'kullanici',
        sa.Column(
            'musaitlikler',
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
    )
    op.execute(
        "UPDATE kullanici SET musaitlikler = ARRAY[musaitlik] "
        "WHERE musaitlik IS NOT NULL AND musaitlik <> ''"
    )
    op.drop_column('kullanici', 'musaitlik')


def downgrade() -> None:
    op.add_column('kullanici', sa.Column('musaitlik', sa.VARCHAR(), nullable=True))
    op.execute("UPDATE kullanici SET musaitlik = musaitlikler[1]")
    op.drop_column('kullanici', 'musaitlikler')
