"""eposta tekil

`kullanici.email` ve `kurum.iletisim_email` UNIQUE oluyor; onay anındaki
"e-postayla bul veya oluştur" artık yarışa dayanıklı bir upsert.

Kısıttan önce veri hazırlanıyor:
  1. E-postalar normalize edilir (`lower(trim(...))`, app/core/metin.py ile
     aynı kural). Boş kurum e-postası NULL olur.
  2. Aynı e-postaya sahip mükerrer satırlar birleştirilir: bağlı kartlar
     (yetenek_karti.kullanici_id, ihtiyac_karti.kurum_id) tutulan satıra
     taşınır, diğerleri silinir. Tutulan satır en küçük `id`'li olan —
     tabloda zaman damgası yok, seçim keyfi ama deterministik. Kart
     kaybolmaz; yalnızca mükerrer profil satırı gider.

Revision ID: cb9a542b6431
Revises: 7c3a9e51b8d4
Create Date: 2026-09-25 23:53:12.730420
"""
from collections.abc import Sequence

from alembic import op

revision: str = 'cb9a542b6431'
down_revision: str | None = '7c3a9e51b8d4'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (profil tablosu, e-posta kolonu, kart tablosu, kartın profil FK'si)
HEDEFLER = (
    ("kullanici", "email", "yetenek_karti", "kullanici_id"),
    ("kurum", "iletisim_email", "ihtiyac_karti", "kurum_id"),
)


def _mukerrerleri_birlestir(tablo: str, kolon: str, kart_tablosu: str, fk: str) -> None:
    tutulan = f"""
        SELECT id,
               (array_agg(id) OVER (PARTITION BY {kolon} ORDER BY id))[1] AS tutulan
        FROM {tablo}
        WHERE {kolon} IS NOT NULL
    """
    op.execute(
        f"""
        UPDATE {kart_tablosu} k SET {fk} = s.tutulan
        FROM ({tutulan}) s
        WHERE k.{fk} = s.id AND s.id <> s.tutulan
        """
    )
    op.execute(
        f"""
        DELETE FROM {tablo} t
        USING ({tutulan}) s
        WHERE t.id = s.id AND s.id <> s.tutulan
        """
    )


def upgrade() -> None:
    op.execute("UPDATE kullanici SET email = lower(trim(email))")
    op.execute(
        "UPDATE kurum SET iletisim_email = NULLIF(lower(trim(iletisim_email)), '') "
        "WHERE iletisim_email IS NOT NULL"
    )
    for hedef in HEDEFLER:
        _mukerrerleri_birlestir(*hedef)

    op.create_unique_constraint(op.f('uq_kullanici_email'), 'kullanici', ['email'])
    op.drop_index(op.f('ix_kurum_iletisim_email'), table_name='kurum')
    op.create_index(op.f('ix_kurum_iletisim_email'), 'kurum', ['iletisim_email'], unique=True)


def downgrade() -> None:
    # Birleştirilen mükerrerler ve eski yazımlar geri getirilemez; yalnızca
    # kısıtlar kalkar.
    op.drop_index(op.f('ix_kurum_iletisim_email'), table_name='kurum')
    op.create_index(op.f('ix_kurum_iletisim_email'), 'kurum', ['iletisim_email'], unique=False)
    op.drop_constraint(op.f('uq_kullanici_email'), 'kullanici', type_='unique')
