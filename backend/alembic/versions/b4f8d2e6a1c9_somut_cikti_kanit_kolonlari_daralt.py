"""somut cikti: kanit_linki ve kanit_turu kalkar (contract)

Doğrulama (docs/dogrulama.md § 13). Genişlet → geçir → daralt'ın son adımı:
kanıt artık `kanit_parcasi`'nda (3d998c849bba kopyaladı, 2c63259'dan beri kod
yalnızca parçaları okuyup yazıyor). `kanit_turu` hiçbir yerde kullanılmıyordu;
tür, parçanın platformundan gelecek.

Kolonu dolu olup parçası olmayan kalem varsa (ör. genişletmeden sonra eski
kodla yazılmış satır) migration DURUR, hiçbir şeyi silmez: genişletme
revizyonunun kopyalaması tekrar çalıştırılabilir (idempotent). Geri alma
kolonları geri ekler ve her kalemin ilk link parçasını `kanit_linki`'ye yazar.

Revision ID: b4f8d2e6a1c9
Revises: 9e1b5d3a7c24
Create Date: 2026-10-01 20:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b4f8d2e6a1c9"
down_revision: str | None = "9e1b5d3a7c24"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    baglanti = op.get_bind()
    kalanlar = baglanti.execute(
        sa.text(
            "SELECT c.id, c.kanit_linki FROM somut_cikti c "
            "WHERE c.kanit_linki IS NOT NULL AND btrim(c.kanit_linki) <> '' "
            "AND NOT EXISTS (SELECT 1 FROM kanit_parcasi p WHERE p.somut_cikti_id = c.id)"
        )
    ).all()
    if kalanlar:
        raise RuntimeError(
            f"{len(kalanlar)} kalemin linki henüz kanıt parçasına taşınmamış. "
            "Önce 3d998c849bba revizyonunu geri alıp yeniden uygulayın (kopyalama "
            "tekrar çalışır); veri silinmez."
        )
    op.drop_column("somut_cikti", "kanit_turu")
    op.drop_column("somut_cikti", "kanit_linki")


def downgrade() -> None:
    op.add_column("somut_cikti", sa.Column("kanit_linki", sa.String(), nullable=True))
    op.add_column("somut_cikti", sa.Column("kanit_turu", sa.String(), nullable=True))
    op.execute(
        "UPDATE somut_cikti c SET kanit_linki = ("
        "  SELECT p.url FROM kanit_parcasi p"
        "  WHERE p.somut_cikti_id = c.id AND p.tur = 'link' AND p.url IS NOT NULL"
        "  ORDER BY p.olusturma_tarihi LIMIT 1"
        ")"
    )
