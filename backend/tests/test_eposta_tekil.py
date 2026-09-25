"""Kullanıcı ve kurum e-postayla tekil; onay kaydı günceller ama boşla silmez.

Eskiden: e-posta tekil değildi, "bul veya oluştur" yarışa açıktı ve kayıtlı
bir kişi onayda yeni bilgi verse de yok sayılıyordu (ikinci kartında şehrini
değiştiren gencin filtresi eski şehre göre çalışıyordu).

Upsert'in "boş gelen alan eskisini silmez" davranışı SQL'de (COALESCE/CASE).
DB'siz testler üretilen SQL'i sabitliyor; gerçek davranış yerel veritabanı
varsa işlem içinde denenip geri alınıyor, yoksa o testler atlanıyor.
"""

import asyncio
import uuid

import pytest
from dotenv import dotenv_values
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from app.api import kesif as kesif_api
from app.api.kesif import kullanici_upsert_ifadesi
from app.api.tanimlama import kurum_upsert_ifadesi
from app.core.metin import eposta_normalize
from app.db.session import get_session
from app.main import app
from app.models.kullanici import Kullanici
from app.models.kurum import Kurum
from app.schemas.kesif import KartOnaylaIstegi


def _sql(ifade) -> str:
    return str(ifade.compile(dialect=postgresql.dialect()))


def test_eposta_alanlari_tekil():
    assert Kullanici.__table__.c.email.unique is True
    assert Kurum.__table__.c.iletisim_email.unique is True


def test_eposta_normalize_edilir():
    """'Elif@Ornek.com' ile 'elif@ornek.com' iki ayrı kayıt açmamalı."""
    assert eposta_normalize("  Elif@Ornek.COM ") == "elif@ornek.com"


def test_kullanici_upsert_bos_alanla_eskisini_silmez():
    sql = _sql(
        kullanici_upsert_ifadesi(
            ad="Elif", email="elif@ornek.com", sehir=None, calisma_modelleri=[], musaitlik=None
        )
    )
    assert "ON CONFLICT (email) DO UPDATE" in sql
    assert "coalesce(excluded.musaitlik, kullanici.musaitlik)" in sql
    assert "coalesce(excluded.sehir, kullanici.sehir)" in sql
    assert "coalesce(excluded.ad, kullanici.ad)" in sql
    # Liste: boş gelirse eskisi kalır
    assert "CASE WHEN (cardinality(excluded.calisma_modelleri) =" in sql
    assert "THEN kullanici.calisma_modelleri ELSE excluded.calisma_modelleri END" in sql
    assert "RETURNING kullanici.id" in sql


def test_kurum_upsert_bos_alanla_eskisini_silmez():
    sql = _sql(
        kurum_upsert_ifadesi(ad="Koop", iletisim_email="koop@ornek.org", sektor=None, sehir=None)
    )
    assert "ON CONFLICT (iletisim_email) DO UPDATE" in sql
    assert "coalesce(excluded.sektor, kurum.sektor)" in sql
    assert "coalesce(excluded.sehir, kurum.sehir)" in sql


class KayitTutanOturum:
    def __init__(self):
        self.ifadeler = []

    async def scalar(self, ifade, *_args, **_kwargs):
        self.ifadeler.append(ifade)
        return uuid.uuid4()


def test_onay_e_postayi_normalize_edip_bos_musaitligi_none_gonderir():
    istek = KartOnaylaIstegi(
        oturum_id=uuid.uuid4(),
        kullanici={"ad": "Elif", "email": "Elif@Ornek.com", "sehir": "istanbul", "musaitlik": ""},
    )
    oturum = KayitTutanOturum()
    asyncio.run(kesif_api._kullaniciyi_kaydet(oturum, istek))

    degerler = oturum.ifadeler[0].compile(dialect=postgresql.dialect()).params
    assert degerler["email"] == "elif@ornek.com"
    assert degerler["musaitlik"] is None
    assert degerler["sehir"] == "İstanbul"


def test_bos_ad_422():
    """Upsert yeni kayıtta NOT NULL'a takılmasın; istek baştan reddedilir."""
    app.dependency_overrides[get_session] = lambda: None
    try:
        yanit = TestClient(app).post(
            "/kesif/kart/onayla",
            json={
                "oturum_id": str(uuid.uuid4()),
                "kullanici": {"ad": "   ", "email": "elif@ornek.com", "sehir": "İstanbul"},
            },
        )
    finally:
        app.dependency_overrides.clear()
    assert yanit.status_code == 422


# --- Gerçek veritabanında: işlem içinde dene, geri al --------------------------


def _veritabani_adresi() -> str | None:
    adres = dotenv_values(".env").get("DATABASE_URL")
    if not adres:
        return None
    return adres.replace("postgresql://", "postgresql+asyncpg://", 1)


async def _islem_icinde(islem):
    adres = _veritabani_adresi()
    if adres is None:
        pytest.skip("Yerel veritabanı tanımlı değil (.env)")
    motor = create_async_engine(adres, poolclass=NullPool)
    try:
        async with motor.connect() as baglanti:
            donus = await baglanti.begin()
            try:
                await islem(baglanti)
            finally:
                await donus.rollback()
    except OSError as hata:
        pytest.skip(f"Yerel veritabanına ulaşılamadı: {hata}")
    finally:
        await motor.dispose()


def test_mevcut_kullanici_musaitlik_vermeden_onaylarsa_eskisi_korunur():
    email = f"test-{uuid.uuid4()}@ornek.com"

    async def islem(baglanti):
        ilk = await baglanti.scalar(
            kullanici_upsert_ifadesi(
                ad="Elif",
                email=email,
                sehir="İstanbul",
                calisma_modelleri=["hibrit"],
                musaitlik="yarim_zamanli",
            )
        )
        ikinci = await baglanti.scalar(
            kullanici_upsert_ifadesi(
                ad="Elif Şahin", email=email, sehir=None, calisma_modelleri=[], musaitlik=None
            )
        )
        assert ikinci == ilk  # aynı kayıt, yeni satır yok

        satir = (
            await baglanti.execute(
                text(
                    "SELECT ad, sehir, calisma_modelleri, musaitlik, "
                    "(SELECT count(*) FROM kullanici WHERE email = :e) "
                    "FROM kullanici WHERE email = :e"
                ),
                {"e": email},
            )
        ).one()
        assert satir == ("Elif Şahin", "İstanbul", ["hibrit"], "yarim_zamanli", 1)

    asyncio.run(_islem_icinde(islem))


def test_mevcut_kurum_sektor_vermeden_onaylarsa_eskisi_korunur():
    email = f"test-{uuid.uuid4()}@koop.org"

    async def islem(baglanti):
        await baglanti.scalar(
            kurum_upsert_ifadesi(ad="Koop", iletisim_email=email, sektor="tarım", sehir="İzmir")
        )
        await baglanti.scalar(
            kurum_upsert_ifadesi(ad="Koop A.Ş.", iletisim_email=email, sektor=None, sehir=None)
        )
        satir = (
            await baglanti.execute(
                text("SELECT ad, sektor, sehir FROM kurum WHERE iletisim_email = :e"),
                {"e": email},
            )
        ).one()
        assert satir == ("Koop A.Ş.", "tarım", "İzmir")

    asyncio.run(_islem_icinde(islem))
