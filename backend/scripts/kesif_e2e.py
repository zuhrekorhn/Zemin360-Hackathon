"""Keşif Ajanı'nın uçtan uca denemesi — gerçek Gemini ve Voyage çağrılarıyla.

Mock yok: sohbet baştan sona yürütülür, kart onaylanır, embedding'in
veritabanına yazıldığı SQL ile doğrulanır. İki senaryo çalışır:
  A) Normal akış — somut çıktısı olan bir genç.
  B) "Hiç projem yok" — fallback zinciri, kartın "potansiyel" çıkması.

Çalıştırma (sunucu ayakta olmalı):
    .venv/Scripts/python.exe scripts/kesif_e2e.py            # iki senaryo
    .venv/Scripts/python.exe scripts/kesif_e2e.py b          # sadece "projem yok" senaryosu

Gemini ücretsiz katmanın dakikalık istek sınırına takılmamak için çağrılar
arasında kısa bir bekleme var.
"""

from __future__ import annotations

import asyncio
import os
import sys
import uuid

import asyncpg
import httpx
from dotenv import load_dotenv

# Windows konsolu varsayılan olarak cp1252; Türkçe çıktı bozulmasın.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

API = os.environ.get("API_URL", "http://localhost:8000")
CAGRI_ARASI_BEKLEME = 6.0  # saniye — Gemini ücretsiz katman hız sınırı
MAKS_TUR = 8  # sonsuz döngüye karşı emniyet

SENARYO_A = [
    "Mahalle kütüphanesine ödünç takip sistemi yazdım. 400 kitabı ve 120 üyeyi takip ediyor. "
    "Python ve Django kullandım, kodu github.com/ornek/kutuphane adresinde.",
    "Kendimi backend geliştirici olarak görüyorum, iki yıldır uğraşıyorum. "
    "Eğitim ve sivil toplum alanlarında çalışmak isterim.",
    "Ayrıca PostgreSQL ve Docker kullanıyorum.",
]

SENARYO_B = [
    "Açıkçası bitirdiğim bir proje yok, daha yeni başlıyorum.",
    "Okulda da öyle bitirdiğim bir ödev yok maalesef.",
    "Gönüllü bir iş de yapmadım. Veri analizine ilgim var, Excel ve biraz SQL biliyorum. "
    "Finans sektöründe çalışmak isterim.",
    "Kendimi veri analisti adayı olarak görüyorum.",
]


async def bekle() -> None:
    await asyncio.sleep(CAGRI_ARASI_BEKLEME)


async def sohbeti_yurut(istemci: httpx.AsyncClient, cevaplar: list[str]) -> dict:
    yanit = (await istemci.post(f"{API}/kesif/sohbet/baslat", json={})).raise_for_status().json()
    oturum_id = yanit["oturum_id"]
    print(f"  Ajan: {yanit['soru']}")

    for tur in range(MAKS_TUR):
        if yanit["taslak_hazir"]:
            break
        cevap = cevaplar[min(tur, len(cevaplar) - 1)]
        print(f"  Kullanıcı: {cevap[:70]}…")
        await bekle()
        yanit = (
            (
                await istemci.post(
                    f"{API}/kesif/sohbet/cevap",
                    json={"oturum_id": oturum_id, "cevap": cevap},
                )
            )
            .raise_for_status()
            .json()
        )
        if yanit["soru"]:
            print(f"  Ajan: {yanit['soru']}")

    if not yanit["taslak_hazir"]:
        raise SystemExit(f"{MAKS_TUR} turda taslak hazır olmadı")

    print(f"  → Taslak: {yanit['taslak']}")
    return yanit


async def karti_onayla(istemci: httpx.AsyncClient, oturum_id: str, email: str) -> dict:
    yanit = await istemci.post(
        f"{API}/kesif/kart/onayla",
        json={
            "oturum_id": oturum_id,
            "kullanici": {
                "ad": "Test Kullanıcı",
                "email": email,
                "sehir": "İstanbul",
                "musaitlik": "yarim_zamanli",
            },
        },
        timeout=60,
    )
    yanit.raise_for_status()
    return yanit.json()


async def veritabanindan_dogrula(kart_id: str) -> None:
    url = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")
    baglanti = await asyncpg.connect(url)
    try:
        satir = await baglanti.fetchrow(
            """
            SELECT rol_alani, deneyim_seviyesi, sektor_ilgi_alani, araclar_teknolojiler,
                   kanit_bekleyen, versiyon,
                   embedding IS NOT NULL AS embedding_var,
                   vector_dims(embedding) AS boyut
            FROM yetenek_karti WHERE id = $1
            """,
            uuid.UUID(kart_id),
        )
        ciktilar = await baglanti.fetch(
            "SELECT baslik, kanit_linki FROM somut_cikti WHERE yetenek_karti_id = $1",
            uuid.UUID(kart_id),
        )
    finally:
        await baglanti.close()

    if satir is None:
        raise SystemExit("Kart veritabanında bulunamadı")
    print(f"  DB kart: {dict(satir)}")
    print(f"  DB somut_cikti: {[dict(c) for c in ciktilar]}")
    assert satir["embedding_var"], "embedding NULL — Voyage çağrısı kaydedilmemiş"
    assert satir["boyut"] == 1024, f"embedding boyutu {satir['boyut']}, beklenen 1024"


async def senaryo_a(istemci: httpx.AsyncClient) -> None:
    print("\n=== Senaryo A — normal akış ===")
    a = await sohbeti_yurut(istemci, SENARYO_A)
    kart_a = await karti_onayla(istemci, a["oturum_id"], f"test-a-{uuid.uuid4().hex[:8]}@ornek.com")
    print(f"  Kart yanıtı: {kart_a}")
    await veritabanindan_dogrula(kart_a["id"])

    getir = (await istemci.get(f"{API}/yetenek-kartlari/{kart_a['id']}")).json()
    assert "email" not in str(getir), "GET yanıtında e-posta sızmış"
    print("  GET /yetenek-kartlari: e-posta içermiyor ✓")


async def senaryo_b(istemci: httpx.AsyncClient) -> None:
    print("\n=== Senaryo B — 'hiç projem yok' ===")
    b = await sohbeti_yurut(istemci, SENARYO_B)
    kart_b = await karti_onayla(istemci, b["oturum_id"], f"test-b-{uuid.uuid4().hex[:8]}@ornek.com")
    print(f"  Kart yanıtı: {kart_b}")
    await veritabanindan_dogrula(kart_b["id"])
    assert kart_b["deneyim_seviyesi"] == "potansiyel", (
        f"çıktısız kart 'potansiyel' olmalıydı, {kart_b['deneyim_seviyesi']} geldi"
    )
    assert not kart_b["somut_ciktilar"], "çıktısız senaryoda somut çıktı oluşmuş"
    print("  Çıktısız kart 'potansiyel' etiketiyle oluştu ✓")


async def main() -> None:
    load_dotenv()
    # Hız sınırına takılınca tek senaryoyu tekrar çalıştırabilmek için: "a" | "b"
    secim = sys.argv[1].lower() if len(sys.argv) > 1 else "hepsi"
    async with httpx.AsyncClient(timeout=60) as istemci:
        if secim in ("a", "hepsi"):
            await senaryo_a(istemci)
        if secim == "hepsi":
            await bekle()
        if secim in ("b", "hepsi"):
            await senaryo_b(istemci)

    print(f"\nSenaryo '{secim}' geçti.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except httpx.HTTPStatusError as hata:
        print(f"HTTP {hata.response.status_code}: {hata.response.text[:500]}", file=sys.stderr)
        raise SystemExit(1) from hata
