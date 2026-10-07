"""Gencin müsaitliği çoklu seçim (docs/kararlar.md G2).

Filtre: ihtiyacın tercihi gencin listesinde mi? Liste boşsa ("belirtilmedi")
aday elenmez — çalışma modelindeki kural. Saf kural ile SQL aynı şeyi söylemeli.
"""

import asyncio
import uuid

import pytest
from pydantic import ValidationError
from sqlalchemy import select

from app.agents.eslestirme import adaylari_getir
from app.api.auth import hesap_olustur
from app.core.musaitlik import (
    PROJE_BAZLI,
    STAJ,
    TAM_ZAMANLI,
    YARIM_ZAMANLI,
    musaitlik_uyar_mi,
    musaitlikleri_dogrula,
)
from app.db.base import EMBEDDING_DIM
from app.models.ihtiyac_karti import IhtiyacKarti
from app.models.kullanici import Kullanici
from app.models.kurum import Kurum
from app.models.yetenek_karti import YetenekKarti
from app.schemas.kesif import GencProfili
from tests.veritabani import geri_alinan_oturum

VEKTOR = [1.0] + [0.0] * (EMBEDDING_DIM - 1)


# --- Saf kural ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("tercih", "liste", "uyar"),
    [
        (None, [], True),  # ihtiyacın tercihi yok: filtre yok
        (None, [STAJ], True),
        (STAJ, [], True),  # genç belirtmemiş: elenmez
        (STAJ, [STAJ], True),
        (STAJ, [TAM_ZAMANLI, STAJ], True),
        (STAJ, [TAM_ZAMANLI], False),
        (PROJE_BAZLI, [YARIM_ZAMANLI, STAJ], False),
    ],
)
def test_musaitlik_uyar_mi(tercih, liste, uyar):
    assert musaitlik_uyar_mi(tercih, liste) is uyar


# --- Katı okuma (istemciden gelen liste) ----------------------------------------------------


def test_liste_kanoniklesir_tekrarsiz_ve_sirali():
    assert musaitlikleri_dogrula(["Staj", "tam zamanlı", "tam_zamanli"]) == [TAM_ZAMANLI, STAJ]


def test_bos_ya_da_none_bos_liste():
    assert musaitlikleri_dogrula(None) == []
    assert musaitlikleri_dogrula([]) == []


def test_tanimayan_deger_reddedilir():
    with pytest.raises(ValidationError):
        GencProfili(musaitlikler=["haftasonu"])


def test_tekil_metin_liste_yerine_kabul_edilmez():
    """Eski istemci `"staj"` gönderirse sessizce harf harf okunmasın."""
    with pytest.raises(ValidationError):
        GencProfili(musaitlikler="staj")


# --- SQL filtresi (gerçek veritabanı) -------------------------------------------------------


def test_aday_filtresi_tercihi_gencin_listesinde_arar():
    async def senaryo():
        async with geri_alinan_oturum() as oturum:
            kurum = Kurum(ad="Koop")
            oturum.add(kurum)

            async def genc(musaitlikler):
                hesap = await hesap_olustur(
                    oturum,
                    email=f"test-{uuid.uuid4().hex[:8]}@ornek.com",
                    sifre="yeterince-uzun",
                    rol="genc",
                    ad="Genç",
                )
                profil = await oturum.scalar(
                    select(Kullanici).where(Kullanici.hesap_id == hesap.id)
                )
                profil.musaitlikler = musaitlikler
                kart = YetenekKarti(
                    kullanici_id=profil.id,
                    rol_alani="r",
                    deneyim_seviyesi="orta",
                    embedding=VEKTOR,
                )
                oturum.add(kart)
                await oturum.flush()
                return kart.id

            staj_ve_tam = await genc([TAM_ZAMANLI, STAJ])
            yalniz_tam = await genc([TAM_ZAMANLI])
            belirtmemis = await genc([])
            await oturum.flush()

            ihtiyac = IhtiyacKarti(
                kurum_id=kurum.id,
                problem_tanimi="p",
                musaitlik_tercihi=STAJ,
                embedding=VEKTOR,
            )
            oturum.add(ihtiyac)
            await oturum.flush()

            adaylar = {a.yetenek_karti.id for a in await adaylari_getir(oturum, ihtiyac)}
            assert staj_ve_tam in adaylar
            assert belirtmemis in adaylar
            assert yalniz_tam not in adaylar

    asyncio.run(senaryo())
