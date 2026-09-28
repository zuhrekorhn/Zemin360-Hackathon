"""Geliştirme betikleri: yerel sıfırlama ve demo hesapları (docs/faz-b-kimlik-ve-dongu.md § 8-9).

Sıfırlamanın kendisi (TRUNCATE) burada çalıştırılmıyor: geri alınan işlem
içinde bile yerel veritabanının tamamını kilitler. Sınanan, neyi sileceği ve
nerede çalışmayı reddettiği. Demo betiği gerçek veritabanında, geri alınan
işlem içinde, embedding sahte vektörle çalıştırılıyor.
"""

import asyncio
import contextlib
import uuid

import pytest
from sqlalchemy import func, select

from app.agents.eslestirme import adaylari_getir
from app.api import ihtiyac_kartlari, yetenek_kartlari
from app.core.kimlik import sifre_dogru_mu
from app.db.base import EMBEDDING_DIM
from app.models.hesap import Hesap
from app.models.ihtiyac_karti import IhtiyacKarti
from app.models.kullanici import Kullanici
from app.models.kurum import Kurum
from app.models.yetenek_karti import YetenekKarti
from app.schemas.auth import GirisIstegi
from scripts import demo_hesaplari, yerel_sifirla
from tests.veritabani import geri_alinan_oturum

# --- yerel_sifirla -----------------------------------------------------------------------


def test_uretimde_calismaz():
    with pytest.raises(yerel_sifirla.UretimdeCalismaz):
        yerel_sifirla.calistirilabilir_mi("production")
    with pytest.raises(yerel_sifirla.UretimdeCalismaz):
        yerel_sifirla.calistirilabilir_mi(" Production ")
    yerel_sifirla.calistirilabilir_mi("development")


def test_uygulama_tablolari_ve_checkpointler_silinir_sema_surumleri_kalir():
    tablolar = set(yerel_sifirla.sifirlanacak_tablolar())
    assert {"hesap", "kullanici", "kurum", "eslesme", "isbirligi", "bildirim"} <= tablolar
    assert {"checkpoints", "checkpoint_blobs", "checkpoint_writes"} <= tablolar
    assert not set(yerel_sifirla.DOKUNULMAYANLAR) & tablolar


def test_truncate_ifadesi():
    assert yerel_sifirla.truncate_ifadesi(["a", "b"]) == "TRUNCATE a, b RESTART IDENTITY CASCADE"


# --- demo_hesaplari ----------------------------------------------------------------------


def test_demo_sifresi_bossa_calismaz():
    with pytest.raises(SystemExit):
        demo_hesaplari.sifreyi_dogrula("")
    with pytest.raises(SystemExit):
        demo_hesaplari.sifreyi_dogrula("kisa")
    assert demo_hesaplari.sifreyi_dogrula("yeterince-uzun") == "yeterince-uzun"


def test_demo_adresleri_giris_formundan_gecer():
    """Nottaki `@demo.zemin360` burada kalıyordu; giriş yapılamayan demo hesabı olmaz."""
    for email in (
        demo_hesaplari.GENC_EPOSTA,
        demo_hesaplari.KURUM_EPOSTA,
        demo_hesaplari.GIRVAK_EPOSTA,
    ):
        assert GirisIstegi(email=email, sifre="x").email == email


def test_demo_gencinin_profili_eksiksiz_ve_demo_ihtiyacina_uyar():
    """Tohum veri yeni kayıt alanlarıyla dolu; demo önerisi filtrede elenmez."""
    from app.core.calisma_modeli import sehir_eslesmeli_mi
    from app.core.genc_profili import eksik_profil_alanlari
    from app.core.musaitlik import musaitlik_uyar_mi

    profil = demo_hesaplari.GENC_PROFILI
    assert (
        eksik_profil_alanlari(
            sehir=profil.sehir,
            calisma_modelleri=profil.calisma_modelleri,
            musaitlikler=profil.musaitlikler,
            kariyer_durumu=profil.kariyer_durumu,
        )
        == []
    )
    ihtiyac = demo_hesaplari.kurumun_karti(None)
    assert musaitlik_uyar_mi(ihtiyac.musaitlik_tercihi, profil.musaitlikler)
    assert ihtiyac.calisma_modeli in profil.calisma_modelleri
    assert not sehir_eslesmeli_mi(ihtiyac.calisma_modeli) or profil.sehir == ihtiyac.sehir_tercihi


def test_benzerlik():
    assert demo_hesaplari.benzerlik([1.0, 0.0], [2.0, 0.0]) == pytest.approx(1.0)
    assert demo_hesaplari.benzerlik([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)


def test_demo_hesaplari_acilir_tekrar_calismasi_guvenli_ve_kartlar_eslesir(monkeypatch):
    # Yerel veritabanında gerçek demo hesapları zaten olabilir (betik çalıştırıldıysa);
    # test onlara bağlı kalmasın diye her çalışmada benzersiz adresler.
    ek = uuid.uuid4().hex[:8]
    monkeypatch.setattr(demo_hesaplari, "GENC_EPOSTA", f"genc-{ek}@demo.zemin360.example")
    monkeypatch.setattr(demo_hesaplari, "KURUM_EPOSTA", f"kurum-{ek}@demo.zemin360.example")
    monkeypatch.setattr(demo_hesaplari, "GIRVAK_EPOSTA", f"girvak-{ek}@demo.zemin360.example")
    vektor = [0.0] * EMBEDDING_DIM
    vektor[7] = 1.0

    async def sahte_embedding(_metin, girdi_turu="document"):
        return vektor

    monkeypatch.setattr(yetenek_kartlari, "embedding_uret", sahte_embedding)
    monkeypatch.setattr(ihtiyac_kartlari, "embedding_uret", sahte_embedding)

    async def senaryo():
        async with geri_alinan_oturum() as oturum:

            @contextlib.asynccontextmanager
            async def ayni_oturum():
                yield oturum

            monkeypatch.setattr(demo_hesaplari, "get_sessionmaker", lambda: ayni_oturum)

            ilk = await demo_hesaplari.demo_ac("yeterince-uzun")
            assert [(s.rol, s.yeni) for s in ilk] == [
                ("genc", True),
                ("kurum", True),
                ("girvak", True),
            ]
            ikinci = await demo_hesaplari.demo_ac("yeterince-uzun")
            assert not any(s.yeni for s in ikinci)

            hesap = await oturum.scalar(
                select(Hesap).where(Hesap.email == demo_hesaplari.GENC_EPOSTA)
            )
            assert sifre_dogru_mu(hesap.sifre_hash, "yeterince-uzun")
            genc = await oturum.scalar(select(Kullanici).where(Kullanici.hesap_id == hesap.id))
            assert genc.ad == demo_hesaplari.GENC_ADI
            kart_sayisi = await oturum.scalar(
                select(func.count())
                .select_from(YetenekKarti)
                .where(YetenekKarti.kullanici_id == genc.id)
            )
            assert kart_sayisi == 1  # ikinci çalıştırma kart eklemedi

            # Çıkmaz sokak yok: demo ihtiyacı, demo gencin kartını sert filtrelerden
            # (şehir, çalışma modeli, müsaitlik, hesap) geçirerek aday görüyor.
            kurum_hesabi = await oturum.scalar(
                select(Hesap).where(Hesap.email == demo_hesaplari.KURUM_EPOSTA)
            )
            ihtiyac = await oturum.scalar(
                select(IhtiyacKarti)
                .join(IhtiyacKarti.kurum)
                .where(Kurum.hesap_id == kurum_hesabi.id)
            )
            adaylar = {a.yetenek_karti.kullanici_id for a in await adaylari_getir(oturum, ihtiyac)}
            assert genc.id in adaylar

    asyncio.run(senaryo())


def test_oneri_durumu_iki_siniri_da_kontrol_eder():
    """0.52 benzerlik alt sınırı geçer ama kanıtsız kartın skoru 0.39: öneri çıkmaz."""
    assert "alt sınırın" in demo_hesaplari.oneri_durumu(0.40)
    assert "skor eşiğinin" in demo_hesaplari.oneri_durumu(0.52)
    assert "görecek" in demo_hesaplari.oneri_durumu(0.60)


# --- zamani_geri_al ------------------------------------------------------------------------


def test_zaman_kaydirma_uretimde_calismaz_ve_gun_siniri():
    from scripts import zamani_geri_al as z

    with pytest.raises(z.UretimdeCalismaz):
        z.calistirilabilir_mi("production")
    for yanlis in (0, -3, 366):
        with pytest.raises(ValueError):
            z.gun_dogrula(yanlis)
    assert z.kaydirma_ifadeleri(8)[0] == (
        "UPDATE eslesme SET son_aktivite_tarihi = son_aktivite_tarihi - INTERVAL '8 days'"
    )


def test_zaman_kaydirma_butun_tarih_kolonlarini_kapsar():
    """Yeni bir tarih kolonu eklenirse ya kaydırılmalı ya bilerek dışarıda bırakılmalı."""
    from sqlalchemy import Date, DateTime

    from app.db.base import Base
    from scripts import zamani_geri_al as z

    tum = {
        (t.name, c.name)
        for t in Base.metadata.sorted_tables
        for c in t.columns
        if isinstance(c.type, DateTime | Date)
    }
    assert tum == set(z.ZAMAN_ALANLARI) | set(z.KAYDIRILMAYANLAR)


def test_zaman_kaydirma_pasiflesmeyi_gosterir(monkeypatch):
    """8 gün geri: yeni öneri 'bakılmayan öneri' olur; sıralar korunur."""
    import datetime as dt

    from app.api import canlilik as canlilik_api
    from app.models.canlilik_olayi import CanlilikOlayi
    from scripts import zamani_geri_al as z
    from tests.test_sahiplik import senaryo

    async def adimlar(istemci, d):
        once = d.E1.son_aktivite_tarihi

        @contextlib.asynccontextmanager
        async def ayni_oturum():
            yield d.oturum

        await z.kaydir(8, fabrika=ayni_oturum)
        await d.oturum.refresh(d.E1)
        assert once - d.E1.son_aktivite_tarihi == dt.timedelta(days=8)

        await canlilik_api.tarama_yap(d.oturum)
        olaylar = list(
            await d.oturum.scalars(
                select(CanlilikOlayi.tur).where(CanlilikOlayi.eslesme_id == d.E1.id)
            )
        )
        assert olaylar == ["oneri_bekliyor"]

    senaryo(adimlar)
