"""Canlı karne ile kayıtlı karne arasındaki sapma (plan § 10.1, § 16). Saf: ağ ve dosya yok.

Kayıtlı (kasetli) karne dondurulmuş sayfalar ve model yanıtlarıyla ölçer; canlı
karne bugünün sayfaları ve bugünün modeliyle. İkisinin farkı iki şeyin habercisidir:
link çürümesi / sayfa değişimi ve model kayması. Bu yüzden vaka başına hangi
başlığın neden değiştiği görünür. Fark bir kapı değil, bir uyarıdır; kapı canlı
karnenin kabul eşikleridir (`Karne.esikleri_geciyor_mu`).
"""

from __future__ import annotations

from dataclasses import dataclass

from degerlendirme.olcutler import VakaSonucu
from degerlendirme.vaka import BASLIKLAR


@dataclass(frozen=True)
class Sapma:
    vaka_id: str
    alan: str
    # Başlık → (kayıtlı, canlı); yalnızca değişenler
    degisen: dict[str, tuple[int | None, int | None]]
    # Canlıda sonuç üretilemediyse nedeni (zaman aşımı, ağ hatası…)
    canli_hata: str | None = None


def sapmalari_bul(kayitli: list[VakaSonucu], canli: list[VakaSonucu]) -> list[Sapma]:
    """Aynı kimlikli vakaları karşılaştırır; yalnızca farklı olanları döner (kimliğe göre)."""
    kayitli_kimlik = {s.vaka.id: s for s in kayitli}
    sapmalar = []
    for s in canli:
        onceki = kayitli_kimlik.get(s.vaka.id)
        if onceki is None:
            continue
        degisen = {
            b: (onceki.degerlendirme.baslik(b), s.degerlendirme.baslik(b))
            for b in BASLIKLAR
            if onceki.degerlendirme.baslik(b) != s.degerlendirme.baslik(b)
        }
        if degisen or s.degerlendirme.hata:
            sapmalar.append(Sapma(s.vaka.id, s.vaka.alan.value, degisen, s.degerlendirme.hata))
    return sorted(sapmalar, key=lambda x: x.vaka_id)


def _deger(d: int | None) -> str:
    return "—" if d is None else str(d)


def sapma_bolumu(sapmalar: list[Sapma], toplam: int) -> list[str]:
    """Markdown satırları: kaç vakada fark var ve hangi başlıkta."""
    satirlar = [
        "",
        "## Kayıttan sapma",
        "",
        "Canlı sonuç ile kayıtlı karne (dondurulmuş sayfalar ve model yanıtları) arasındaki fark. "
        "Sayfa değişimi, link çürümesi ve model kayması burada görünür.",
        "",
        f"Sapan vaka: **{len(sapmalar)}** / {toplam}",
    ]
    if not sapmalar:
        return satirlar
    satirlar += [
        "",
        "| Vaka | Alan | Değişen (kayıtlı → canlı) | Canlı hata |",
        "|---|---|---|---|",
    ]
    for s in sapmalar:
        fark = "; ".join(f"{b}: {_deger(a)} → {_deger(c)}" for b, (a, c) in s.degisen.items())
        satirlar.append(f"| {s.vaka_id} | {s.alan} | {fark or '—'} | {s.canli_hata or ''} |")
    return satirlar
