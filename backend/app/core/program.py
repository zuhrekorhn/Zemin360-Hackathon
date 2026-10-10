"""Zemin360 programının hedefleri ve bizim platformda neyi saydığımız
(docs/canlilik.md § 7).

Etiket iki parçalı: programın kendi adı + platformda ölçtüğümüz şey. İkisi
arasındaki fark gizlenmez: örneğin program "startup başvurusu" diyor, biz
"en az bir yetenek kartı olan genç" sayıyoruz. Program adları ya da hedefler
değişirse yalnızca bu dosya değişir; panelden düzenleme yok (kapsam dışı).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProgramHedefi:
    anahtar: str
    hedef: int
    program_adi: str
    olcum: str


HEDEFLER: tuple[ProgramHedefi, ...] = (
    ProgramHedefi(
        anahtar="basvuru",
        hedef=80,
        program_adi="startup başvurusu",
        olcum="yetenek kartı oluşturan genç",
    ),
    ProgramHedefi(
        anahtar="kurum",
        hedef=20,
        program_adi="kurum",
        olcum="ihtiyaç tanımlayan firma",
    ),
    ProgramHedefi(
        anahtar="eslesme",
        hedef=10,
        program_adi="eşleşme",
        olcum="iki tarafın da ilgilendiği (karşılıklı ilgi) eşleşme",
    ),
    ProgramHedefi(
        anahtar="pilot",
        hedef=5,
        program_adi="pilot",
        olcum="iki tarafın da tamamladığı iş birliği (her türden)",
    ),
)
