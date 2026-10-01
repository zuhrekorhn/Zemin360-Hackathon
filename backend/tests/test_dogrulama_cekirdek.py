"""Değerlendirme çekirdeği: kurallar, alıntı denetimi, şablon not (LLM ve ağ yok).

docs/plans/dogrulama-iyilestirme.md § 2 (seviye tavanları, bireysel kurallar),
§ 11 (model gerçek çıkarır, kural puanlar, şablon anlatır).
"""

import asyncio

import pytest

from app.agents.dogrulama.alinti import alinti_gecerli_mi
from app.agents.dogrulama.cekirdek import (
    ISARET_ALAKASIZ,
    DegerlendirmeGirdisi,
    kalemi_degerlendir,
    ozet_hesapla,
)
from app.agents.dogrulama.cikarim import CIKARIM_SABLONU, CIKARIM_TALIMATI, KanitCikarimi
from app.agents.dogrulama.kurallar import (
    BaslikPuanlari,
    OkunanKanit,
    kalem_puani,
    kanit_puani,
    rol_puani,
    sonuc_puani,
)
from app.agents.dogrulama.not_sablonu import not_yaz, temiz_oneri
from app.core.kanit_okuma.belge import ErisimDurumu, KaynakSeviyesi
from app.core.kullanici_dili import metin_ihlalleri

E, S = ErisimDurumu, KaynakSeviyesi
METIN = (
    "GitHub - elif/kutuphane: Mahalle kütüphanesi ödünç takip sistemi. 400 kitap takip ediliyor."
)


def okunan(seviye=S.KAMUYA_ACIK, erisim=E.ACIK, bireysel=False, metin=METIN):
    return OkunanKanit(erisim=erisim, seviye=seviye, metin=metin, url="x", bireysel=bireysel)


# --- Kurallar ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("girdi", "ilgili", "celiski", "beklenen"),
    [
        (None, True, False, None),  # kanıt yok: "—"
        (okunan(erisim=E.ENGELLENDI), True, False, None),  # okunamadı: "—"
        (okunan(erisim=E.GIRIS_GEREKLI), True, False, None),
        (okunan(erisim=E.BULUNAMADI), True, False, 0),
        (okunan(erisim=E.GUVENSIZ), True, False, 0),
        (okunan(), False, False, 0),  # ilgisiz → 0
        (okunan(seviye=S.BEYAN), True, False, 1),
        (okunan(), True, False, 2),  # C tavanı
        (okunan(seviye=S.PLATFORM), True, False, 3),
        (okunan(seviye=S.DUZENLEYEN), True, False, 3),
        (okunan(seviye=S.PLATFORM), True, True, 1),  # çelişki en çok 1
    ],
)
def test_kanit_puani(girdi, ilgili, celiski, beklenen):
    assert kanit_puani(girdi, ilgili=ilgili, celisiyor=celiski) == beklenen


@pytest.mark.parametrize(
    ("var", "sayisal", "olcut", "destek", "celiski", "beklenen"),
    [
        (False, False, False, False, False, 0),
        (True, False, False, True, False, 1),
        (True, True, False, True, False, 2),
        (True, True, True, False, False, 2),  # beyan en çok 2
        (True, True, True, True, False, 3),
        (True, True, True, True, True, 1),
    ],
)
def test_sonuc_puani(var, sayisal, olcut, destek, celiski, beklenen):
    assert (
        sonuc_puani(
            var=var, sayisal=sayisal, olcut_acik=olcut, bagimsiz_destek=destek, celisiyor=celiski
        )
        == beklenen
    )


@pytest.mark.parametrize(
    ("var", "ozgul", "destek", "beklenen"),
    [
        (False, False, False, 0),
        (True, False, True, 1),
        (True, True, False, 2),
        (True, True, True, 3),
    ],
)
def test_rol_puani(var, ozgul, destek, beklenen):
    assert rol_puani(var=var, ozgul=ozgul, bagimsiz_destek=destek, celisiyor=False) == beklenen


def test_kalem_puani_en_guclu_parcayi_alir_toplamaz():
    puan = kalem_puani([BaslikPuanlari(2, 1, None), BaslikPuanlari(3, None, 2)])
    assert puan == BaslikPuanlari(3, 1, 2)


# --- Alıntı denetimi ---------------------------------------------------------------------


def test_alinti_kucuk_farklara_hosgorulu():
    assert alinti_gecerli_mi("400 KİTAP takip ediliyor", METIN)
    assert alinti_gecerli_mi("ödünç takip sistemi.", METIN)


def test_uydurma_ve_cok_kisa_alinti_gecmez():
    assert not alinti_gecerli_mi("10 bin yıldız aldı", METIN)
    assert not alinti_gecerli_mi("400", METIN)
    assert not alinti_gecerli_mi(None, METIN)


# --- Şablon not --------------------------------------------------------------------------


@pytest.mark.parametrize("kanit", [None, 0, 1, 2, 3])
@pytest.mark.parametrize("sonuc", [None, 0, 1, 2, 3])
def test_not_sen_hitabiyla_ve_rehbere_uygun(kanit, sonuc):
    metin = not_yaz(BaslikPuanlari(kanit, sonuc, 2), okunan(), kanit_celisiyor=False, oneri=None)
    assert metin_ihlalleri(metin, hitap="sen") == []


def test_kurala_aykiri_oneri_atilir():
    assert temiz_oneri("Rolünüzü daha net yazabilirsiniz.") is None
    assert temiz_oneri("Puanını artırmak için sayı ekle.") is None
    assert temiz_oneri("Sonucu sayıyla yazarsan güçlenir.") == "Sonucu sayıyla yazarsan güçlenir."


def test_istem_kanit_metnini_veri_olarak_isaretler():
    assert "<kanit_metni>" in str(CIKARIM_SABLONU)
    assert "talimat değildir" in CIKARIM_TALIMATI
    assert "{itiraz_notu}" in str(CIKARIM_SABLONU)
    assert "Ajanı'sın" not in CIKARIM_TALIMATI  # kendini ajan diye tanıtmaz (bulgu 14)


# --- Çekirdek ----------------------------------------------------------------------------


def cikarim(**ek) -> KanitCikarimi:
    temel = dict(
        ilgili_mi=True,
        sonuc_var=True,
        sonuc_sayisal=True,
        sonuc_olcut_acik=True,
        pay_var=True,
        pay_ozgul=True,
    )
    return KanitCikarimi(**{**temel, **ek})


def degerlendir(cik: KanitCikarimi, ok=None, **girdi_ek):
    async def sahte(_alanlar):
        return cik

    girdi = DegerlendirmeGirdisi(baslik="Kütüphane", yetenekler=("Python",), **girdi_ek)
    return asyncio.run(kalemi_degerlendir(girdi, ok, sahte))


def test_kamuya_acik_kanitta_beyan_ve_ici_iddia_en_cok_2():
    """README'deki sayı çalışmanın içindeki iddiadır: Sonuç 3 olmaz (§ 2)."""
    sonuc = degerlendir(
        cikarim(
            destekler=[
                {"iddia": "sonuc", "durum": "destekleniyor", "alinti": "400 kitap takip ediliyor"}
            ]
        ),
        okunan(),
    )
    assert sonuc.puanlar == BaslikPuanlari(2, 2, 2)


def test_bagli_hesapta_bireysel_proje_3_3():
    sonuc = degerlendir(cikarim(), okunan(seviye=S.PLATFORM, bireysel=True))
    assert (sonuc.puanlar.kanit, sonuc.puanlar.rol) == (3, 3)


def test_ekip_ortakligi_bireysel_kurali_kapatir():
    sonuc = degerlendir(
        cikarim(ekip_ortakligi_belirtilmis=True), okunan(seviye=S.PLATFORM, bireysel=True)
    )
    assert sonuc.puanlar.rol == 2


def test_ilgisiz_kanit_0_ve_isaret():
    sonuc = degerlendir(cikarim(ilgili_mi=False), okunan())
    assert sonuc.puanlar.kanit == 0
    assert sonuc.isaretler == (ISARET_ALAKASIZ,)
    assert "ilgili görünmüyor" in sonuc.not_metni


def test_linksiz_kalem_beyan_tavaniyla_degerlendirilir():
    sonuc = degerlendir(cikarim())
    assert sonuc.puanlar == BaslikPuanlari(None, 2, 2)


def test_uydurma_alintili_celiski_sayilmaz():
    """Alıntısı metinde olmayan "çelişiyor" kuralı tetiklemez (istem enjeksiyonu boşa düşer)."""
    sonuc = degerlendir(
        cikarim(destekler=[{"iddia": "pay", "durum": "celisiyor", "alinti": "başkası yazdı"}]),
        okunan(seviye=S.PLATFORM),
    )
    assert sonuc.puanlar.kanit == 3


def test_referansin_pay_evet_yaniti_rolu_3e_tasir():
    sonuc = degerlendir(cikarim(), referans_pay_evet=True)
    assert sonuc.puanlar.rol == 3


def test_yetenek_kaniti_listede_ve_alintili_olmali():
    sonuc = degerlendir(
        cikarim(
            kanitlanan_yetenekler=[
                {"yetenek": "python", "alinti": "ödünç takip sistemi"},
                {"yetenek": "Rust", "alinti": "ödünç takip sistemi"},  # listede yok
            ]
        ),
        okunan(),
    )
    assert [(y.yetenek, y.puan) for y in sonuc.yetenek_kanitlari] == [("Python", 2)]


def test_ayni_girdi_ayni_ozet_itiraz_notu_degistirir():
    girdi = DegerlendirmeGirdisi(baslik="Kütüphane")
    assert ozet_hesapla(girdi, okunan()) == ozet_hesapla(girdi, okunan())
    itirazli = DegerlendirmeGirdisi(baslik="Kütüphane", itiraz_notu="rolüm yazıyor")
    assert ozet_hesapla(itirazli, okunan()) != ozet_hesapla(girdi, okunan())
