"""inceleme isareti: eposta_barkodu → edevlet_barkodu

Doğrulama iyileştirmesi adım 9 (docs/plans/dogrulama-iyilestirme.md § 4.2, § 9).
Tür adı baştan yanlış yazılmıştı: işaret e-Devlet barkodlu belgenin GİRVAK
tarafından elle doğrulanmasını bekler, e-postayla ilgisi yok. Adım 9'a kadar bu
türde işaret açılmadı; yine de varsa satırlar da taşınır.

Revision ID: a6d2e9f4b7c1
Revises: f3b8d1e6c9a4
Create Date: 2026-10-03 12:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "a6d2e9f4b7c1"
down_revision: str | None = "f3b8d1e6c9a4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ORTAK = (
    "ayni_iddia_cok_hesapta",
    "ayni_belge_iki_hesapta",
    "gorsel_baskasinda",
    "referans_supheli",
    "belge_tutarsiz",
    "kanit_celisiyor",
    "itiraz_siniri",
    "ad_degisikligi",
    "profil_kodu_elle",
)
# Adlandırma kuralı (`ck_%(table_name)s_%(constraint_name)s`) drop_constraint adına da uygulanır;
# ham SQL tam adı kullanır.
_KISIT = "ck_inceleme_isareti_tur_gecerli"


def upgrade() -> None:
    op.drop_constraint("tur_gecerli", "inceleme_isareti", type_="check")
    op.execute("UPDATE inceleme_isareti SET tur = 'edevlet_barkodu' WHERE tur = 'eposta_barkodu'")
    turler = ", ".join(f"'{t}'" for t in (*_ORTAK, "edevlet_barkodu"))
    op.execute(f"ALTER TABLE inceleme_isareti ADD CONSTRAINT {_KISIT} CHECK (tur IN ({turler}))")


def downgrade() -> None:
    op.drop_constraint("tur_gecerli", "inceleme_isareti", type_="check")
    op.execute("UPDATE inceleme_isareti SET tur = 'eposta_barkodu' WHERE tur = 'edevlet_barkodu'")
    turler = ", ".join(f"'{t}'" for t in (*_ORTAK, "eposta_barkodu"))
    op.execute(f"ALTER TABLE inceleme_isareti ADD CONSTRAINT {_KISIT} CHECK (tur IN ({turler}))")
