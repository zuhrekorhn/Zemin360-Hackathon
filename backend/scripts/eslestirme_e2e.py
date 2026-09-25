"""Eşleştirme Ajanı'nın uçtan uca denemesi.

Pipeline'ı gerçek veriyle çalıştırır: sert filtreler → pgvector benzerliği →
skor → eşik → LLM gerekçesi → "ilgileniyorum" → ISBIRLIGI.

    python scripts/eslestirme_e2e.py
    python scripts/eslestirme_e2e.py --tohum

Kurum hesabıyla giriş yapar (Faz B): `.env`'de E2E_KURUM_EPOSTA ve
E2E_KURUM_SIFRE tanımlı olmalı; kurum ve ihtiyaç kartı o hesabınkidir.

`--tohum`, havuzda ihtiyaca gerçekten uyan bir aday yoksa DEMO amaçlı bir
yetenek kartı ekler (Voyage embedding'iyle, Gemini çağrısı olmadan). Cold
start sorununu elle aşmak için: gerçek sohbetten geçmiş kartlar azken
pipeline'ın tamamını görebilmek gerekiyor.

LLM: yalnızca gerekçe üretiminde (güçlü katman), öneri başına bir çağrı.
"""

from __future__ import annotations

import asyncio
import os
import sys
import uuid

import httpx
from dotenv import load_dotenv
from sqlalchemy import select

from app.api.auth import hesap_olustur
from app.core.embeddings import embedding_uret, yetenek_temsil_metni
from app.db.session import get_sessionmaker
from app.models.guven_skoru import GuvenSkoru
from app.models.kullanici import Kullanici
from app.models.somut_cikti import SomutCikti
from app.models.yetenek_karti import YetenekKarti

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

API = os.environ.get("API_URL", "http://localhost:8000")

DEMO_EMAIL = "demo-aday@ornek.com"
DEMO = {
    "ad": "Demo Aday",
    "sehir": "İstanbul",
    "musaitlik": "yarim_zamanli",
    "rol_alani": "backend geliştirici",
    "deneyim_seviyesi": "orta",
    "sektor_ilgi_alani": ["müşteri hizmetleri", "kurumsal yazılım"],
    "araclar_teknolojiler": ["Python", "NLP", "ticket sistemleri"],
    "cikti_baslik": "Destek biletlerini otomatik sınıflandıran bot",
    "cikti_aciklama": (
        "Gelen talepleri konuya göre ayırıp tier-1 biletlerin %60'ını insan "
        "müdahalesi olmadan çözdü."
    ),
}


async def demo_karti_ekle() -> uuid.UUID:
    """Doğrulanmış bir demo kartı ekler (varsa yeniden kullanır)."""
    async with get_sessionmaker()() as oturum:
        kullanici = await oturum.scalar(select(Kullanici).where(Kullanici.email == DEMO_EMAIL))
        if kullanici is None:
            # Hesapsız profilin kartı eşleştirmeye girmez (Faz B notu § 8):
            # demo aday da bir hesaba bağlı. Şifre kullanılmıyor, rastgele.
            hesap = await hesap_olustur(
                oturum, email=DEMO_EMAIL, sifre=uuid.uuid4().hex, rol="genc", ad=DEMO["ad"]
            )
            kullanici = await oturum.scalar(select(Kullanici).where(Kullanici.hesap_id == hesap.id))
            kullanici.sehir = DEMO["sehir"]
            kullanici.musaitlik = DEMO["musaitlik"]
            await oturum.flush()

        mevcut = await oturum.scalar(
            select(YetenekKarti).where(YetenekKarti.kullanici_id == kullanici.id)
        )
        if mevcut is not None:
            print(f"  demo kart zaten var: {mevcut.id}")
            return mevcut.id

        cikti = SomutCikti(
            baslik=DEMO["cikti_baslik"],
            aciklama=DEMO["cikti_aciklama"],
            kanit_linki="https://ornek.com/demo-bot",
            # Doğrulama Ajanı Faz 2'de bunu kendisi üretecek; burada skor elle
            # veriliyor ki doğrulama bonusu gerçek SQL üzerinden denensin.
            guven_skoru=GuvenSkoru(
                kanit_orijinalligi=3,
                sonuc_olculebilirligi=3,
                rol_netligi=2,
                ucuncu_taraf_onayi=1,
                gerekce_metni="Demo veri — elle girildi.",
            ),
        )
        kart = YetenekKarti(
            kullanici_id=kullanici.id,
            rol_alani=DEMO["rol_alani"],
            deneyim_seviyesi=DEMO["deneyim_seviyesi"],
            sektor_ilgi_alani=DEMO["sektor_ilgi_alani"],
            araclar_teknolojiler=DEMO["araclar_teknolojiler"],
            kanit_bekleyen=False,
            somut_ciktilar=[cikti],
        )
        oturum.add(kart)
        await oturum.commit()

        kart.embedding = await embedding_uret(
            yetenek_temsil_metni(
                rol_alani=kart.rol_alani,
                deneyim_seviyesi=kart.deneyim_seviyesi,
                sektor_ilgi_alani=kart.sektor_ilgi_alani,
                araclar_teknolojiler=kart.araclar_teknolojiler,
                somut_ciktilar=[(cikti.baslik, cikti.aciklama)],
            )
        )
        await oturum.commit()
        print(f"  demo kart eklendi: {kart.id}")
        return kart.id


def oneri_yaz(yanit: dict) -> None:
    print(f"  ihtiyaç kartı: {yanit['ihtiyac_karti_id']}")
    print(f"  az sonuç uyarısı: {yanit['az_sonuc_uyarisi']}")
    if not yanit["oneriler"]:
        print("  (eşik üstünde öneri yok)")
    for sira, oneri in enumerate(yanit["oneriler"], start=1):
        kart = oneri["yetenek_karti"]
        print(
            f"  {sira}. skor={oneri['skor']:.3f} durum={oneri['durum']} "
            f"rol={kart['rol_alani']} ({kart['deneyim_seviyesi']}) "
            f"kanıt_bekleyen={kart['kanit_bekleyen']}"
        )
        print(f"     gerekçe: {oneri['gerekce_metni']}")


async def main() -> None:
    load_dotenv()
    eposta, sifre = os.environ.get("E2E_KURUM_EPOSTA"), os.environ.get("E2E_KURUM_SIFRE")
    if not (eposta and sifre):
        raise SystemExit(".env'de E2E_KURUM_EPOSTA ve E2E_KURUM_SIFRE tanımlı olmalı")

    if "--tohum" in sys.argv:
        print("=== Demo aday kartı ===")
        await demo_karti_ekle()

    async with httpx.AsyncClient(timeout=120) as istemci:
        giris = await istemci.post(f"{API}/auth/giris", json={"email": eposta, "sifre": sifre})
        giris.raise_for_status()
        istemci.headers["Authorization"] = f"Bearer {giris.json()['token']}"
        kurum_id = (await istemci.get(f"{API}/me")).raise_for_status().json()["kurum_id"]

        print("\n=== POST /eslestirme/calistir ===")
        yanit = (
            (await istemci.post(f"{API}/eslestirme/calistir", json={})).raise_for_status().json()
        )
        oneri_yaz(yanit)

        print("\n=== GET /eslestirme/oneriler (yeniden hesaplamadan okur) ===")
        tekrar = (
            (await istemci.get(f"{API}/eslestirme/oneriler/{kurum_id}")).raise_for_status().json()
        )
        oneri_yaz(tekrar)

        if not tekrar["oneriler"]:
            print("\nÖneri yok; 'ilgileniyorum' adımı atlanıyor.")
            return

        en_iyi = tekrar["oneriler"][0]
        print("\n=== POST /eslestirme/ilgileniyorum ===")
        sonuc = (
            (
                await istemci.post(
                    f"{API}/eslestirme/ilgileniyorum",
                    json={"eslesme_id": en_iyi["eslesme_id"]},
                )
            )
            .raise_for_status()
            .json()
        )
        print(f"  eşleşme durumu: {sonuc['durum']}")
        print(f"  iş birliği: {sonuc['isbirligi_id']} ({sonuc['isbirligi_durum']})")


if __name__ == "__main__":
    asyncio.run(main())
