"""Doğrulama değerlendirme setinin karnesi (docs/plans/dogrulama-iyilestirme.md § 10.1).

    python -m scripts.karne                      # çevrimdışı: kayıtlı yanıtlarla
    python -m scripts.karne --model kaydet       # kayıtlı ağ, eksik model çağrıları gerçek
    python -m scripts.karne --ag tamamla --model kaydet  # yeni okuyucu: eksik istekler canlı
    python -m scripts.karne --ag kaydet --model kaydet   # gerçek ağ ve model (yeni vaka)
    python -m scripts.karne --taslak             # etiket yoksa önerilen etiketle
    python -m scripts.karne --json cikti.json    # vaka başına sonuçlar (gerileme)

Kod değiştiğinde `--model kaydet` kullanılır: sayfalar kasetten gelir, böylece
karnedeki fark yalnızca kodun farkıdır (sayfaların bugünkü hâli karışmaz). Model
kaydı daha önce görülmüş girdiyi yeniden çağırmaz. Karne
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

from app.core.config import get_settings
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
    kipler = [k.value for k in KasetKipi]
    ayr.add_argument("--ag", choices=kipler, default=KasetKipi.OYNAT.value, help="ağ kaseti")
    ayr.add_argument("--model", choices=kipler, default=KasetKipi.OYNAT.value, help="model kaseti")
    ayr.add_argument(
        "--taslak", action="store_true", help="etiketsiz vakada önerilen etiketi kullan"
    )
    ayr.add_argument("--json", type=Path, help="vaka başına sonuçları bu dosyaya yaz")
    ayr.add_argument("--rapor-yazma", action="store_true", help="Markdown karneyi dosyaya yazma")
    ayr.add_argument("--rapor-eki", default="", help="rapor dosya adına ek (ör. adim2)")
    return ayr.parse_args(argv)


async def calistir(argv: list[str] | None = None) -> int:
    arg = _argumanlar(argv)
    ag = AgKaseti(KasetKipi(arg.ag))
    model = ModelKaseti(KasetKipi(arg.model))
    if KasetKipi.OYNAT not in (ag.kip,) or model.kip is not KasetKipi.OYNAT:
        load_dotenv()
        get_settings.cache_clear()  # ayarlar .env yüklenmeden önbelleğe alınmış olabilir
    embedding = ModelKaseti(KasetKipi(arg.model), dosya="embedding.json.gz")
    degerlendirici = MevcutSistemDegerlendirici(ag, model, embedding)
    vakalar = vakalari_yukle()

    with ag.dns_baglami():
        sonuclar = await hepsini_degerlendir(degerlendirici, vakalar)
    ag.kaydet()
    model.kaydet()
    embedding.kaydet()

    karne = karne_hesapla(degerlendirici.ad, sonuclar, taslak=arg.taslak)
    tarih = dt.date.today().isoformat()
    metin = rapor.markdown(karne, tarih)
    if not arg.rapor_yazma:
        KARNE_KLASORU.mkdir(parents=True, exist_ok=True)
        ek = ("-taslak" if arg.taslak else "") + (f"-{arg.rapor_eki}" if arg.rapor_eki else "")
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
