"""Genç ana sayfası: fırsatlar, ilgiler, 'Kartını güçlendir' (docs/plans/genc-akisi.md § 7)."""

import pytest

from app.agents.guclendirme import (
    FirsatSirasi,
    bonus_farki,
    guclendirme_metni,
    one_cikacagi_firsat_sayisi,
    sira,
)
from app.models.eslesme import Eslesme
from tests.test_sahiplik import durumlar, senaryo

# --- Güçlendirme hesabı (saf) ---------------------------------------------------------------


def test_sira():
    assert sira(0.6, []) == 1
    assert sira(0.6, [0.7, 0.5, 0.65]) == 3
    assert sira(0.7, [0.7]) == 1  # eşitlik öne geçmek sayılmaz, geride de bırakmaz


def test_bonus_farki_tek_kanitsiz_calisma():
    """Göstergesiz tek çalışma: kanıt 3/3 olursa bonus 3/12, skora 0.25 × 0.25."""
    # (3, 0, 0, —) → 3/9; 0.25 × 1/3. Referans "—" paydaya girmez.
    assert bonus_farki({"a": None}, "a", 0) == pytest.approx(0.25 / 3)


def test_bonus_farki_mevcut_bilesenler_korunur():
    # (1, 3, 3, 0) → (3, 3, 3, 0): bonus 7/12 → 9/12
    assert bonus_farki({"a": (1, 3, 3, 0)}, "a", 0) == pytest.approx(0.25 * 2 / 12)


def test_bonus_farki_pilot_tavani():
    """Pilot ve güçlü gösterge bonusu zaten tavandaysa kanıtın etkisi yok."""
    assert bonus_farki({"a": (3, 3, 3, 3), "b": None}, "b", 1) == 0.0


@pytest.mark.parametrize(
    "siralar,fark,beklenen",
    [
        ([FirsatSirasi(0.60, [0.62, 0.50])], 0.0625, 1),  # 0.62'yi geçer
        ([FirsatSirasi(0.60, [0.70])], 0.0625, 0),  # yetişemez
        ([FirsatSirasi(0.60, [0.62]), FirsatSirasi(0.50, [0.40])], 0.0625, 1),  # zaten 1.
        ([FirsatSirasi(0.60, [0.62])], 0.0, 0),
    ],
)
def test_one_cikacagi_firsat_sayisi(siralar, fark, beklenen):
    assert one_cikacagi_firsat_sayisi(siralar, fark) == beklenen


def test_guclendirme_metni_sayiyi_girdiden_alir():
    assert guclendirme_metni(2) == "Bu çalışmaya kanıt eklersen 2 fırsatta öne çıkabilirsin."
    assert guclendirme_metni(0) == "Kanıt eklemek, yeni fırsatlarda kartını güçlendirir."


# --- Uçlar (gerçek veritabanı; dünya tests/test_sahiplik.py) --------------------------------

ONAY = {"iletisim_onayi": True}


def test_firsatlar_ve_ilgiler():
    async def adimlar(istemci, d):
        # K1 için I2'de düşük skorlu (0.3) bir kayıt. Eskiden skor eşiğinin altında
        # kalıp görünmezdi; eşik kalktı, skor yalnızca sıralar: fırsat olarak görünür, sonda.
        d.oturum.add(
            Eslesme(ihtiyac_karti_id=d.I2.id, yetenek_karti_id=d.K1.id, skor=0.3, durum="onerildi")
        )
        await d.oturum.commit()

        firsatlar = (await istemci.get("/eslestirme/firsatlarim", headers=d.genc1.baslik)).json()
        assert [f["uyum"] for f in firsatlar] == [0.6, 0.3]
        assert firsatlar[0]["eslesme_id"] == str(d.E1.id)
        assert firsatlar[0]["ihtiyac_karti"]["kurum"]["ad"] == "Koop Bir"
        assert firsatlar[0]["iletisim"] is None
        assert d.kurum1.hesap.email not in str(firsatlar)

        await istemci.post(f"/eslestirme/{d.E1.id}/genc-ilgi", headers=d.genc1.baslik, json=ONAY)
        kalan = (await istemci.get("/eslestirme/firsatlarim", headers=d.genc1.baslik)).json()
        assert [f["uyum"] for f in kalan] == [0.3]
        ilgiler = (await istemci.get("/eslestirme/ilgilerim", headers=d.genc1.baslik)).json()
        assert [(i["eslesme_id"], i["durum"]) for i in ilgiler] == [
            (str(d.E1.id), "genc_ilgilendi")
        ]

        # Firmanın başlattığı ilgi (E2) gencin "ilgilerim" listesinde değil.
        assert (await istemci.get("/eslestirme/ilgilerim", headers=d.genc2.baslik)).json() == []

        # Kapalı ihtiyaçtaki öneri fırsat değildir.
        d.E1.durum = "onerildi"
        d.I1.durum = "kapandi"
        d.I2.durum = "kapandi"
        await d.oturum.commit()
        assert (await istemci.get("/eslestirme/firsatlarim", headers=d.genc1.baslik)).json() == []

        await durumlar(
            istemci, "GET", "/eslestirme/firsatlarim", {None: 401, d.kurum1: 403, d.girvak: 403}
        )
        await durumlar(istemci, "GET", "/eslestirme/ilgilerim", {None: 401, d.kurum1: 403})

    senaryo(adimlar)


def test_guclendir_gercek_skorlardan_sayar():
    async def adimlar(istemci, d):
        # I1'de K1 (0.60) ile yarışan K2 (0.62): C1'e tam kanıt eklenirse K1 öne geçer.
        d.oturum.add(
            Eslesme(ihtiyac_karti_id=d.I1.id, yetenek_karti_id=d.K2.id, skor=0.62, durum="onerildi")
        )
        await d.oturum.commit()

        yanit = await istemci.get(f"/yetenek-kartlari/{d.K1.id}/guclendir", headers=d.genc1.baslik)
        assert yanit.status_code == 200
        assert yanit.json() == [
            {
                "somut_cikti_id": str(d.C1.id),
                "baslik": "Kütüphane sistemi",
                "one_cikacagi_firsat": 1,
                "metin": "Bu çalışmaya kanıt eklersen 1 fırsatta öne çıkabilirsin.",
            }
        ]
        await durumlar(
            istemci,
            "GET",
            f"/yetenek-kartlari/{d.K1.id}/guclendir",
            {None: 401, d.kurum1: 403, d.genc2: 404},
        )

    senaryo(adimlar)
