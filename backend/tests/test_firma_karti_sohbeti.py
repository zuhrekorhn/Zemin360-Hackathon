"""Firma kartı sohbeti (docs/plans/firma-akisi.md § 0 karar 3, § 5).

Karar mantığı LLM olmadan (Tanımlama testleriyle aynı yaklaşım); uçlar sahte
grafikle ve gerçek veritabanıyla.
"""

from __future__ import annotations

import asyncio
import uuid
from types import SimpleNamespace

from app.agents import sohbet_motoru as motor
from app.agents.firma_karti import (
    ACILIS_SORUSU,
    EK_SORULAR,
    FIRMA_KARTI,
    YEDEK_SORULAR,
    bos_taslak,
    profil_baglami,
)
from app.agents.kesif import KESIF
from app.agents.tanimlama import TANIMLAMA, TANIMLAMA_ORTAK
from app.main import app
from app.models.kurum import Kurum
from app.servisler import firma_karti as servis
from tests.test_sahiplik import durumlar, senaryo

TASLAK = {
    "ne_yapiyoruz": "Perakende için talep tahmini yapan yazılım",
    "yetkinlikler": ["talep tahmini"],
    "onceki_isler": "İki market zincirinde pilot",
    "aranan_isbirligi": None,
    "isbirligi_turleri": ["pilot"],
}


def _karar(durum: dict) -> dict:
    return asyncio.run(motor.karar(FIRMA_KARTI, durum))


# --- Karar mantığı ---------------------------------------------------------------------


def test_bos_taslak_alanlari():
    assert set(bos_taslak()) == {
        "ne_yapiyoruz",
        "yetkinlikler",
        "onceki_isler",
        "aranan_isbirligi",
        "isbirligi_turleri",
    }


def test_zorunlu_eksikse_sabit_soru_modelinki_yalnizca_konusu_eksikse():
    durum = {"taslak": bos_taslak(), "takip_turu": 0}
    assert _karar(durum)["sonraki_soru"] == YEDEK_SORULAR["ne_yapiyoruz"]

    # Model konusu dolu bir alanı sorarsa kullanılmaz.
    taslak = {**bos_taslak(), "ne_yapiyoruz": "x"}
    durum = {
        "taslak": taslak,
        "takip_turu": 1,
        "son_takip_sorusu": "Web siteniz nedir?",
        "son_takip_konusu": "diger",
    }
    assert _karar(durum)["sonraki_soru"] == YEDEK_SORULAR["yetkinlikler"]

    durum["son_takip_sorusu"] = "Hangi alanlarda güçlüsünüz?"
    durum["son_takip_konusu"] = "yetkinlikler"
    assert _karar(durum)["sonraki_soru"] == "Hangi alanlarda güçlüsünüz?"


def test_ek_sorular_bir_kez_sonra_taslak():
    taslak = {**bos_taslak(), "ne_yapiyoruz": "x", "yetkinlikler": ["y"]}
    durum = {"taslak": taslak, "takip_turu": 1}
    birinci = _karar(durum)
    assert birinci["sonraki_soru"] == EK_SORULAR["onceki_isler"]

    durum.update(ek_takip_turu=1, sorulan_ekler=["onceki_isler"])
    ikinci = _karar(durum)
    assert ikinci["sonraki_soru"] == EK_SORULAR["aranan_isbirligi"]

    durum.update(ek_takip_turu=2, sorulan_ekler=["onceki_isler", "aranan_isbirligi"])
    son = _karar(durum)
    assert son["taslak_hazir"] is True


def test_zorunlu_tavan_dolunca_taslak_eksik_kapanir_yer_tutucu_yok():
    durum = {"taslak": bos_taslak(), "takip_turu": 2, "ek_takip_turu": 2}
    son = _karar(durum)
    assert son["taslak_hazir"] is True
    # "belirtilmedi" gibi yer tutucu yazılmaz: onay formu firmaya eksiği gösterir.
    assert son["taslak"]["ne_yapiyoruz"] is None


def test_firmaya_siz_diye_sorulur():
    for soru in [ACILIS_SORUSU, *YEDEK_SORULAR.values(), *EK_SORULAR.values()]:
        kelimeler = soru.lower().replace("?", " ").replace(",", " ").split()
        assert not {"sen", "senin", "anlat", "yaz"} & set(kelimeler), soru


def test_profil_baglami_form_bilgilerini_tasir():
    kurum = SimpleNamespace(
        ad="Market X",
        tur="kurumsal",
        sektor="Perakende",
        sehir="İzmir",
        calisan_araligi="250+",
        web_sitesi="https://marketx.com",
        tanitim="Zincir market.",
    )
    baglam = profil_baglami(kurum)
    assert "SORMA" in baglam
    for parca in ("Market X", "Kurumsal", "Perakende", "İzmir", "250+", "marketx.com"):
        assert parca in baglam
    bos = SimpleNamespace(
        ad=None, tur=None, sektor=None, sehir=None, calisan_araligi=None, web_sitesi=None,
        tanitim=None,
    )  # fmt: skip
    assert profil_baglami(bos) is None


# --- Uçlar (sahte grafik, gerçek veritabanı) -------------------------------------------


class SahteGrafik:
    """Sahibi belli sohbet. `hazir=False` iken taslak henüz kapanmadı."""

    def __init__(self, sahip_hesap_id, taslak, hazir=True):
        self.sahip, self.taslak, self.hazir = str(sahip_hesap_id), taslak, hazir
        self.baslangiclar: list[dict] = []

    async def aget_state(self, _config):
        return SimpleNamespace(
            values={"sahip_hesap_id": self.sahip, "taslak_hazir": self.hazir, "taslak": self.taslak}
        )

    async def ainvoke(self, girdi, config):
        self.baslangiclar.append(girdi)
        return {"sonraki_soru": ACILIS_SORUSU, "taslak": bos_taslak(), "taslak_hazir": False}


def _grafikle(grafik, adimlar):
    async def sarili(istemci, d):
        app.state.firma_karti_grafigi = grafik(d)
        try:
            await adimlar(istemci, d)
        finally:
            del app.state.firma_karti_grafigi

    senaryo(sarili)


def test_sohbet_uclari_yetki():
    async def adimlar(istemci, d):
        oturum_id = str(uuid.uuid4())
        for yol, govde in (
            ("/kurum/kart/sohbet/baslat", {}),
            ("/kurum/kart/sohbet/cevap", {"oturum_id": oturum_id, "cevap": "x"}),
            ("/kurum/kart/onayla", {"oturum_id": oturum_id}),
        ):
            await durumlar(
                istemci, "POST", yol, {None: 401, d.genc1: 403, d.girvak: 403}, json=govde
            )

    _grafikle(lambda d: SahteGrafik(d.kurum1.hesap.id, TASLAK), adimlar)


def test_baslat_profil_baglamini_verir_kart_varsa_409():
    grafikler = {}

    def kur(d):
        grafikler["g"] = SahteGrafik(d.kurum1.hesap.id, TASLAK)
        return grafikler["g"]

    async def adimlar(istemci, d):
        kurum = await d.oturum.get(Kurum, d.kurum1.profil.id)
        kurum.tur, kurum.sektor = "girisim", "Yapay zekâ"
        await d.oturum.commit()

        yanit = await istemci.post("/kurum/kart/sohbet/baslat", headers=d.kurum1.baslik, json={})
        assert yanit.status_code == 200
        assert yanit.json()["soru"] == ACILIS_SORUSU
        baslangic = grafikler["g"].baslangiclar[0]
        assert baslangic["sahip_hesap_id"] == str(d.kurum1.hesap.id)
        assert "Girişim" in baslangic["profil_baglami"]
        assert "Yapay zekâ" in baslangic["profil_baglami"]

        await servis.karti_olustur(d.oturum, d.kurum1.profil.id, TASLAK)
        await d.oturum.commit()
        tekrar = await istemci.post("/kurum/kart/sohbet/baslat", headers=d.kurum1.baslik, json={})
        assert tekrar.status_code == 409

    _grafikle(kur, adimlar)


def test_onay_karti_yazar_hazirlar_tekrar_200(firma_karti_hazirlama_arka_plani_yok):
    cagrilar = firma_karti_hazirlama_arka_plani_yok

    async def adimlar(istemci, d):
        oturum_id = str(uuid.uuid4())
        yanit = await istemci.post(
            "/kurum/kart/onayla", headers=d.kurum1.baslik, json={"oturum_id": oturum_id}
        )
        assert yanit.status_code == 201
        kart = yanit.json()
        assert kart["ne_yapiyoruz"] == TASLAK["ne_yapiyoruz"]
        assert kart["isbirligi_turleri"] == ["pilot"]
        assert kart["versiyon"] == 1
        assert cagrilar == [(uuid.UUID(kart["id"]), 1)]

        tekrar = await istemci.post(
            "/kurum/kart/onayla", headers=d.kurum1.baslik, json={"oturum_id": oturum_id}
        )
        assert tekrar.status_code == 200
        assert tekrar.json()["id"] == kart["id"]

        # Başka bir sohbetle ikinci kart açılamaz.
        baska = await istemci.post(
            "/kurum/kart/onayla", headers=d.kurum1.baslik, json={"oturum_id": str(uuid.uuid4())}
        )
        assert baska.status_code == 409

    _grafikle(lambda d: SahteGrafik(d.kurum1.hesap.id, TASLAK), adimlar)


def test_onay_duzeltilmis_taslak_ve_eksik_taslak():
    async def adimlar(istemci, d):
        eksik = await istemci.post(
            "/kurum/kart/onayla", headers=d.kurum1.baslik, json={"oturum_id": str(uuid.uuid4())}
        )
        assert eksik.status_code == 422

        duzeltilmis = await istemci.post(
            "/kurum/kart/onayla",
            headers=d.kurum1.baslik,
            json={
                "oturum_id": str(uuid.uuid4()),
                "duzeltilmis_taslak": {
                    "ne_yapiyoruz": "Soğuk zincir lojistiği",
                    "yetkinlikler": ["depolama", "Depolama", "dağıtım"],
                },
            },
        )
        assert duzeltilmis.status_code == 201
        assert duzeltilmis.json()["yetkinlikler"] == ["depolama", "dağıtım"]

    _grafikle(lambda d: SahteGrafik(d.kurum1.hesap.id, {**TASLAK, "yetkinlikler": []}), adimlar)


def test_baskasinin_sohbeti_404_hazir_olmayan_409():
    async def adimlar(istemci, d):
        govde = {"oturum_id": str(uuid.uuid4())}
        baskasi = await istemci.post("/kurum/kart/onayla", headers=d.kurum2.baslik, json=govde)
        assert baskasi.status_code == 404
        cevap = await istemci.post(
            "/kurum/kart/sohbet/cevap",
            headers=d.kurum2.baslik,
            json={**govde, "cevap": "x"},
        )
        assert cevap.status_code == 404

        hazir_degil = await istemci.post("/kurum/kart/onayla", headers=d.kurum1.baslik, json=govde)
        assert hazir_degil.status_code == 409

    _grafikle(lambda d: SahteGrafik(d.kurum1.hesap.id, TASLAK, hazir=False), adimlar)


def test_hazir_taslakta_cevap_409():
    async def adimlar(istemci, d):
        cevap = await istemci.post(
            "/kurum/kart/sohbet/cevap",
            headers=d.kurum1.baslik,
            json={"oturum_id": str(uuid.uuid4()), "cevap": "x"},
        )
        assert cevap.status_code == 409

    _grafikle(lambda d: SahteGrafik(d.kurum1.hesap.id, TASLAK), adimlar)


def test_aciklama_yedekleri_firmaya_siz_der():
    """Açıklama yedeği ajanın hitabıyla: gence "sen", firmaya "siz"."""
    for tanim in (FIRMA_KARTI, TANIMLAMA, TANIMLAMA_ORTAK):
        assert "aklınıza" in tanim.aciklama_yedegi
    assert "aklına" in KESIF.aciklama_yedegi
