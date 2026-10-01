"""Doğrulama değerlendirme setinin karnesi (docs/plans/dogrulama-iyilestirme.md § 10.1).

    python -m scripts.karne                    # çevrimdışı: kayıtlı yanıtlarla
    python -m scripts.karne --kip kaydet       # gerçek ağ ve model; kaseti yazar
    python -m scripts.karne --taslak           # etiket yoksa önerilen etiketle
    python -m scripts.karne --json cikti.json  # vaka başına sonuçlar (gerileme)

Kayıt kipi gerçek model çağırır (güçlü katman, vaka başına en çok bir çağrı;
daha önce kaydedilmiş girdi yeniden çağrılmaz). Karne
`tests/degerlendirme_seti/karneler/` altına tarihli olarak yazılır.
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from degerlendirme import rapor
from degerlendirme.calistir import hepsini_degerlendir
from degerlendirme.kaset import AgKaseti, KasetKipi, ModelKaseti
from degerlendirme.mevcut_sistem import MevcutSistemDegerlendirici
from degerlendirme.olcutler import karne_hesapla
from degerlendirme.vaka import SETI_KLASORU, vakalari_yukle

KARNE_KLASORU = SETI_KLASORU / "karneler"


def _argumanlar(argv: list[str] | None) -> argparse.Namespace:
    ayr = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    ayr.add_argument("--kip", choices=[k.value for k in KasetKipi], default=KasetKipi.OYNAT.value)
    ayr.add_argument(
        "--taslak", action="store_true", help="etiketsiz vakada önerilen etiketi kullan"
    )
    ayr.add_argument("--json", type=Path, help="vaka başına sonuçları bu dosyaya yaz")
    ayr.add_argument("--rapor-yazma", action="store_true", help="Markdown karneyi dosyaya yazma")
    ayr.add_argument(
        "--ayristirma-suresi", type=float, default=20.0, help="başlık ayrıştırması süre sınırı (sn)"
    )
    return ayr.parse_args(argv)


async def calistir(argv: list[str] | None = None) -> int:
    arg = _argumanlar(argv)
    kip = KasetKipi(arg.kip)
    if kip is KasetKipi.KAYDET:
        load_dotenv()

    ag = AgKaseti(kip)
    model = ModelKaseti(kip)
    degerlendirici = MevcutSistemDegerlendirici(ag, model, ayristirma_suresi=arg.ayristirma_suresi)
    vakalar = vakalari_yukle()

    with ag.dns_baglami(), degerlendirici:
        sonuclar = await hepsini_degerlendir(degerlendirici, vakalar)
    ag.kaydet()
    model.kaydet()

    karne = karne_hesapla(degerlendirici.ad, sonuclar, taslak=arg.taslak)
    tarih = dt.date.today().isoformat()
    metin = rapor.markdown(karne, tarih)
    if not arg.rapor_yazma:
        KARNE_KLASORU.mkdir(parents=True, exist_ok=True)
        ek = "-taslak" if arg.taslak else ""
        (KARNE_KLASORU / f"{tarih}-{degerlendirici.ad}{ek}.md").write_text(metin, encoding="utf-8")
    if arg.json:
        arg.json.write_text(
            json.dumps(rapor.anlik_goruntu(karne), ensure_ascii=False, indent=1, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
    sys.stdout.write(metin)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(asyncio.run(calistir()))
