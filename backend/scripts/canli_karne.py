"""Haftalık canlı karne (docs/dogrulama.md § 10.1, § 16).

Değerlendirme setini bugünün sayfaları ve bugünün modeliyle ölçer ve kayıtlı
(kasetli) karneyle karşılaştırır: link çürümesi, sayfa değişimi ve model kayması
vaka başına görünür. Kayıtlı kasetler ve karneler DEĞİŞMEZ (canlı çalışma geçici
bir klasöre kaydeder, sonra siler).

    python -m scripts.canli_karne                  # etiketli vakalar, canlı ağ ve model
    python -m scripts.canli_karne --taslak         # etiket yoksa önerilen etiketle
    python -m scripts.canli_karne --alan yazilim   # tek alan (maliyet düşük)
    python -m scripts.canli_karne --yazma-yok      # karneyi dosyaya yazma

Çıkış kodu: canlı karne kabul eşiklerini geçiyorsa 0, geçmiyorsa 1 (cron'un
uyarı vermesi için). Sapma tek başına çıkış kodunu değiştirmez: bir uyarıdır.
Gerçek model çağrısı yapar (ücretli) ve gerçek ağa çıkar; yedek okuyucu servisi
yapılandırılmamışsa o yoldaki vakalar "sonuç üretemedi" görünür. Zamanlayıcı
kurulmaz (CLAUDE.md): haftada bir çalıştırmak platform cron'unun ya da elin işi.

Karne `tests/degerlendirme_seti/karneler/canli/` altına tarihli yazılır.
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import sys
import tempfile
from pathlib import Path

from dotenv import load_dotenv

from app.agents.dogrulama.okuma import EKRAN_OKUNUSLARI
from app.core.config import get_settings
from degerlendirme import rapor
from degerlendirme.calistir import hepsini_degerlendir
from degerlendirme.canli import sapma_bolumu, sapmalari_bul
from degerlendirme.kaset import AgKaseti, KasetKipi, ModelKaseti, YedekOkuyucuKaseti
from degerlendirme.mevcut_sistem import MevcutSistemDegerlendirici
from degerlendirme.olcutler import VakaSonucu, karne_hesapla
from degerlendirme.vaka import SETI_KLASORU, Vaka, vakalari_yukle

CANLI_KARNE_KLASORU = SETI_KLASORU / "karneler" / "canli"


def _argumanlar(argv: list[str] | None) -> argparse.Namespace:
    ayr = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    ayr.add_argument(
        "--taslak", action="store_true", help="etiketsiz vakada önerilen etiketi kullan"
    )
    ayr.add_argument("--alan", help="yalnızca bu alandaki vakalar (ör. yazilim)")
    ayr.add_argument("--yazma-yok", action="store_true", help="karneyi dosyaya yazma")
    return ayr.parse_args(argv)


async def _calistir(vakalar: list[Vaka], kip: KasetKipi, klasor: Path | None) -> list[VakaSonucu]:
    """Kasetin kipiyle bir tur. `klasor` verilirse kaset oraya yazılır/oradan okunur; hiçbir
    zaman `kaydet()` çağrılmaz (kayıtlı kaset ve karne bozulmasın)."""
    EKRAN_OKUNUSLARI.temizle()  # bir önceki turun okunuşu bu turu kirletmesin
    ek = {"klasor": klasor} if klasor is not None else {}
    ag = AgKaseti(kip, **ek)
    model = ModelKaseti(kip, **ek)
    embedding = ModelKaseti(kip, dosya="embedding.json.gz", **ek)
    degerlendirici = MevcutSistemDegerlendirici(ag, model, embedding, YedekOkuyucuKaseti(kip, **ek))
    with ag.dns_baglami():
        return await hepsini_degerlendir(degerlendirici, vakalar)


async def calistir(argv: list[str] | None = None) -> int:
    arg = _argumanlar(argv)
    load_dotenv()
    get_settings.cache_clear()  # ayarlar .env yüklenmeden önbelleğe alınmış olabilir

    vakalar = vakalari_yukle()
    if arg.alan:
        vakalar = [v for v in vakalar if v.alan.value == arg.alan]
        if not vakalar:
            sys.stderr.write(f"Bu alanda vaka yok: {arg.alan}\n")
            return 2

    # Kayıtlı taraf: dondurulmuş sayfalar ve model yanıtları (çevrimdışı, ücretsiz).
    kayitli = await _calistir(vakalar, KasetKipi.OYNAT, None)
    # Canlı taraf: boş geçici klasörde kaydet kipi = her şey gerçek ağdan ve modelden.
    with tempfile.TemporaryDirectory(prefix="canli_karne_") as gecici:
        canli = await _calistir(vakalar, KasetKipi.KAYDET, Path(gecici))

    karne = karne_hesapla("mevcut_sistem_canli", canli, taslak=arg.taslak)
    sapmalar = sapmalari_bul(kayitli, canli)
    tarih = dt.date.today().isoformat()
    metin = rapor.markdown(karne, tarih).rstrip("\n") + "\n"
    metin += "\n".join(sapma_bolumu(sapmalar, len(canli))) + "\n"

    if not arg.yazma_yok:
        CANLI_KARNE_KLASORU.mkdir(parents=True, exist_ok=True)
        ek = ("-taslak" if arg.taslak else "") + (f"-{arg.alan}" if arg.alan else "")
        (CANLI_KARNE_KLASORU / f"{tarih}-canli{ek}.md").write_text(metin, encoding="utf-8")
    sys.stdout.write(metin)
    return 0 if karne.esikleri_geciyor_mu else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(asyncio.run(calistir()))
