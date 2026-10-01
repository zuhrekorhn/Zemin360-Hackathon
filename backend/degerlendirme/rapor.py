"""Karneyi Markdown rapora ve gerileme karşılaştırması için JSON'a çevirir."""

from __future__ import annotations

from typing import Any

from degerlendirme.olcutler import BIREBIR_ESIGI, YAKIN_ESIGI, Karne, uyuyor_mu
from degerlendirme.vaka import BASLIKLAR, BaslikBeklentisi


def _deger(d: int | None) -> str:
    return "—" if d is None else str(d)


def _beklenti(b: BaslikBeklentisi) -> str:
    if isinstance(b, list):
        return "/".join(_deger(x) for x in b)
    return _deger(b)


def _yuzde(oran: float) -> str:
    return f"%{oran * 100:.0f}"


def markdown(karne: Karne, tarih: str) -> str:
    etiket = "TASLAK ETİKET (öneriler; Zühre'nin etiketi değil)" if karne.taslak else "etiketli"
    durum = "geçiyor" if karne.esikleri_geciyor_mu else "geçmiyor"
    satirlar = [
        f"# Karne: {karne.degerlendirici} ({tarih})",
        "",
        f"- Etiket kaynağı: **{etiket}**",
        f"- Vaka: {karne.toplam_vaka} toplam, {karne.olculen_vaka} ölçülen",
        f"- Kabul eşikleri: **{durum}**",
        f"- Sahte vakada yanlış 3: **{len(karne.sahte_yanlis_uc)}** (hedef 0)",
        f"- Bütün vakalarda yanlış 3: {len(karne.yanlis_uc)}",
        f"- Notta dil ihlali olan vaka: {len(karne.not_ihlalleri)} (hedef 0)",
        f"- Sonuç üretemeyen vaka: {len(karne.hatalar)}",
        "",
        "## Başlık başına uyum",
        "",
        f"| Başlık | Birebir (hedef {_yuzde(BIREBIR_ESIGI)}) "
        f"| ±1 (hedef {_yuzde(YAKIN_ESIGI)}) | Vaka |",
        "|---|---|---|---|",
    ]
    for ad, o in karne.basliklar.items():
        satirlar.append(f"| {ad} | {_yuzde(o.birebir)} | {_yuzde(o.yakin)} | {o.sayi} |")

    satirlar += [
        "",
        "## Alan kırılımı",
        "",
        '| Alan | Kanıt "—" oranı | Dürüst vakada ort. Kanıt |',
        "|---|---|---|",
    ]
    for alan, oran in karne.alan_tire_orani.items():
        ort = karne.alan_kanit_ortalamasi.get(alan)
        satirlar.append(f"| {alan} | {_yuzde(oran)} | {'—' if ort is None else f'{ort:.2f}'} |")

    if karne.sahte_yanlis_uc or karne.yanlis_uc:
        satirlar += ["", "## Yanlış 3", ""]
        satirlar += [
            f"- {v}{' (kötü niyetli)' if v in karne.sahte_yanlis_uc else ''}"
            for v in karne.yanlis_uc
        ]
    if karne.not_ihlalleri:
        satirlar += ["", "## Notta dil ihlalleri", ""]
        satirlar += [f"- {v}: {', '.join(i)}" for v, i in karne.not_ihlalleri.items()]
    if karne.hatalar:
        satirlar += ["", "## Sonuç üretemeyen vakalar", ""]
        satirlar += [f"- {v}: {h}" for v, h in karne.hatalar.items()]

    satirlar += [
        "",
        "## Vakalar",
        "",
        "Hücre: sistem / beklenen. ✗ uyuşmayan başlık.",
        "",
        "| Vaka | Alan | Kanıt | Sonuç | Rol | Referans |",
        "|---|---|---|---|---|---|",
    ]
    for s in karne.sonuclar:
        beklenen = s.vaka.etiket(karne.taslak)
        hucreler = []
        for b in BASLIKLAR:
            deger = s.degerlendirme.baslik(b)
            if beklenen is None:
                hucreler.append(_deger(deger))
                continue
            beklenti = beklenen.baslik(b)
            isaret = "" if uyuyor_mu(beklenti, deger) and not s.degerlendirme.hata else " ✗"
            hucreler.append(f"{_deger(deger)} / {_beklenti(beklenti)}{isaret}")
        ad = s.vaka.id + (" ⚠" if s.vaka.kotu_niyetli else "")
        satirlar.append(f"| {ad} | {s.vaka.alan.value} | " + " | ".join(hucreler) + " |")
    return "\n".join(satirlar) + "\n"


def anlik_goruntu(karne: Karne) -> dict[str, Any]:
    """Vaka başına sonuçlar; bir adım davranışı değiştirmemeliyse bununla karşılaştırılır."""
    return {s.vaka.id: s.degerlendirme.ozet() for s in karne.sonuclar}
