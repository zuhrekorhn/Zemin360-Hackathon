"""İlan düzenleme ucu (docs/plans/ilan-duzenleme.md).

Kural tablosu tests/test_ihtiyac_duzenleme_kurallari.py'de; burada uç: yetki,
409'lar, değişmeyen düzenlemenin yan etkisizliği, gencin ilgisinin korunması,
gerekçe sıfırlama, bildirim, embedding ve yeniden eşleştirme.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.agents.ihtiyac_duzenleme import ILAN_KAPALI, ISBIRLIGI_BASLADI
from app.api import ihtiyac_kartlari
from app.core.embeddings import EmbeddingHatasi
from app.db.base import EMBEDDING_DIM
from app.models.bildirim import TUR_FIRSAT_GUNCELLENDI, Bildirim
from app.models.eslesme import Eslesme
from app.models.ihtiyac_karti import IhtiyacKarti
from tests.test_sahiplik import durumlar, senaryo

GOVDE = {
    "problem_tanimi": "Ödünç işleri kâğıtla, iade gecikiyor",
    "basari_kriteri": "İade gecikmesi yarıya insin",
    "sehir_tercihi": "Ankara",
    "calisma_modeli": "hibrit",
}


def _yol(d) -> str:
    return f"/ihtiyac-kartlari/{d.I1.id}"


@pytest.fixture
def eslestirme_kaydi(monkeypatch):
    """Embedding sahte, eşleştirme çalışmaz; çağrılan ilanlar kaydedilir."""
    cagrilar: list = []

    async def embedding(_metin, girdi_turu):
        return [0.0] * EMBEDDING_DIM

    async def eslestir(kart_id):
        cagrilar.append(kart_id)

    monkeypatch.setattr(ihtiyac_kartlari, "embedding_uret", embedding)
    monkeypatch.setattr(ihtiyac_kartlari, "eslestirmeyi_arka_planda_calistir", eslestir)
    return cagrilar


async def _taze(oturum, model, kimlik):
    return await oturum.scalar(
        select(model).where(model.id == kimlik).execution_options(populate_existing=True)
    )


async def _bildirimler(oturum, hesap_id) -> list[Bildirim]:
    return list(
        await oturum.scalars(
            select(Bildirim).where(
                Bildirim.hesap_id == hesap_id, Bildirim.tur == TUR_FIRSAT_GUNCELLENDI
            )
        )
    )


def test_duzenleme_yetkisi(eslestirme_kaydi):
    """401 token yok, 403 genç/GİRVAK, 404 başka firmanın ilanı."""

    async def adimlar(istemci, d):
        await durumlar(
            istemci,
            "PATCH",
            _yol(d),
            {None: 401, d.genc1: 403, d.girvak: 403, d.kurum2: 404},
            json=GOVDE,
        )
        ilan = await _taze(d.oturum, IhtiyacKarti, d.I1.id)
        assert ilan.basari_kriteri is None

    senaryo(adimlar)


def test_zorunlu_alan_bossa_422(eslestirme_kaydi):
    async def adimlar(istemci, d):
        yanit = await istemci.patch(
            _yol(d), headers=d.kurum1.baslik, json={**GOVDE, "basari_kriteri": "  "}
        )
        assert yanit.status_code == 422

    senaryo(adimlar)


def test_kapali_ilan_409(eslestirme_kaydi):
    async def adimlar(istemci, d):
        await istemci.post(
            f"{_yol(d)}/kapat", headers=d.kurum1.baslik, json={"neden": "vazgecildi"}
        )
        yanit = await istemci.patch(_yol(d), headers=d.kurum1.baslik, json=GOVDE)
        assert yanit.status_code == 409
        assert yanit.json()["detail"] == ILAN_KAPALI

    senaryo(adimlar)


def test_is_birligi_baslamis_ilan_409(eslestirme_kaydi):
    async def adimlar(istemci, d):
        e1 = await d.oturum.get(Eslesme, d.E1.id)
        e1.durum = "kabul_edildi"
        await d.oturum.commit()
        yanit = await istemci.patch(_yol(d), headers=d.kurum1.baslik, json=GOVDE)
        assert yanit.status_code == 409
        assert yanit.json()["detail"] == ISBIRLIGI_BASLADI
        assert eslestirme_kaydi == []

    senaryo(adimlar)


def test_duzenleme_ilgiyi_korur_gerekceyi_sifirlar_bildirir(eslestirme_kaydi):
    async def adimlar(istemci, d):
        # Uç değişmeyen düzenlemede geri alır; paylaşılan oturumdaki nesneler süresi
        # dolmuş olur, kimlikler önceden alınır.
        genc1_hesap, genc2_hesap = d.genc1.hesap.id, d.genc2.hesap.id
        # E1: genç ilgilendi (dokunulmaz); E3: firma ilgileniyor (gerekçe yeniden yazılır).
        e1 = await d.oturum.get(Eslesme, d.E1.id)
        e1.durum = "genc_ilgilendi"
        e1.gerekce_metni = "eski gerekçe (genç)"
        e1.uygunluk = "uygun"
        e3 = Eslesme(
            ihtiyac_karti_id=d.I1.id,
            yetenek_karti_id=d.K2.id,
            skor=0.5,
            durum="ilgileniliyor",
            gerekce_metni="eski gerekçe",
            uygunluk="kismen",
        )
        d.oturum.add(e3)
        await d.oturum.commit()

        yanit = await istemci.patch(
            _yol(d), headers=d.kurum1.baslik, json={**GOVDE, "aranan": "firma"}
        )
        assert yanit.status_code == 200
        govde = yanit.json()
        assert govde["basari_kriteri"] == GOVDE["basari_kriteri"]
        assert govde["aranan"] == "genc"  # kapı değişmez
        assert govde["embedding_var"] is True
        ilan_id = d.I1.id
        assert eslestirme_kaydi == [ilan_id]

        e1 = await _taze(d.oturum, Eslesme, d.E1.id)
        assert (e1.durum, e1.skor, e1.gerekce_metni, e1.uygunluk) == (
            "genc_ilgilendi",
            0.6,
            "eski gerekçe (genç)",
            "uygun",
        )
        e3 = await _taze(d.oturum, Eslesme, e3.id)
        # Gerekçe sıfırlanınca karar da sıfırlanır (karar gerekçeye dayanır).
        assert (e3.durum, e3.gerekce_metni, e3.uygunluk) == ("ilgileniliyor", None, None)

        genc1 = await _bildirimler(d.oturum, genc1_hesap)
        genc2 = await _bildirimler(d.oturum, genc2_hesap)
        assert len(genc1) == len(genc2) == 1
        assert genc1[0].metin == "İlgilendiğin bir fırsatın ayrıntıları güncellendi."
        assert "@" not in genc1[0].metin

        # Aynı değerle ikinci düzenleme: 200, bildirim, embedding, eşleştirme yok.
        tekrar = await istemci.patch(_yol(d), headers=d.kurum1.baslik, json=GOVDE)
        assert tekrar.status_code == 200
        assert len(await _bildirimler(d.oturum, genc1_hesap)) == 1
        assert eslestirme_kaydi == [ilan_id]

    senaryo(adimlar)


def test_embedding_hesaplanamazsa_duzenleme_kaydedilir(monkeypatch):
    cagrilar: list = []

    async def embedding(_metin, girdi_turu):
        raise EmbeddingHatasi("yok")

    async def eslestir(kart_id):
        cagrilar.append(kart_id)

    monkeypatch.setattr(ihtiyac_kartlari, "embedding_uret", embedding)
    monkeypatch.setattr(ihtiyac_kartlari, "eslestirmeyi_arka_planda_calistir", eslestir)

    async def adimlar(istemci, d):
        yanit = await istemci.patch(_yol(d), headers=d.kurum1.baslik, json=GOVDE)
        assert yanit.status_code == 200
        assert yanit.json()["embedding_var"] is False
        assert yanit.json()["problem_tanimi"] == GOVDE["problem_tanimi"]
        assert cagrilar == []

    senaryo(adimlar)
