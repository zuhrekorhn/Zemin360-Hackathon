"""Ortak ilanı ve iki kapı (docs/plans/firma-akisi.md § 0 kararlar 4-5, § 5).

Aynı motor, aynı ihtiyaç kartı; ikinci soru seti. Kapı sohbetin başında
seçilir, durumda saklanır; sonraki istekler grafiği durumdan seçer. Firma
adayları 7. adımda: bu adımda ortak ilanına kimse önerilmez, gençler de.
"""

from __future__ import annotations

import asyncio
import uuid
from types import SimpleNamespace

from app.agents import sohbet_motoru as motor
from app.agents.tanimlama import (
    ACILIS_SORUSU_ORTAK,
    HEDEF_SORUSU,
    TANIMLAMA_ORTAK,
    YEDEK_SORULAR_ORTAK,
    bos_ortak_taslak,
)
from app.api import ihtiyac_kartlari
from app.core.firma_profili import firma_turlerini_temizle
from app.db.base import EMBEDDING_DIM
from app.main import app
from app.models.eslesme import Eslesme
from app.models.ihtiyac_karti import IhtiyacKarti
from app.models.kurum import Kurum
from app.models.yetenek_karti import YetenekKarti
from app.servisler import eslestirme as eslestirme_servisi
from app.servisler import kart_hazirlama
from tests.test_sahiplik import senaryo

VEKTOR = [1.0] + [0.0] * (EMBEDDING_DIM - 1)

ORTAK_TASLAK = {
    "problem_tanimi": "Bozulan ürün oranı yüksek",
    "basari_kriteri": "Bozulma 6 ayda %20 azalsın",
    "kisitlar": None,
    "isbirligi_turu": "pilot",
    "aranan_firma_turleri": ["girisim", "bilinmeyen"],
    "sehir_tercihi": None,
    # Ortak ilanında yazılmamalı:
    "calisma_modeli": "hibrit",
    "musaitlik_tercihi": "staj",
}


# --- Soru seti (LLM yok) ---------------------------------------------------------------


def test_ortak_soru_seti():
    assert set(bos_ortak_taslak()) == {
        "problem_tanimi",
        "basari_kriteri",
        "kisitlar",
        "isbirligi_turu",
        "sehir_tercihi",
        "aranan_firma_turleri",
        "basari_olcutu",
    }
    durum = {"taslak": bos_ortak_taslak(), "takip_turu": 0}
    assert (
        asyncio.run(motor.karar(TANIMLAMA_ORTAK, durum))["sonraki_soru"]
        == (YEDEK_SORULAR_ORTAK["problem_tanimi"])
    )
    for soru in [ACILIS_SORUSU_ORTAK, HEDEF_SORUSU, *YEDEK_SORULAR_ORTAK.values()]:
        kelimeler = set(soru.lower().replace("?", " ").replace(":", " ").split())
        assert not {"sen", "senin", "anlat", "yaz"} & kelimeler, soru


def test_firma_turleri_hosgorulu_temizlenir():
    assert firma_turlerini_temizle(["kurumsal", "x", "girisim", "girisim"]) == [
        "girisim",
        "kurumsal",
    ]
    assert firma_turlerini_temizle(None) == []


# --- Uçlar (sahte grafikler, gerçek veritabanı) ----------------------------------------


class SahteGrafik:
    def __init__(self, ad, degerler=None):
        self.ad, self.degerler, self.cagrilar = ad, degerler, []

    async def aget_state(self, _config):
        return SimpleNamespace(values=self.degerler or {})

    async def ainvoke(self, girdi, config):
        self.cagrilar.append(girdi)
        return {"sonraki_soru": f"{self.ad} sorusu", "taslak": {}, "taslak_hazir": False,
                "aranan": (self.degerler or girdi).get("aranan")}  # fmt: skip


def _iki_grafikle(degerler_uret, adimlar):
    async def sarili(istemci, d):
        degerler = degerler_uret(d) if degerler_uret else None
        app.state.tanimlama_grafigi = SahteGrafik("genc", degerler)
        app.state.tanimlama_ortak_grafigi = SahteGrafik("ortak", degerler)
        try:
            await adimlar(istemci, d)
        finally:
            del app.state.tanimlama_grafigi
            del app.state.tanimlama_ortak_grafigi

    senaryo(sarili)


def test_baslat_kapiya_gore_grafik_ve_baglam():
    async def adimlar(istemci, d):
        kurum = await d.oturum.get(Kurum, d.kurum1.profil.id)
        kurum.tur, kurum.sektor = "kurumsal", "Perakende"
        await d.oturum.commit()

        ortak = await istemci.post(
            "/tanimlama/sohbet/baslat", headers=d.kurum1.baslik, json={"aranan": "firma"}
        )
        assert ortak.status_code == 200
        assert ortak.json()["soru"] == "ortak sorusu"
        assert ortak.json()["aranan"] == "firma"
        girdi = app.state.tanimlama_ortak_grafigi.cagrilar[0]
        assert girdi["aranan"] == "firma"
        assert "Perakende" in girdi["profil_baglami"]

        # Eski istemci gövdesi ({}) genç kapısı. cf60c8a'dan beri (bilinçli) genç kapısı da
        # firmanın profilini bağlam olarak alır: örnek sorular sektöre uyarlansın,
        # kayıt bilgileri sorulmasın. Eski beklenti "bağlam yok"tu.
        genc = await istemci.post("/tanimlama/sohbet/baslat", headers=d.kurum1.baslik, json={})
        assert genc.json()["soru"] == "genc sorusu"
        genc_girdi = app.state.tanimlama_grafigi.cagrilar[0]
        assert genc_girdi["aranan"] == "genc"
        assert "Perakende" in genc_girdi["profil_baglami"]

        gecersiz = await istemci.post(
            "/tanimlama/sohbet/baslat", headers=d.kurum1.baslik, json={"aranan": "herkes"}
        )
        assert gecersiz.status_code == 422

    _iki_grafikle(None, adimlar)


def test_cevap_durumdaki_kapiya_gider():
    def degerler(d):
        return {
            "sahip_hesap_id": str(d.kurum1.hesap.id),
            "aranan": "firma",
            "taslak_hazir": False,
            "taslak": {},
        }

    async def adimlar(istemci, d):
        yanit = await istemci.post(
            "/tanimlama/sohbet/cevap",
            headers=d.kurum1.baslik,
            json={"oturum_id": str(uuid.uuid4()), "cevap": "Soğuk zincirde kayıp var"},
        )
        assert yanit.status_code == 200
        assert yanit.json()["soru"] == "ortak sorusu"
        assert app.state.tanimlama_grafigi.cagrilar == []

    _iki_grafikle(degerler, adimlar)


def test_ortak_ilani_onayi_alanlari_yazar(monkeypatch):
    async def uret(_metin, girdi_turu="document"):
        return VEKTOR

    monkeypatch.setattr(ihtiyac_kartlari, "embedding_uret", uret)

    def degerler(d):
        return {
            "sahip_hesap_id": str(d.kurum1.hesap.id),
            "aranan": "firma",
            "taslak_hazir": True,
            "taslak": ORTAK_TASLAK,
        }

    async def adimlar(istemci, d):
        yanit = await istemci.post(
            "/tanimlama/kart/onayla",
            headers=d.kurum1.baslik,
            json={"oturum_id": str(uuid.uuid4())},
        )
        assert yanit.status_code == 201
        kart = yanit.json()
        assert kart["aranan"] == "firma"
        assert kart["aranan_firma_turleri"] == ["girisim"]
        assert kart["isbirligi_turu"] == "pilot"
        assert kart["calisma_modeli"] is None
        assert kart["musaitlik_tercihi"] is None

        me = (await istemci.get("/me", headers=d.kurum1.baslik)).json()
        assert {k["id"]: k["aranan"] for k in me["ihtiyac_kartlari"]}[kart["id"]] == "firma"

        # Formda düzeltilen türler katı okunur.
        hatali = await istemci.post(
            "/tanimlama/kart/onayla",
            headers=d.kurum1.baslik,
            json={
                "oturum_id": str(uuid.uuid4()),
                "duzeltilmis_taslak": {**ORTAK_TASLAK, "musaitlik_tercihi": None},
            },
        )
        assert hatali.status_code == 422

    _iki_grafikle(degerler, adimlar)


def test_ortak_ilanina_genc_onerilmez():
    async def adimlar(istemci, d):
        kart = await d.oturum.get(YetenekKarti, d.K1.id)
        kart.embedding = VEKTOR
        ortak = IhtiyacKarti(
            kurum_id=d.kurum1.profil.id,
            problem_tanimi="Ortak arıyoruz",
            aranan="firma",
            embedding=VEKTOR,
        )
        d.oturum.add(ortak)
        await d.oturum.commit()

        # Kart hazırlama ortak ilanını aday listesine almaz.
        ilgili = await kart_hazirlama.ilgili_ihtiyac_kartlari(d.oturum, d.K1.id)
        assert ortak.id not in ilgili

        # Pipeline ortak ilanında genç aday aramaz, eşleşme yazmaz.
        async def aday_aranmamali(*_):
            raise AssertionError("ortak ilanında genç aday arandı")

        from pytest import MonkeyPatch

        with MonkeyPatch.context() as mp:
            mp.setattr(eslestirme_servisi, "adaylari_getir", aday_aranmamali)
            assert await eslestirme_servisi.pipeline_calistir(d.oturum, ortak) == []
        sayi = await d.oturum.scalar(
            Eslesme.__table__.select()
            .with_only_columns(Eslesme.id)
            .where(Eslesme.ihtiyac_karti_id == ortak.id)
        )
        assert sayi is None

    senaryo(adimlar)


def test_sohbet_geri_yuklenir_baskasina_404():
    """Sayfa yenilenince sohbet checkpointer'dan geri gelir (mesajlar, kapı, taslak)."""
    from langchain_core.messages import AIMessage, HumanMessage

    def degerler(d):
        return {
            "sahip_hesap_id": str(d.kurum1.hesap.id),
            "aranan": "firma",
            "mesajlar": [AIMessage(content="Soru?"), HumanMessage(content="Cevap.")],
            "sonraki_soru": "Soru?",
            "taslak": {"problem_tanimi": "Bozulma yüksek"},
            "taslak_hazir": False,
        }

    async def adimlar(istemci, d):
        oturum_id = str(uuid.uuid4())
        yanit = await istemci.get(f"/tanimlama/sohbet/{oturum_id}", headers=d.kurum1.baslik)
        assert yanit.status_code == 200
        govde = yanit.json()
        assert govde["aranan"] == "firma"
        assert govde["mesajlar"] == [
            {"kim": "ajan", "metin": "Soru?"},
            {"kim": "kullanici", "metin": "Cevap."},
        ]
        assert govde["taslak"]["problem_tanimi"] == "Bozulma yüksek"

        baskasi = await istemci.get(f"/tanimlama/sohbet/{oturum_id}", headers=d.kurum2.baslik)
        assert baskasi.status_code == 404
        genc = await istemci.get(f"/tanimlama/sohbet/{oturum_id}", headers=d.genc1.baslik)
        assert genc.status_code == 403

    _iki_grafikle(degerler, adimlar)
