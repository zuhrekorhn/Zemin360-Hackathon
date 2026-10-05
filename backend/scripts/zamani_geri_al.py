"""Yerel veritabanındaki bütün zamanları N gün geriye çeker (docs/faz-d-canlilik.md § 6).

Pasifleşme günlerce beklemeden yerelde gösterilsin diye: eşleşmelerin son
hareketi, kartların oluşturulma tarihi, adımların hedef tarihi, onay ve işaret
zamanları, Canlılık olayları ve bildirimler BİRLİKTE kayar. Birlikte kaydığı
için birbirlerine göre sıraları korunur: tekrar kuralı ("son hareketten sonra
hatırlatıldı mı") kaydırmadan sonra da doğru çalışır.

Yalnızca yerel: APP_ENV=production'da çalışmaz. Onay sorar (--evet ile sormaz).
Canlıda bu işi tohum veri hazır getirir (Faz E).

    .venv/Scripts/python.exe scripts/zamani_geri_al.py --gun 8
    .venv/Scripts/python.exe scripts/canlilik_taramasi.py   # ya da paneldeki düğme
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import get_sessionmaker

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# (tablo, kolon) — zaman damgaları ve tarihler. Yeni bir zaman alanı eklenirse
# buraya da eklenmeli; yoksa kaydırmadan sonra sıralar karışır.
ZAMAN_ALANLARI: tuple[tuple[str, str], ...] = (
    ("eslesme", "son_aktivite_tarihi"),
    ("yetenek_karti", "olusturma_tarihi"),
    ("ihtiyac_karti", "olusturma_tarihi"),
    ("isbirligi", "baslangic_tarihi"),
    ("isbirligi", "genc_plan_onayi"),
    ("isbirligi", "kurum_plan_onayi"),
    ("isbirligi", "tamamlanma_tarihi"),
    ("isbirligi", "ozet_tarihi"),
    ("milestone", "hedef_tarih"),
    ("milestone", "genc_isaret"),
    ("milestone", "kurum_isaret"),
    ("canlilik_olayi", "tetiklenme_tarihi"),
    ("bildirim", "olusturma_tarihi"),
    ("bildirim", "okundu_tarihi"),
    ("hesap", "olusturma_tarihi"),
    # Referansın 7 günlük zaman aşımı da tutarlı kaysın.
    ("referans_istegi", "olusturma_tarihi"),
    # Referans yanıtı ile iş kaleminin içerik tarihi birlikte kaysın: yanıtın
    # puana girip girmediği ikisinin sırasına bağlı.
    ("referans_istegi", "yanit_tarihi"),
    ("referans_istegi", "gonderim_tarihi"),
    ("referans_istegi", "hatirlatma_tarihi"),
    ("somut_cikti", "icerik_tarihi"),
    # Doğrulama (plan § 13): parçanın eklenme ve okunma anı, göstergenin hesaplandığı an
    ("kanit_parcasi", "olusturma_tarihi"),
    ("kanit_parcasi", "okuma_tarihi"),
    ("guven_skoru", "degerlendirme_tarihi"),
    ("eslesme", "genc_ilgi_tarihi"),
    ("eslesme", "genc_iletisim_onayi_tarihi"),
    ("eslesme", "kurum_ilgi_tarihi"),
    ("hesap", "kvkk_onay_tarihi"),
    ("ihtiyac_karti", "kapanma_tarihi"),
    ("kurum", "dogrulama_tarihi"),
    ("firma_karti", "olusturma_tarihi"),
    # Kimlik (plan § 6.3): bağlantının süresi ve yeniden gönderme aralığı birlikte kaysın.
    ("hesap", "eposta_dogrulandi_tarihi"),
    ("eposta_dogrulama", "olusturma_tarihi"),
    ("eposta_dogrulama", "son_gecerlilik"),
    ("inceleme_isareti", "olusturma_tarihi"),
    ("inceleme_isareti", "kapanma_tarihi"),
    # Hesap bağlama (plan § 6.2): doğrulama kodunun 48 saati de kaysın.
    ("bagli_hesap", "baglanma_tarihi"),
    ("profil_kodu", "son_gecerlilik"),
)

# Bilerek kaydırılmayanlar: kullanıcının yazdığı tarih ya da gözlem kaydı (sistemin kendi
# ölçümü; Canlılık simülasyonunu etkilemez, 90 gün saklama gerçek zamana göre işler).
KAYDIRILMAYANLAR: tuple[tuple[str, str], ...] = (
    ("somut_cikti", "tarih"),
    ("kullanici", "musaitlik_baslangici"),
    ("kanit_gozlemi", "tarih"),
    ("degerlendirme_gozlemi", "tarih"),
    ("servis_gunlugu", "gun"),
    ("servis_gunlugu", "son_basari"),
    ("servis_gunlugu", "son_hata"),
)


class UretimdeCalismaz(Exception):
    pass


def calistirilabilir_mi(app_env: str) -> None:
    if app_env.strip().lower() == "production":
        raise UretimdeCalismaz("APP_ENV=production: zaman kaydırma canlı veritabanında çalışmaz.")


def gun_dogrula(gun: int) -> int:
    if not 1 <= gun <= 365:
        raise ValueError("Gün 1 ile 365 arasında olmalı.")
    return gun


def kaydirma_ifadeleri(gun: int) -> list[str]:
    """Her alan için tek UPDATE; NULL'lar NULL kalır (NULL - aralık = NULL)."""
    gun = gun_dogrula(gun)
    return [
        f"UPDATE {tablo} SET {kolon} = {kolon} - INTERVAL '{gun} days'"
        for tablo, kolon in ZAMAN_ALANLARI
    ]


async def kaydir(gun: int, fabrika=None) -> None:
    fabrika = fabrika or get_sessionmaker()
    async with fabrika() as oturum:
        for ifade in kaydirma_ifadeleri(gun):
            await oturum.execute(text(ifade))
        await oturum.commit()


def main() -> None:
    ayristirici = argparse.ArgumentParser(description="Yerel zamanları N gün geriye çeker")
    ayristirici.add_argument("--gun", type=int, required=True, help="kaç gün (1-365)")
    ayristirici.add_argument("--evet", action="store_true", help="onay sormadan çalıştır")
    argumanlar = ayristirici.parse_args()

    try:
        calistirilabilir_mi(get_settings().app_env)
        gun = gun_dogrula(argumanlar.gun)
    except (UretimdeCalismaz, ValueError) as hata:
        raise SystemExit(str(hata)) from hata

    print(f"Yerel veritabanındaki bütün zamanlar {gun} gün geriye çekilecek.")
    if not argumanlar.evet and input("Devam edilsin mi? (evet/hayır): ").strip().lower() != "evet":
        raise SystemExit("Vazgeçildi, hiçbir şey değişmedi.")

    asyncio.run(kaydir(gun))
    print(
        f"Tamam: {gun} gün geriye çekildi. Şimdi taramayı çalıştır "
        "(scripts/canlilik_taramasi.py ya da GİRVAK panelindeki düğme)."
    )


if __name__ == "__main__":
    main()
