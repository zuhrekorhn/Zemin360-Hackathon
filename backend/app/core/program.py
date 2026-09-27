"""Zemin360 programının hedefleri ve bizim platformda neyi saydığımız
(docs/faz-d-canlilik.md § 7).

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
        olcum="en az bir yetenek kartı olan genç",
    ),
    ProgramHedefi(
        anahtar="kurum",
        hedef=20,
        program_adi="kurum",
        olcum="en az bir ihtiyaç kartı olan kurum",
    ),
    ProgramHedefi(
        anahtar="eslesme",
        hedef=10,
        program_adi="eşleşme",
        olcum="gencin kabul ettiği (karşılıklı onaylı) eşleşme",
    ),
    ProgramHedefi(
        anahtar="pilot",
        hedef=5,
        program_adi="pilot",
        olcum="iki tarafça tamamlanmış iş birliği",
    ),
)
