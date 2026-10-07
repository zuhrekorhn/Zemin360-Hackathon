"""Firma kartı: kurallar, okuma, düzenleme, hazırlama (docs/kararlar.md F9-10, § 5).

Kartın sohbetle oluşması 5b'de (tests/test_firma_karti_sohbeti.py); burada kart
servisle yazılıp uçlar sınanıyor.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.core.embeddings import firma_temsil_metni
from app.core.firma_karti import (
    eksik_kart_alanlari,
    isbirligi_turlerini_temizle,
    uzun_metin,
    yetkinlikleri_temizle,
)
from app.db.base import EMBEDDING_DIM
from app.schemas.firma_karti import FirmaKartiGirdisi, FirmaKartiGuncelleme
from app.servisler import embedding as embedding_servisi
from app.servisler import firma_karti as servis
from tests.test_sahiplik import durumlar, senaryo

KART = {
    "ne_yapiyoruz": "Perakende için talep tahmini yapan yapay zekâ yazılımı",
    "yetkinlikler": ["talep tahmini", "stok optimizasyonu"],
    "onceki_isler": "Üç bölgesel market zincirinde pilot",
    "aranan_isbirligi": "Veri paylaşabilecek bir market zinciri",
    "isbirligi_turleri": ["pilot"],
}

# --- Saf kurallar ----------------------------------------------------------------------


def test_yetkinlikler_temizlenir_tekillesir():
    assert yetkinlikleri_temizle(["  Veri  analizi ", "veri analizi", "", "ML"]) == [
        "Veri analizi",
        "ML",
    ]
    with pytest.raises(ValueError, match="çok 15"):
        yetkinlikleri_temizle([f"y{i}" for i in range(16)])
    with pytest.raises(ValueError, match="80"):
        yetkinlikleri_temizle(["a" * 81])


def test_isbirligi_turleri_sabit_sirada():
    assert isbirligi_turlerini_temizle(["yatirim", "pilot", "pilot"]) == ["pilot", "yatirim"]
    with pytest.raises(ValueError, match="Tanınmayan"):
        isbirligi_turlerini_temizle(["ortaklik"])


def test_uzun_metin_ve_eksikler():
    assert uzun_metin("  a   b ", 10, "X") == "a b"
    assert uzun_metin(" ", 10, "X") is None
    with pytest.raises(ValueError, match="X en çok 3"):
        uzun_metin("abcd", 3, "X")
    assert eksik_kart_alanlari(None, []) == ["ne_yapiyoruz", "yetkinlikler"]
    assert eksik_kart_alanlari("x", ["y"]) == []


def test_embedding_metni_firmanin_ne_yaptigini_tasir_aradigini_degil():
    metin = firma_temsil_metni(
        ne_yapiyoruz="Talep tahmini",
        yetkinlikler=["ML", "stok"],
        onceki_isler=None,
        sektor="Perakende",
    )
    assert "Talep tahmini" in metin and "ML, stok" in metin and "Perakende" in metin
    assert servis.embedding_yenilenmeli_mi({"ne_yapiyoruz"})
    assert servis.embedding_yenilenmeli_mi({"onceki_isler", "aranan_isbirligi"})
    assert not servis.embedding_yenilenmeli_mi({"aranan_isbirligi", "isbirligi_turleri"})


def test_girdi_semasi():
    assert FirmaKartiGirdisi(**KART).yetkinlikler == KART["yetkinlikler"]
    for eksik in ("ne_yapiyoruz", "yetkinlikler"):
        with pytest.raises(ValidationError):
            FirmaKartiGirdisi(**{**KART, eksik: [] if eksik == "yetkinlikler" else " "})
    with pytest.raises(ValidationError):
        FirmaKartiGirdisi(**KART, vergi_no="1")
    with pytest.raises(ValidationError):
        FirmaKartiGuncelleme(isbirligi_turleri=["bilinmeyen"])


# --- Gerçek veritabanı -----------------------------------------------------------------


async def _kart(d, **ek):
    kart = await servis.karti_olustur(d.oturum, d.kurum1.profil.id, {**KART, **ek})
    await d.oturum.commit()
    return kart


def test_uclar_yetki():
    """401 token yok, 403 firma değil. Başkasının kartı diye bir yol yok (token'ın kartı)."""

    async def adimlar(istemci, d):
        await durumlar(istemci, "GET", "/kurum/kart", {None: 401, d.genc1: 403, d.girvak: 403})
        await durumlar(
            istemci,
            "PATCH",
            "/kurum/kart",
            {None: 401, d.genc1: 403, d.girvak: 403},
            json={"onceki_isler": "x"},
        )

    senaryo(adimlar)


def test_kart_yoksa_null_ve_duzenleme_404():
    async def adimlar(istemci, d):
        yanit = await istemci.get("/kurum/kart", headers=d.kurum1.baslik)
        assert yanit.status_code == 200
        assert yanit.json() is None
        duzenle = await istemci.patch(
            "/kurum/kart", headers=d.kurum1.baslik, json={"onceki_isler": "x"}
        )
        assert duzenle.status_code == 404

    senaryo(adimlar)


def test_firma_basina_tek_kart_ve_baskasinin_karti_gorunmez():
    async def adimlar(istemci, d):
        await _kart(d)
        kendi = (await istemci.get("/kurum/kart", headers=d.kurum1.baslik)).json()
        assert kendi["firma_adi"] == "Koop Bir"
        assert kendi["versiyon"] == 1
        assert kendi["embedding_var"] is False
        baskasi = (await istemci.get("/kurum/kart", headers=d.kurum2.baslik)).json()
        assert baskasi is None
        # Panel bandı /me'den okunuyor.
        assert (await istemci.get("/me", headers=d.kurum1.baslik)).json()["firma_karti_var"]
        assert not (await istemci.get("/me", headers=d.kurum2.baslik)).json()["firma_karti_var"]

        with pytest.raises(IntegrityError):
            await servis.karti_olustur(d.oturum, d.kurum1.profil.id, KART)
        await d.oturum.rollback()

    senaryo(adimlar)


def test_duzenleme_versiyon_ve_hazirlama(firma_karti_hazirlama_arka_plani_yok):
    cagrilar = firma_karti_hazirlama_arka_plani_yok

    async def adimlar(istemci, d):
        kart = await _kart(d)
        kart.embedding = [0.0] * EMBEDDING_DIM
        kart_id = kart.id
        await d.oturum.commit()

        # Aradığı ortak değişti: versiyon artar, vektör ve hazırlama yok.
        yanit = await istemci.patch(
            "/kurum/kart",
            headers=d.kurum1.baslik,
            json={"aranan_isbirligi": "Bir lojistik firması", "isbirligi_turleri": []},
        )
        assert yanit.status_code == 200
        govde = yanit.json()
        assert govde["versiyon"] == 2
        assert govde["embedding_var"] is True
        assert govde["isbirligi_turleri"] == []
        assert cagrilar == []

        # Aynı değer: hiçbir şey değişmez.
        ayni = await istemci.patch(
            "/kurum/kart",
            headers=d.kurum1.baslik,
            json={"aranan_isbirligi": "Bir lojistik firması"},
        )
        assert ayni.json()["versiyon"] == 2

        # Ne yaptığı değişti: vektör düşer, yanıttan sonra hazırlanır.
        yeni = await istemci.patch(
            "/kurum/kart",
            headers=d.kurum1.baslik,
            json={"yetkinlikler": ["talep tahmini", "fiyat optimizasyonu"], "onceki_isler": ""},
        )
        govde = yeni.json()
        assert govde["versiyon"] == 3
        assert govde["embedding_var"] is False
        assert govde["onceki_isler"] is None
        assert cagrilar == [(kart_id, 3)]

    senaryo(adimlar)


def test_zorunlu_bosaltilamaz_toplanmayan_422():
    async def adimlar(istemci, d):
        await _kart(d)
        for govde in (
            {"ne_yapiyoruz": " "},
            {"yetkinlikler": []},
            {"ne_yapiyoruz": None},
            {"vergi_no": "1"},
            {"isbirligi_turleri": ["ortaklik"]},
        ):
            cevap = await istemci.patch("/kurum/kart", headers=d.kurum1.baslik, json=govde)
            assert cevap.status_code == 422, govde

    senaryo(adimlar)


def test_hazirlama_embedding_yazar_eski_versiyonu_atlar(monkeypatch):
    metinler: list[str] = []

    async def sahte_embedding(metin, girdi_turu="document"):
        metinler.append(metin)
        return [0.1] * EMBEDDING_DIM

    monkeypatch.setattr(embedding_servisi, "embedding_uret", sahte_embedding)

    async def adimlar(istemci, d):
        kart = await _kart(d)
        kart.versiyon = 3
        await d.oturum.commit()

        assert await servis.firma_kartini_hazirla_oturumla(d.oturum, kart.id, 2) is False
        assert metinler == []

        assert await servis.firma_kartini_hazirla_oturumla(d.oturum, kart.id, 3) is True
        assert "talep tahmini" in metinler[0]
        assert "market zinciri" not in metinler[0].split("Önceki işler")[0]
        kendi = (await istemci.get("/kurum/kart", headers=d.kurum1.baslik)).json()
        assert kendi["embedding_var"] is True

    senaryo(adimlar)


# --- Profil değişince yenileme (PATCH /kurum/profil) -----------------------------------


async def _profil_kur(d, *, kart: bool = True, **alanlar):
    """Firmanın profilini bilinen değerlere çeker; isteğe bağlı kartı da yazar."""
    kurum = d.kurum1.profil
    kurum.tur, kurum.sektor, kurum.sehir = "kobi", "Gıda", "İzmir"
    await d.oturum.commit()
    return await _kart(d) if kart else None


def test_sektor_degisince_kart_hazirlanir(
    firma_karti_hazirlama_arka_plani_yok, firma_yeniden_eslestirme_arka_plani_yok
):
    hazirlama, eslestirme = (
        firma_karti_hazirlama_arka_plani_yok,
        firma_yeniden_eslestirme_arka_plani_yok,
    )

    async def adimlar(istemci, d):
        kart = await _profil_kur(d)
        kart_id, versiyon = kart.id, kart.versiyon
        yanit = await istemci.patch(
            "/kurum/profil", headers=d.kurum1.baslik, json={"sektor": "Lojistik"}
        )
        assert yanit.status_code == 200
        assert yanit.json()["sektor"] == "Lojistik"
        assert hazirlama == [(kart_id, versiyon)]
        assert eslestirme == []

    senaryo(adimlar)


def test_sehir_ya_da_tur_degisince_yalnizca_eslestirme(
    firma_karti_hazirlama_arka_plani_yok, firma_yeniden_eslestirme_arka_plani_yok
):
    hazirlama, eslestirme = (
        firma_karti_hazirlama_arka_plani_yok,
        firma_yeniden_eslestirme_arka_plani_yok,
    )

    async def adimlar(istemci, d):
        kart = await _profil_kur(d)
        kart_id = kart.id
        for govde in ({"sehir": "Ankara"}, {"tur": "kurumsal"}):
            yanit = await istemci.patch("/kurum/profil", headers=d.kurum1.baslik, json=govde)
            assert yanit.status_code == 200
        assert eslestirme == [kart_id, kart_id]
        assert hazirlama == []

    senaryo(adimlar)


def test_sektor_ve_sehir_birlikte_degisince_tek_is(
    firma_karti_hazirlama_arka_plani_yok, firma_yeniden_eslestirme_arka_plani_yok
):
    """Hazırlama zaten ilgili ilanları eşleştirir; ikinci iş boşuna pipeline koşturmaz."""

    async def adimlar(istemci, d):
        await _profil_kur(d)
        yanit = await istemci.patch(
            "/kurum/profil", headers=d.kurum1.baslik, json={"sektor": "Lojistik", "sehir": "Ankara"}
        )
        assert yanit.status_code == 200
        assert len(firma_karti_hazirlama_arka_plani_yok) == 1
        assert firma_yeniden_eslestirme_arka_plani_yok == []

    senaryo(adimlar)


def test_ayni_degerle_ya_da_ilgisiz_alanla_kaydetmek_hicbir_sey_calistirmaz(
    firma_karti_hazirlama_arka_plani_yok, firma_yeniden_eslestirme_arka_plani_yok
):
    async def adimlar(istemci, d):
        await _profil_kur(d)
        for govde in (
            {"sektor": "Gıda", "sehir": "İzmir", "tur": "kobi"},
            {"tanitim": "Yeni tanıtım", "kurulus_yili": 2015},
        ):
            yanit = await istemci.patch("/kurum/profil", headers=d.kurum1.baslik, json=govde)
            assert yanit.status_code == 200
        assert firma_karti_hazirlama_arka_plani_yok == []
        assert firma_yeniden_eslestirme_arka_plani_yok == []

    senaryo(adimlar)


def test_karti_olmayan_firmada_profil_degisimi_hicbir_sey_calistirmaz(
    firma_karti_hazirlama_arka_plani_yok, firma_yeniden_eslestirme_arka_plani_yok
):
    async def adimlar(istemci, d):
        await _profil_kur(d, kart=False)
        yanit = await istemci.patch(
            "/kurum/profil",
            headers=d.kurum1.baslik,
            json={"sektor": "Lojistik", "sehir": "Ankara", "tur": "kurumsal"},
        )
        assert yanit.status_code == 200
        assert firma_karti_hazirlama_arka_plani_yok == []
        assert firma_yeniden_eslestirme_arka_plani_yok == []

    senaryo(adimlar)


def test_sektor_degisince_yalnizca_onerildi_kararlari_sifirlanir():
    """Karar verilmiş kayda (docs/kararlar.md G14) dokunulmaz; kararsız öneri yeniden yargılanır."""
    from sqlalchemy import select

    from app.models.eslesme import Eslesme
    from app.models.ihtiyac_karti import IhtiyacKarti

    async def adimlar(istemci, d):
        kart = await _profil_kur(d)
        ilan3 = IhtiyacKarti(kurum_id=d.kurum2.profil.id, problem_tanimi="Üçüncü ilan")
        d.oturum.add(ilan3)
        await d.oturum.flush()
        d.oturum.add_all(
            [
                Eslesme(
                    ihtiyac_karti_id=d.I2.id,
                    firma_karti_id=kart.id,
                    skor=0.6,
                    durum="onerildi",
                    gerekce_metni="Eski gerekçe",
                    uygunluk="kismen",
                ),
                Eslesme(
                    ihtiyac_karti_id=ilan3.id,
                    firma_karti_id=kart.id,
                    skor=0.6,
                    durum="kabul_edildi",
                    gerekce_metni="Karar gerekçesi",
                    uygunluk="uygun",
                ),
            ]
        )
        await d.oturum.commit()
        yanit = await istemci.patch(
            "/kurum/profil", headers=d.kurum1.baslik, json={"sektor": "Lojistik"}
        )
        assert yanit.status_code == 200
        for kayit in await d.oturum.scalars(
            select(Eslesme).where(Eslesme.firma_karti_id == kart.id)
        ):
            await d.oturum.refresh(kayit)
            if kayit.durum == "onerildi":
                assert kayit.gerekce_metni is None and kayit.uygunluk is None
            else:
                assert kayit.gerekce_metni == "Karar gerekçesi" and kayit.uygunluk == "uygun"

    senaryo(adimlar)
