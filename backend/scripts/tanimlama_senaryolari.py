"""İhtiyaç sohbetinin (Tanımlama) kötü girdi senaryoları — gerçek modelle.

Sunucu ve veritabanı gerekmez: grafik bellek içi checkpointer'la kurulur,
yalnızca LLM çağrıları gerçektir. Her senaryo firmanın cevaplarını sırayla
verir; cevaplar bitince `varsayilan` cevap tekrarlanır. Sohbet taslak hazır
olunca ya da MAKS_TUR'da biter. Her senaryonun beklentileri sohbetin sonucuna
bakan küçük fonksiyonlar; karne tablo olarak basılır.

Çalıştırma (backend klasöründen):
    .venv/Scripts/python -m scripts.tanimlama_senaryolari
    .venv/Scripts/python -m scripts.tanimlama_senaryolari rol_tarifi bilmiyorum
    .venv/Scripts/python -m scripts.tanimlama_senaryolari \
        --json tests/tanimlama_senaryolari/karne.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from langgraph.checkpoint.memory import MemorySaver

from app.agents import tanimlama
from app.agents.sohbet_motoru import kullanici_mesaji

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

MAKS_TUR = 8  # sonsuz döngüye karşı emniyet


@dataclass
class Sonuc:
    """Bir sohbetin kaydı: her tur (firmanın cevabı, sistemin sonraki sorusu)."""

    turlar: list[tuple[str, str | None]] = field(default_factory=list)
    taslaklar: list[dict[str, Any]] = field(default_factory=list)
    hazir: bool = False

    @property
    def taslak(self) -> dict[str, Any]:
        return self.taslaklar[-1] if self.taslaklar else {}

    @property
    def tur_sayisi(self) -> int:
        return len(self.turlar)


Beklenti = tuple[str, Callable[[Sonuc], bool]]


@dataclass(frozen=True)
class Senaryo:
    ad: str
    cevaplar: tuple[str, ...]
    beklentiler: tuple[Beklenti, ...]
    varsayilan: str = "Bilmiyorum."
    kapi: str = "genc"


def _dolu(deger: Any) -> bool:
    return bool(deger) and deger != "belirtilmedi"


def _yer_tutucu_yok(sonuc: Sonuc) -> bool:
    """Boş alan kayda "belirtilmedi" diye girmedi (embedding'e ve gence gidiyordu)."""
    return "belirtilmedi" not in sonuc.taslak.values()


# Her senaryoya eklenen ortak beklentiler
ORTAK_BEKLENTILER: tuple[Beklenti, ...] = (("yer tutucu yok", _yer_tutucu_yok),)


def _olcut(sonuc: Sonuc) -> dict[str, Any]:
    return sonuc.taslak.get("basari_olcutu") or {}


def _olcum_ya_hedef_ya_isaret(sonuc: Sonuc) -> bool:
    """Ölçülemez kriter karta ölçülmüş gibi girmedi: hedef değer var ya da
    "ölçüm yöntemi belirlenecek" işareti konmuş."""
    olcut = _olcut(sonuc)
    return _dolu(olcut.get("hedef_deger")) or bool(olcut.get("olcum_bilinmiyor"))


SENARYOLAR: tuple[Senaryo, ...] = (
    Senaryo(
        ad="tek_cumle",
        cevaplar=(
            "Dijitalleşmek istiyoruz.",
            "Siparişleri hâlâ telefonla alıp kâğıda yazıyoruz; günde 80 sipariş geliyor "
            "ve karışıyor.",
            "Yanlış giden sipariş oranı ayda %10 civarı, 3 ay içinde %2'ye inmesini istiyoruz.",
        ),
        beklentiler=(
            ("ilk cevapla kapanmadı", lambda s: s.tur_sayisi > 1),
            ("problem dolu", lambda s: _dolu(s.taslak.get("problem_tanimi"))),
            ("kriter dolu", lambda s: _dolu(s.taslak.get("basari_kriteri"))),
            ("taslak hazır", lambda s: s.hazir),
        ),
    ),
    Senaryo(
        ad="rol_tarifi",
        cevaplar=(
            "3 yıl deneyimli bir full stack developer arıyoruz.",
            "Müşteri paneli yok; müşteriler sipariş durumunu öğrenmek için çağrı merkezini "
            "arıyor, günde 200 çağrı geliyor.",
            "6 ay içinde bu çağrıların yarısı panelden çözülsün.",
        ),
        beklentiler=(
            (
                "rol tarifi problem sayılmadı (1. tur)",
                lambda s: "developer" not in (s.taslaklar[0].get("problem_tanimi") or "").lower(),
            ),
            (
                "son problemde rol yok",
                lambda s: "developer" not in (s.taslak.get("problem_tanimi") or "").lower(),
            ),
            ("problem dolu", lambda s: _dolu(s.taslak.get("problem_tanimi"))),
            ("kriter dolu", lambda s: _dolu(s.taslak.get("basari_kriteri"))),
        ),
    ),
    Senaryo(
        ad="olculemez_kriter",
        cevaplar=(
            "Müşteri şikâyetleri çok, kargolar geç çıkıyor.",
            "Müşteri memnuniyeti artsın.",
            "Bunu ölçmüyoruz, şu an bir rakam veremeyiz.",
        ),
        beklentiler=(
            ("ölçülemez cevapta kapanmadı", lambda s: s.tur_sayisi > 2),
            ("problem dolu", lambda s: _dolu(s.taslak.get("problem_tanimi"))),
            ("hedef ya da 'belirlenecek' işareti", _olcum_ya_hedef_ya_isaret),
            ("taslak hazır", lambda s: s.hazir),
        ),
    ),
    Senaryo(
        ad="sayisiz_olculebilir",
        cevaplar=(
            "Depo sayımını elle yapıyoruz, her seferinde bir hafta sürüyor.",
            "Sayım süresi yarıya insin.",
        ),
        varsayilan="Başka bir şartımız yok.",
        beklentiler=(
            ("kriter dolu", lambda s: _dolu(s.taslak.get("basari_kriteri"))),
            ("hedef değer çıkarıldı", lambda s: _dolu(_olcut(s).get("hedef_deger"))),
            ("en çok 3 turda kapandı", lambda s: s.hazir and s.tur_sayisi <= 3),
        ),
    ),
    Senaryo(
        ad="bilmiyorum",
        cevaplar=(),
        beklentiler=(
            ("sohbet sonlandı (döngü yok)", lambda s: s.hazir),
            ("problem uydurulmadı", lambda s: not _dolu(s.taslak.get("problem_tanimi"))),
            ("kriter uydurulmadı", lambda s: not _dolu(s.taslak.get("basari_kriteri"))),
        ),
    ),
)


def _grafik(kapi: str):
    checkpointer = MemorySaver()
    if kapi == "firma":
        return tanimlama.ortak_grafik_derle(checkpointer)
    return tanimlama.grafik_derle(checkpointer)


async def calistir(senaryo: Senaryo) -> Sonuc:
    grafik = _grafik(senaryo.kapi)
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    await grafik.ainvoke({"aranan": senaryo.kapi}, config=config)

    sonuc = Sonuc()
    for sira in range(MAKS_TUR):
        cevap = senaryo.cevaplar[sira] if sira < len(senaryo.cevaplar) else senaryo.varsayilan
        durum = await grafik.ainvoke({"mesajlar": [kullanici_mesaji(cevap)]}, config=config)
        sonuc.turlar.append((cevap, durum.get("sonraki_soru")))
        sonuc.taslaklar.append(dict(durum.get("taslak") or {}))
        if durum.get("taslak_hazir"):
            sonuc.hazir = True
            break
    return sonuc


def _yazdir(senaryo: Senaryo, sonuc: Sonuc) -> dict[str, Any]:
    print(f"\n=== {senaryo.ad} ({senaryo.kapi}) — {sonuc.tur_sayisi} tur")
    for cevap, soru in sonuc.turlar:
        print(f"  F: {cevap}")
        print(f"  S: {soru or '[taslak hazır]'}")
    print(f"  taslak: {json.dumps(sonuc.taslak, ensure_ascii=False)}")
    kontroller = {}
    for ad, kontrol in (*senaryo.beklentiler, *ORTAK_BEKLENTILER):
        try:
            gecti = bool(kontrol(sonuc))
        except Exception:  # noqa: BLE001 — beklenti kırılırsa kalmış say
            gecti = False
        kontroller[ad] = gecti
        print(f"  [{'✓' if gecti else '✗'}] {ad}")
    return {
        "tur": sonuc.tur_sayisi,
        "hazir": sonuc.hazir,
        "turlar": sonuc.turlar,
        "taslak": sonuc.taslak,
        "kontroller": kontroller,
    }


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("adlar", nargs="*", help="yalnızca bu senaryolar")
    parser.add_argument("--json", type=Path, help="karneyi bu dosyaya yaz")
    args = parser.parse_args()

    secilen = [s for s in SENARYOLAR if not args.adlar or s.ad in args.adlar]
    sonuclar = await asyncio.gather(*(calistir(s) for s in secilen))

    karne = {s.ad: _yazdir(s, r) for s, r in zip(secilen, sonuclar, strict=True)}
    gecen = sum(sum(k["kontroller"].values()) for k in karne.values())
    toplam = sum(len(k["kontroller"]) for k in karne.values())
    print(f"\nKARNE: {gecen}/{toplam} beklenti")
    for ad, k in karne.items():
        print(f"  {ad:22} {sum(k['kontroller'].values())}/{len(k['kontroller'])}  ({k['tur']} tur)")

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(karne, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main())
