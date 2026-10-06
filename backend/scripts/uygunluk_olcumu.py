"""Uygunluk kararı ölçümü (TASLAK, üretim koduna dokunmaz, veritabanına yazmaz).

Soru: gerekçeyi üreten model aynı çağrıda "uygun / kismen / uygun_degil" kararını
doğru verebiliyor mu, iyi bir adayı yanlışlıkla eliyor mu? Çıktı şeması
`{gerekce, uygunluk}` (gerekçe önce), istem üretimdeki gerekçe isteminin üstüne bir ek.

Veri: `tests/degerlendirme_seti/eslestirme_uygunluk/*.json`. Havuz çiftleri yalnızca
üretimdeki koşulu geçenler (benzerlik tabanı: genç 0.48, firma 0.52); demo vakaları
tabandan bağımsız, etiketli çiftlerin hepsi. Gerçek Voyage ve gerçek LLM çağrısı yapar.

    python -m scripts.uygunluk_olcumu --kuru            # çağrı yapmadan çiftleri ve ilk istemi göster
    python -m scripts.uygunluk_olcumu --calistirma 3    # asıl ölçüm
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import re
import sys
import tempfile
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Literal

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

import app.models  # noqa: F401  (tüm eşlemeler yüklensin)
from app.agents import eslestirme as E
from app.core.embeddings import (
    embedding_listesi_uret,
    firma_temsil_metni,
    ihtiyac_temsil_metni,
    yetenek_temsil_metni,
)
from app.core.firma_dogrulama import DOGRULANDI
from app.core.llm import HizSinirHatasi, ModelMesgulHatasi, kullanim_topla, llm_hatasini_cevir, yedekli_zincir
from app.core.metin import turkce_kucult
from app.models.firma_karti import FirmaKarti
from app.models.ihtiyac_karti import IhtiyacKarti
from app.models.kurum import Kurum
from app.models.somut_cikti import SomutCikti
from app.models.yetenek_karti import YetenekKarti

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

VERI = Path(__file__).resolve().parent.parent / "tests" / "degerlendirme_seti" / "eslestirme_uygunluk"
BEKLENEN = {2: "uygun", 1: "kismen", 0: "uygun_degil"}
KARARLAR = ("uygun", "kismen", "uygun_degil")
# Demo veritabanında GİRVAK'ın doğruladığı firmalar (güven bilgisi satırı için).
DOGRULANMIS_DEMO_FIRMALAR = {"Tazele Analitik", "Ayaz Sensör Teknolojileri"}

# --- Taslak şema ve istem ------------------------------------------------------------


class UygunlukKarari(BaseModel):
    # Alan sırası önemli: model önce gerekçeyi yazar, karar yazdığı metne dayanır.
    gerekce: str = Field(description="2-3 cümlelik gerekçe; adayın ihtiyaca karşılık veren ve eksik kalan yanları")
    uygunluk: Literal["uygun", "kismen", "uygun_degil"] = Field(description="Gerekçeyle tutarlı uygunluk kararı")


EK_KURAL = """

UYGUNLUK KARARI (gerekçeden sonra, ayrı alan):
Bu aday listeye girmiş olsa da gerçekten uygun olmayabilir: gerekçeyi, adayın ilanın temel
ihtiyacına gerçekte ne kadar karşılık verdiğini dürüstçe anlatarak yaz; olumlu görünmeye çalışma.
- "uygun": ilanın temel ihtiyacına karşılık gelen somut bir yetkinlik ya da iş kartta yazıyor.
- "kismen": ilanın temel ihtiyacına komşu bir yetkinlik ya da iş var ama ihtiyacın kendisini
  karşıladığı kartta görünmüyor; ya da emin değilsin.
- "uygun_degil": ilanın temel ihtiyacına karşılık gelen bir yetkinlik yazamıyorsan (aday yalnızca
  aynı alanda çalışıyor, aynı sorunu yaşıyor ya da konuyla ilgisiz).
Emin değilsen "kismen" seç. Gerekçede temel ihtiyaca karşılık gelen bir yetkinliğin kartta
olmadığını yazdıysan karar "uygun" olamaz.
"""


def sablon(tur: str) -> ChatPromptTemplate:
    genc = tur == "genc"
    uretim = E.GEREKCE_SABLONU if genc else E.FIRMA_GEREKCE_SABLONU
    talimat = (E.GEREKCE_TALIMATI if genc else E.FIRMA_GEREKCE_TALIMATI) + EK_KURAL
    insan = uretim.messages[1].prompt.template
    assert "Bu eşleşmenin gerekçesini yaz." in insan
    insan = insan.replace("Bu eşleşmenin gerekçesini yaz.", "Bu eşleşmenin gerekçesini ve uygunluk kararını ver.")
    return ChatPromptTemplate.from_messages([("system", talimat), ("human", insan)])


def zincir(tur: str):
    return yedekli_zincir(
        "guclu", f"uygunluk_olcumu_{tur}", lambda m: sablon(tur) | m.with_structured_output(UygunlukKarari)
    )


# --- Veri -> üretim nesneleri ---------------------------------------------------------


def ilan_nesnesi(d: dict) -> IhtiyacKarti:
    return IhtiyacKarti(
        problem_tanimi=d["problem"],
        basari_kriteri=d.get("basari_kriteri"),
        kisitlar=d.get("kisitlar"),
        isbirligi_turu=d.get("isbirligi_turu"),
    )


def genc_nesnesi(d: dict) -> YetenekKarti:
    return YetenekKarti(
        rol_alani=d["rol"],
        deneyim_seviyesi=d["deneyim"],
        sektor_ilgi_alani=d["sektorler"],
        araclar_teknolojiler=d["araclar"],
        somut_ciktilar=[
            SomutCikti(
                baslik=c["baslik"],
                aciklama=c.get("aciklama"),
                kendi_rolu=c.get("kendi_rolu"),
                olculebilir_sonuc=c.get("olculebilir_sonuc"),
            )
            for c in d["ciktilar"]
        ],
    )


def firma_nesnesi(ad: str, d: dict) -> E.FirmaAdayi:
    kurum = Kurum(
        ad=ad,
        tur=d.get("tur"),
        sektor=d.get("sektor"),
        dogrulama_durumu=DOGRULANDI if ad in DOGRULANMIS_DEMO_FIRMALAR else None,
    )
    kart = FirmaKarti(
        ne_yapiyoruz=d["ne_yapiyoruz"], yetkinlikler=d["yetkinlikler"], onceki_isler=d.get("onceki_isler"), kurum=kurum
    )
    return E.FirmaAdayi(firma_karti=kart, benzerlik=0.0, dogrulama_bonus=0.0)


def girdi_olustur(cift: dict) -> dict:
    ilan = ilan_nesnesi(cift["ilan"])
    if cift["tur"] == "genc":
        return E.gerekce_girdileri(ilan, genc_nesnesi(cift["aday"]))
    return E.firma_gerekce_girdileri(ilan, firma_nesnesi(cift["aday_adi"], cift["aday"]))


def temsil_metinleri(tur: str, ilanlar: dict, adaylar: dict) -> tuple[dict, dict]:
    n = {
        k: ihtiyac_temsil_metni(problem_tanimi=v["problem"], basari_kriteri=v.get("basari_kriteri"))
        for k, v in ilanlar.items()
    }
    if tur == "genc":
        a = {
            k: yetenek_temsil_metni(
                rol_alani=v["rol"],
                deneyim_seviyesi=v["deneyim"],
                sektor_ilgi_alani=v["sektorler"],
                araclar_teknolojiler=v["araclar"],
                somut_ciktilar=[(c["baslik"], c.get("aciklama")) for c in v["ciktilar"]],
            )
            for k, v in adaylar.items()
        }
    else:
        a = {
            k: firma_temsil_metni(
                ne_yapiyoruz=v["ne_yapiyoruz"],
                yetkinlikler=v["yetkinlikler"],
                onceki_isler=v.get("onceki_isler"),
                sektor=v.get("sektor"),
            )
            for k, v in adaylar.items()
        }
    return n, a


# --- Embedding (önbellekli) -----------------------------------------------------------


def kosinus(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True)) / (
        math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    )


async def vektorler(metinler: dict[str, str], onbellek: dict, dosya: Path) -> dict[str, list[float]]:
    eksik = [k for k, m in metinler.items() if m not in onbellek]
    if eksik:
        for deneme in range(6):
            try:
                sonuc = await embedding_listesi_uret([metinler[k] for k in eksik], "document")
                break
            except Exception as hata:  # Voyage hız sınırı: bekleyip yeniden
                print(f"  voyage bekleme: {str(hata)[:80]}", file=sys.stderr)
                time.sleep(25)
        else:
            raise SystemExit("Voyage yanıt vermedi")
        for k, v in zip(eksik, sonuc, strict=True):
            onbellek[metinler[k]] = v
        dosya.write_text(json.dumps(onbellek), encoding="utf-8")
        time.sleep(21)
    return {k: onbellek[m] for k, m in metinler.items()}


# --- Çiftler ---------------------------------------------------------------------------


async def ciftleri_kur(onbellek: dict, onbellek_dosya: Path) -> list[dict]:
    ciftler: list[dict] = []
    for havuz in ("genc_havuzu", "firma_havuzu"):
        v = json.loads((VERI / f"{havuz}.json").read_text(encoding="utf-8"))
        tur, taban = v["tur"], v["benzerlik_tabani"]
        nm, am = temsil_metinleri(tur, v["ilanlar"], v["adaylar"])
        nv = await vektorler(nm, onbellek, onbellek_dosya)
        av = await vektorler(am, onbellek, onbellek_dosya)
        ayni = v.get("ayni_sorun", {})
        for ilan_id, ilan in v["ilanlar"].items():
            for aday_id, aday in v["adaylar"].items():
                s = kosinus(nv[ilan_id], av[aday_id])
                if s < taban:
                    continue
                ciftler.append(
                    {
                        "havuz": havuz,
                        "tur": tur,
                        "ilan_id": ilan_id,
                        "aday_id": aday_id,
                        "aday_adi": aday_id,
                        "ilan": ilan,
                        "aday": aday,
                        "etiket": v["etiketler"].get(ilan_id, {}).get(aday_id, 0),
                        "benzerlik": s,
                        "ayni_sorun": aday_id in ayni.get(ilan_id, []),
                    }
                )
    d = json.loads((VERI / "demo_vakalari.json").read_text(encoding="utf-8"))
    nm = {k: ihtiyac_temsil_metni(problem_tanimi=v["problem"], basari_kriteri=v.get("basari_kriteri")) for k, v in d["ilanlar"].items()}
    _, fm = temsil_metinleri("firma", {}, d["firmalar"])
    _, gm = temsil_metinleri("genc", {}, d["gencler"])
    nv = await vektorler(nm, onbellek, onbellek_dosya)
    fv = await vektorler(fm, onbellek, onbellek_dosya)
    gv = await vektorler(gm, onbellek, onbellek_dosya)
    for vaka in d["vakalar"]:
        tur = "genc" if vaka["aday_tur"] == "genc" else "firma"
        havuz = d["gencler"] if tur == "genc" else d["firmalar"]
        vek = gv if tur == "genc" else fv
        taban = 0.48 if tur == "genc" else 0.52
        s = kosinus(nv[vaka["ilan"]], vek[vaka["aday"]])
        ciftler.append(
            {
                "havuz": "demo",
                "tur": tur,
                "ilan_id": vaka["ilan"],
                "aday_id": vaka["aday"],
                "aday_adi": vaka["aday"],
                "ilan": d["ilanlar"][vaka["ilan"]],
                "aday": havuz[vaka["aday"]],
                "etiket": vaka["etiket"],
                "benzerlik": s,
                "taban_ustu": s >= taban,
                "ayni_sorun": False,
            }
        )
    return ciftler


# --- LLM çağrısı -----------------------------------------------------------------------


async def karar_al(zincirler: dict, cift: dict, girdi: dict, sem: asyncio.Semaphore) -> dict:
    async with sem:
        for deneme in range(4):
            try:
                with kullanim_topla() as kullanim:
                    s = await zincirler[cift["tur"]].ainvoke(girdi)
                return {
                    "karar": s.uygunluk,
                    "gerekce": s.gerekce,
                    "girdi_token": kullanim.girdi_token,
                    "cikti_token": kullanim.cikti_token,
                    "cagri": kullanim.cagri,
                }
            except Exception as hata:
                cevrilmis = llm_hatasini_cevir(hata)
                if isinstance(cevrilmis, HizSinirHatasi | ModelMesgulHatasi) and deneme < 3:
                    await asyncio.sleep(5 * 2**deneme)
                    continue
                return {"karar": None, "hata": f"{type(hata).__name__}: {str(hata)[:200]}", "girdi_token": 0, "cikti_token": 0, "cagri": 0, "gerekce": ""}
    raise AssertionError


EKSIKLIK = re.compile(
    r"(yer almama|bulunmama|yer almıyor|bulunmuyor|mevcut değil|belirtilmemiş|belirtilmemekte|"
    r"yazılmamış|görünmüyor|içermiyor|içermemekte|sunmuyor|geliştirmiyor|yapmıyor|"
    r"\beksik|\byok\b|\byoktur\b)"
)


def eksiklik_ifadesi(metin: str) -> str | None:
    e = EKSIKLIK.search(turkce_kucult(metin))
    return e.group(0) if e else None


# --- Rapor -----------------------------------------------------------------------------


def ozet(metin: str, n: int = 150) -> str:
    metin = " ".join(metin.split())
    return metin if len(metin) <= n else metin[: n - 1] + "…"


def ilan_ozeti(c: dict) -> str:
    return f"{c['ilan'].get('ad', c['ilan_id'])}: {ozet(c['ilan']['problem'])}"


def aday_ozeti(c: dict) -> str:
    a = c["aday"]
    if c["tur"] == "genc":
        return f"{c['aday_adi']} — {a['rol']} ({a['deneyim']}); {ozet(', '.join(x['baslik'] for x in a['ciktilar']), 110)}"
    return f"{c['aday_adi']} — {ozet(a['ne_yapiyoruz'], 130)}"


def tablo(satirlar: list[list[str]], baslik: list[str]) -> str:
    cikti = ["| " + " | ".join(baslik) + " |", "|" + "|".join("---" for _ in baslik) + "|"]
    cikti += ["| " + " | ".join(s) + " |" for s in satirlar]
    return "\n".join(cikti)


def karisiklik(kayitlar: list[tuple[int, str | None]]) -> str:
    sayim = Counter(kayitlar)
    satirlar = []
    for et in (2, 1, 0):
        satirlar.append(
            [f"{et} ({BEKLENEN[et]})"] + [str(sayim[(et, k)]) for k in KARARLAR] + [str(sayim[(et, None)])]
        )
    return tablo(satirlar, ["etiket \\ model", *KARARLAR, "hata"])


def metrikler(kayitlar: list[tuple[int, str | None, dict]]) -> dict:
    gecerli = [k for k in kayitlar if k[1] is not None]
    uyum = sum(1 for e, k, _ in gecerli if BEKLENEN[e] == k)
    guclu = [k for k in gecerli if k[0] == 2]
    alakasiz = [k for k in gecerli if k[0] == 0]
    kismen = [k for k in gecerli if k[0] == 1]
    uygun_kararlar = [k for k in gecerli if k[1] == "uygun"]
    cel = [k for k in uygun_kararlar if eksiklik_ifadesi(k[2]["gerekce"])]
    return {
        "n": len(kayitlar),
        "hata": len(kayitlar) - len(gecerli),
        "uyum": f"{uyum}/{len(gecerli)}" + (f" (%{100 * uyum / len(gecerli):.0f})" if gecerli else ""),
        "guclu_elenen": f"{sum(1 for k in guclu if k[1] == 'uygun_degil')}/{len(guclu)}",
        "guclu_kismen": f"{sum(1 for k in guclu if k[1] == 'kismen')}/{len(guclu)}",
        "alakasiz_elenen": f"{sum(1 for k in alakasiz if k[1] == 'uygun_degil')}/{len(alakasiz)}"
        + (f" (%{100 * sum(1 for k in alakasiz if k[1] == 'uygun_degil') / len(alakasiz):.0f})" if alakasiz else ""),
        "alakasiz_uygun": f"{sum(1 for k in alakasiz if k[1] == 'uygun')}/{len(alakasiz)}",
        "kismen_elenen": f"{sum(1 for k in kismen if k[1] == 'uygun_degil')}/{len(kismen)}",
        "eksiklik_uygun": f"{len(cel)}/{len(uygun_kararlar)}",
    }


def rapor_yaz(ciftler: list[dict], sonuclar: list[list[dict]], args, sure: float) -> str:
    n_run = len(sonuclar)
    tum = [(c["etiket"], s[i]["karar"], s[i]) for s in sonuclar for i, c in enumerate(ciftler)]
    cikti: list[str] = []
    ek = cikti.append
    ek("# Uygunluk kararı ölçümü (taslak istem, çevrimdışı karar için yalnızca ölçüm)\n")
    ek(f"Çalıştırma: {n_run} kez, aynı çiftler; süre {sure:.0f} sn. Etiketler bağımsız değil (kartları ve etiketleri aynı kişi yazdı).\n")
    from app.core.config import get_settings

    ayar = get_settings()
    ek(f"Model (güçlü katman): `{ayar.gemini_guclu_model}`, yedek `{ayar.gemini_guclu_yedek_model}`.\n")

    ek("## 1. Çiftler\n")
    satir = []
    for h in ("genc_havuzu", "firma_havuzu", "demo"):
        cs = [c for c in ciftler if c["havuz"] == h]
        e = Counter(c["etiket"] for c in cs)
        extra = ""
        if h == "demo":
            extra = f"; tabanın altında kalan: {sum(1 for c in cs if not c.get('taban_ustu'))}"
        satir.append([h, str(len(cs)), str(e[2]), str(e[1]), str(e[0]), extra or "—"])
    ek(tablo(satir, ["havuz", "çift", "etiket 2", "etiket 1", "etiket 0", "not"]))
    ek("\nHavuzlarda yalnızca üretimdeki koşulu (benzerlik tabanı) geçen çiftler var; demo vakalarında etiketli çiftlerin hepsi.\n")

    ek("## 2. Karışıklık tablosu (tüm çalıştırmalar toplamı)\n")
    ek(karisiklik([(e, k) for e, k, _ in tum]))
    ek("")
    for h in ("genc_havuzu", "firma_havuzu", "demo"):
        ek(f"\n**{h}**\n")
        ek(karisiklik([(c["etiket"], s[i]["karar"]) for s in sonuclar for i, c in enumerate(ciftler) if c["havuz"] == h]))
    ek("")

    ek("\n## 3. Ölçüler\n")
    anahtarlar = [
        ("uyum", "etiketle uyum"),
        ("guclu_elenen", "**güçlü uygun adayın yanlışlıkla elenmesi (hedef 0)**"),
        ("guclu_kismen", "güçlü uygun adaya 'kısmen' denmesi"),
        ("alakasiz_elenen", "alakasızın elenmesi"),
        ("alakasiz_uygun", "alakasıza 'uygun' denmesi"),
        ("kismen_elenen", "kısmen etiketlinin elenmesi"),
        ("eksiklik_uygun", "karar 'uygun' iken gerekçede eksiklik ifadesi"),
        ("hata", "hata (çağrı sonuç vermedi)"),
    ]
    satir = []
    gruplar = [("hepsi", None), ("genç havuzu", "genc_havuzu"), ("firma havuzu", "firma_havuzu"), ("demo", "demo")]
    m = {
        ad: metrikler([(c["etiket"], s[i]["karar"], s[i]) for s in sonuclar for i, c in enumerate(ciftler) if h is None or c["havuz"] == h])
        for ad, h in gruplar
    }
    for a, ad in anahtarlar:
        satir.append([ad] + [str(m[g][a]) for g, _ in gruplar])
    ek(tablo(satir, ["ölçü", *[g for g, _ in gruplar]]))
    ek("")
    ayni = [(c, s[i]) for s in sonuclar for i, c in enumerate(ciftler) if c.get("ayni_sorun")]
    if ayni:
        sayim = Counter(r["karar"] for _, r in ayni)
        ek(f"\n'Aynı sorunu yaşayan, çözüm sunmayan' firmalar (firma havuzu): {dict(sayim)} (n={len(ayni)})\n")
    ek("\nHer çalıştırma ayrı ayrı (uyum / güçlü elenen / alakasız elenen):\n")
    satir = []
    for r, s in enumerate(sonuclar, 1):
        mm = metrikler([(c["etiket"], s[i]["karar"], s[i]) for i, c in enumerate(ciftler)])
        satir.append([str(r), mm["uyum"], mm["guclu_elenen"], mm["alakasiz_elenen"], mm["eksiklik_uygun"]])
    ek(tablo(satir, ["çalıştırma", "uyum", "güçlü elenen", "alakasız elenen", "'uygun' + eksiklik"]))

    ek("\n## 4. Karar 'uygun' iken gerekçede eksiklik ifadesi bulunanlar\n")
    ek("(Düzenli ifade eşleşmesi; yanlış pozitif olabilir, eşleşen parça gösterilir.)\n")
    bulundu = False
    for r, s in enumerate(sonuclar, 1):
        for i, c in enumerate(ciftler):
            if s[i]["karar"] == "uygun" and (parca := eksiklik_ifadesi(s[i]["gerekce"])):
                bulundu = True
                ek(f"- çalıştırma {r}, {c['ilan_id']} ↔ {c['aday_adi']} (etiket {c['etiket']}), eşleşen: «{parca}»\n  > {ozet(s[i]['gerekce'], 400)}")
    if not bulundu:
        ek("Yok.")

    ek("\n## 5. Kararlılık\n")
    degisen = [i for i in range(len(ciftler)) if len({s[i]["karar"] for s in sonuclar}) > 1]
    ek(f"Kararı çalıştırmalar arasında değişen çift: **{len(degisen)} / {len(ciftler)}**\n")
    for i in degisen:
        c = ciftler[i]
        ek(f"- {c['ilan_id']} ↔ {c['aday_adi']} (etiket {c['etiket']}): " + " / ".join(str(s[i]["karar"]) for s in sonuclar))

    ek("\n## 6. Token ve maliyet\n")
    gt = sum(r["girdi_token"] for s in sonuclar for r in s)
    ct = sum(r["cikti_token"] for s in sonuclar for r in s)
    cg = sum(r["cagri"] for s in sonuclar for r in s)
    n_cagri = sum(len(s) for s in sonuclar)
    ek(f"- Çalıştırma sayısı: {n_run}; çift başına çağrı: {len(ciftler)}; toplam çözülen çift: {n_cagri}; model çağrısı (yedeğe düşenler dahil): {cg}")
    ek(f"- Girdi token toplamı: {gt:,}; çıktı token toplamı (düşünme dahil): {ct:,}")
    if n_cagri:
        ek(f"- Çift başına ortalama: girdi {gt / n_cagri:.0f}, çıktı {ct / n_cagri:.0f}")
    if args.fiyat_girdi is not None and args.fiyat_cikti is not None:
        usd = gt / 1e6 * args.fiyat_girdi + ct / 1e6 * args.fiyat_cikti
        ek(f"- Tahmini maliyet: {usd:.3f} USD (girdi {args.fiyat_girdi}/1M, çıktı {args.fiyat_cikti}/1M token; verilen fiyatla)")
    else:
        ek("- Maliyet: birim fiyat depoda yok; `--fiyat-girdi` ve `--fiyat-cikti` (USD/1M token) verilirse hesaplanır.")

    ek("\n## 7. Modelin etikete katılmadığı çiftler\n")
    ek("Beklenen eşleme: etiket 2 → uygun, 1 → kismen, 0 → uygun_degil. Bir çift, herhangi bir çalıştırmada karar beklenenden farklıysa listelenir. Etiketler bağımsız değil: hangisinde modelin haklı olduğuna siz karar verin.\n")
    sayac = 0
    for i, c in enumerate(ciftler):
        karar = [s[i]["karar"] for s in sonuclar]
        if all(k == BEKLENEN[c["etiket"]] for k in karar):
            continue
        sayac += 1
        ek(f"### {sayac}. {c['ilan_id']} ↔ {c['aday_adi']}  (benzerlik {c['benzerlik']:.3f})\n")
        ek(f"- **İlan:** {ilan_ozeti(c)}")
        ek(f"- **Aday:** {aday_ozeti(c)}")
        ek(f"- **Sizin etiketiniz:** {c['etiket']} ({BEKLENEN[c['etiket']]})")
        ek(f"- **Model kararı (çalıştırmalar):** {' / '.join(str(k) for k in karar)}")
        gosterilen: set[str] = set()
        for r, s in enumerate(sonuclar, 1):
            if s[i]["karar"] != BEKLENEN[c["etiket"]] and s[i]["gerekce"] not in gosterilen:
                gosterilen.add(s[i]["gerekce"])
                ek(f"- **Gerekçe (çalıştırma {r}, karar {s[i]['karar']}):** {s[i].get('gerekce') or s[i].get('hata')}")
        ek("")
    if not sayac:
        ek("Hiçbir çiftte katılmama yok.")
    return "\n".join(cikti)


# --- Ana akış --------------------------------------------------------------------------


async def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--calistirma", type=int, default=3)
    p.add_argument("--kuru", action="store_true", help="LLM çağrısı yapma; çiftleri ve ilk istemi göster")
    p.add_argument("--es", type=int, default=5, help="aynı anda en fazla çağrı")
    p.add_argument("--onbellek", default=str(Path(tempfile.gettempdir()) / "uygunluk_vektor_onbellegi.json"))
    p.add_argument("--cikti", default=str(VERI / "sonuclar"))
    p.add_argument("--fiyat-girdi", type=float)
    p.add_argument("--fiyat-cikti", type=float)
    args = p.parse_args()

    onbellek_dosya = Path(args.onbellek)
    onbellek = json.loads(onbellek_dosya.read_text(encoding="utf-8")) if onbellek_dosya.exists() else {}
    ciftler = await ciftleri_kur(onbellek, onbellek_dosya)
    sayim = Counter((c["havuz"], c["etiket"]) for c in ciftler)
    print(f"{len(ciftler)} çift:", dict(sorted(sayim.items())))
    for c in ciftler:
        if c["havuz"] == "demo":
            print(f"  demo {c['ilan_id']} ↔ {c['aday_adi']}: etiket {c['etiket']}, benzerlik {c['benzerlik']:.3f}, taban üstü {c['taban_ustu']}")
    girdiler = [girdi_olustur(c) for c in ciftler]
    if args.kuru:
        c = ciftler[0]
        print("\n--- İLK İSTEM ---")
        for m in sablon(c["tur"]).format_messages(**girdiler[0]):
            print(f"[{m.type}]\n{m.content}\n")
        return

    zincirler = {t: zincir(t) for t in ("genc", "firma")}
    sem = asyncio.Semaphore(args.es)
    bas = time.time()
    sonuclar = []
    for r in range(args.calistirma):
        print(f"Çalıştırma {r + 1}/{args.calistirma}…", flush=True)
        sonuclar.append(await asyncio.gather(*(karar_al(zincirler, c, g, sem) for c, g in zip(ciftler, girdiler, strict=True))))
        print("  kararlar:", dict(Counter(x["karar"] for x in sonuclar[-1])), flush=True)
    sure = time.time() - bas

    cikti = Path(args.cikti)
    cikti.mkdir(parents=True, exist_ok=True)
    ad = time.strftime("%Y-%m-%d-%H%M")
    (cikti / f"{ad}-ham.json").write_text(
        json.dumps(
            [{"havuz": c["havuz"], "ilan": c["ilan_id"], "aday": c["aday_adi"], "etiket": c["etiket"], "benzerlik": c["benzerlik"], "calistirmalar": [s[i] for s in sonuclar]} for i, c in enumerate(ciftler)],
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )
    (cikti / f"{ad}-rapor.md").write_text(rapor_yaz(ciftler, sonuclar, args, sure), encoding="utf-8")
    print(f"Rapor: {cikti / (ad + '-rapor.md')}")


if __name__ == "__main__":
    asyncio.run(main())
