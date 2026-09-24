"""Çalışma modeli: işin nerede yapıldığı.

Konum (şehir) ile çalışma modeli ayrı alanlar — LinkedIn ve Kariyer.net de
böyle ayırıyor. Önce "Uzaktan / fark etmez" şehir listesine bir seçenek olarak
konmuştu; bu, "İstanbul'da ama hibrit" gibi çok sık bir durumu ifade
edilemez kılıyordu.

Müsaitlik (tam zamanlı, yarı zamanlı, proje bazlı, staj) BAŞKA bir şey:
o çalışma tipi, bu çalışma yeri. İkisi karıştırılmamalı.
"""

from __future__ import annotations

from collections.abc import Sequence

IS_YERINDE = "is_yerinde"
HIBRIT = "hibrit"
UZAKTAN = "uzaktan"

# Sıra anlamlı: en çok konuma bağlı olandan en az bağlı olana.
MODELLER: tuple[str, ...] = (IS_YERINDE, HIBRIT, UZAKTAN)

# Şehir eşleşmesi gerektiren modeller. Uzaktan çalışmada şehrin bir hükmü yok.
SEHRE_BAGLI = frozenset({IS_YERINDE, HIBRIT})

ETIKETLER: dict[str, str] = {
    IS_YERINDE: "İş yerinde",
    HIBRIT: "Hibrit",
    UZAKTAN: "Uzaktan",
}


def gecerli_mi(model: str | None) -> bool:
    return model in MODELLER


def temizle(modeller: Sequence[str] | None) -> list[str]:
    """Tanınmayan değerleri atar, sırayı sabitler, tekrarları siler.

    Sohbetten ya da eski kayıtlardan serbest metin gelebiliyor; kartta yalnızca
    bilinen değerler dursun.
    """
    if not modeller:
        return []
    secilenler = {m for m in modeller if gecerli_mi(m)}
    return [model for model in MODELLER if model in secilenler]


def sehir_eslesmeli_mi(ihtiyac_modeli: str | None) -> bool:
    """İhtiyaç bu modeldeyken şehir filtresi uygulanmalı mı?

    Model belirtilmemişse eski davranış korunuyor: şehir tercihi varsa
    filtre uygulanır (kart tarafında model zorunlu değil).
    """
    if ihtiyac_modeli is None:
        return True
    return ihtiyac_modeli in SEHRE_BAGLI
