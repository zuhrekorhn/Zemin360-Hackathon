"""Eşleştirme gerekçesine giden doğrulama bilgisi dürüst olmalı.

Gerçek vaka: kanıt orijinalliği 1/3 (link iddiayla ilgisiz) olan kart için
gerekçe istemine "kanıtları doğrulandı" gidiyordu ve üç model de kartı
"doğrulanmış" diye anlattı. Artık rubrik puanları cümleye çevrilip gönderiliyor;
güçlü kanıt yokken model yine "doğrulanmış" derse gerekçe bir kez yeniden
üretiliyor, yine derse gerekçesiz bırakılıyor.

Son test gerçek modeli çağırır; varsayılanda atlanır (`CANLI_TEST=1` ile çalışır).
"""

import asyncio
import os
import uuid
from types import SimpleNamespace

import pytest

from app.agents import eslestirme
from app.agents.eslestirme import (
    DUZELTME_NOTU,
    Aday,
    dogrulama_iddiasi_var_mi,
    dogrulama_ozeti,
    gerekce_girdileri,
    guclu_kanitli_mi,
    kart_guclu_kanitli_mi,
)


def skor(orijinallik=1, olculebilirlik=3, rol=0, ucuncu=None):
    return SimpleNamespace(
        kanit_orijinalligi=orijinallik,
        sonuc_olculebilirligi=olculebilirlik,
        rol_netligi=rol,
        ucuncu_taraf_onayi=ucuncu,
    )


def kart(*skorlar, cikti_yok=False):
    ciktilar = (
        []
        if cikti_yok
        else [
            SimpleNamespace(baslik=f"Çıktı {i}", aciklama=None, guven_skoru=s)
            for i, s in enumerate(skorlar or [None], start=1)
        ]
    )
    return SimpleNamespace(
        id=uuid.uuid4(),
        rol_alani="backend geliştirici",
        deneyim_seviyesi="orta",
        sektor_ilgi_alani=["eğitim"],
        araclar_teknolojiler=["Python"],
        somut_ciktilar=ciktilar,
    )


IHTIYAC = SimpleNamespace(
    problem_tanimi="Kütüphane ödünç işleri kâğıtla yürüyor",
    basari_kriteri="3 ayda kayıtların %100'ü dijital",
    kisitlar=None,
)


# --- Güçlü kanıt kuralı -----------------------------------------------------------


def test_orijinallik_tam_ise_guclu():
    assert guclu_kanitli_mi(skor(orijinallik=3))


@pytest.mark.parametrize("ucuncu", [2, 3])
def test_referansin_olumlu_yaniti_da_dogrulamadir(ucuncu):
    """Kanıt linki zayıf olsa bile olumlu bir referans doğrulama sayılır."""
    assert guclu_kanitli_mi(skor(orijinallik=1, ucuncu=ucuncu))


@pytest.mark.parametrize(
    "s",
    [skor(orijinallik=2, ucuncu=1), skor(orijinallik=1, olculebilirlik=3, rol=3, ucuncu=0)],
    ids=["orijinallik-2-referans-zayif", "iddia-net-ama-kanit-zayif"],
)
def test_zayif_kanit_guclu_sayilmaz(s):
    """Ölçülebilirlik ve rol netliği iddianın açıklığını ölçer, doğruluğunu değil."""
    assert not guclu_kanitli_mi(s)


def test_skor_kaydi_olmayan_kart_guclu_degil():
    assert not kart_guclu_kanitli_mi(kart())


# --- Özet ---------------------------------------------------------------------------


def test_zayif_kanitta_ozet_dogrulanmis_demeyi_yasaklar():
    ozet = dogrulama_ozeti(kart(skor(orijinallik=1)))
    assert "iddiayla ilişkisi zayıf" in ozet
    assert 'kartı "doğrulanmış" diye anlatma' in ozet
    assert "güçlü kanıtla doğrulandı" not in ozet


def test_guclu_kanitta_ozet_dogrulandi_der():
    ozet = dogrulama_ozeti(kart(skor(orijinallik=1), skor(orijinallik=1, ucuncu=2)))
    assert "bir referans olumlu yanıt verdi" in ozet
    assert "Genel: en az bir çıktı güçlü kanıtla doğrulandı." in ozet


def test_ozet_dort_bileseni_de_tasir():
    ozet = dogrulama_ozeti(kart(skor(orijinallik=2, olculebilirlik=1, rol=2)))
    assert "kişinin kendi işi olduğu belirsiz" in ozet
    assert "yalnızca niteliksel" in ozet
    assert "ekip içindeki payı belirsiz" in ozet
    assert "referans istenmedi ya da yanıt gelmedi" in ozet


def test_ozet_yanit_yok_ile_olumsuz_yaniti_ayirir():
    """Bulgu 19: "yanıt yok" (None) ile "olumsuz yanıt" (0) aynı cümleye düşmez."""
    assert "referans iddiayı doğrulamadı" in dogrulama_ozeti(kart(skor(ucuncu=0)))


def test_ozet_degerlendirilmemis_basligi_uydurmaz():
    """Bulgu 17: linksiz kalemde yalnızca Referans doluysa "sonuç belirtilmemiş" denmez."""
    ozet = dogrulama_ozeti(kart(skor(orijinallik=None, olculebilirlik=None, rol=None, ucuncu=3)))
    assert "sonuç belirtilmemiş" not in ozet
    assert "sonuç henüz değerlendirilmedi" in ozet
    assert "referans güçlü biçimde onayladı" in ozet


def test_kanitsiz_ve_ciktisiz_kart():
    assert "kanıt eklenmemiş" in dogrulama_ozeti(kart())
    assert "henüz doğrulanmadı" in dogrulama_ozeti(kart())
    assert "potansiyel" in dogrulama_ozeti(kart(cikti_yok=True))


def test_ozet_istem_girdisine_gidiyor():
    girdiler = gerekce_girdileri(IHTIYAC, kart(skor(orijinallik=1)))
    assert "kanıtları doğrulandı" not in girdiler["dogrulama"]
    assert girdiler["ek_not"] == ""


# --- Koruma: "doğrulanmış" iddiası ---------------------------------------------------


@pytest.mark.parametrize(
    "metin",
    [
        "Aday doğrulanmış bir kütüphane sistemi geliştirmiş.",
        "Kanıtları doğrulandı.",
        "Kanıtları doğrulanan bir proje.",
        "DOĞRULANMIŞ deneyim",
        "Bu iş kanıtlanmıştır.",
    ],
)
def test_dogrulama_iddiasi_yakalanir(metin):
    assert dogrulama_iddiasi_var_mi(metin)


@pytest.mark.parametrize(
    "metin",
    [
        "Kart henüz doğrulanmamış.",
        "Kanıt doğrulanmadı ama sonuç sayıyla anlatılmış.",
        "Kanıt linki var ama iddiayla ilişkisi zayıf.",
    ],
)
def test_olumsuz_ifade_iddia_sayilmaz(metin):
    assert not dogrulama_iddiasi_var_mi(metin)


class SahteZincir:
    """Sırayla hazır metin döndürür, gelen girdileri kaydeder."""

    def __init__(self, *metinler):
        self.metinler = list(metinler)
        self.girdiler = []

    async def ainvoke(self, girdiler):
        self.girdiler.append(girdiler)
        return self.metinler.pop(0)


def uret(monkeypatch, yetenek_karti, *metinler):
    zincir = SahteZincir(*metinler)
    monkeypatch.setattr(eslestirme, "_gerekce_zinciri", lambda: zincir)
    aday = Aday(yetenek_karti=yetenek_karti, benzerlik=0.6, dogrulama_bonus=0.3)
    return asyncio.run(eslestirme.gerekce_uret(IHTIYAC, aday)), zincir


def test_zayif_kanitta_iddia_edilirse_duzeltme_notuyla_yeniden_uretilir(monkeypatch):
    sonuc, zincir = uret(
        monkeypatch,
        kart(skor(orijinallik=1)),
        "Aday doğrulanmış bir sistem geliştirmiş.",
        "Kanıt linki var ama iddiayla ilişkisi zayıf; sonuç sayıyla anlatılmış.",
    )
    assert sonuc.startswith("Kanıt linki var")
    assert len(zincir.girdiler) == 2
    assert zincir.girdiler[1]["ek_not"] == DUZELTME_NOTU


def test_iki_kez_iddia_edilirse_gerekcesiz_birakilir(monkeypatch):
    sonuc, zincir = uret(
        monkeypatch,
        kart(skor(orijinallik=1)),
        "Doğrulanmış bir sistem.",
        "Kanıtları doğrulandı.",
    )
    assert sonuc is None
    assert len(zincir.girdiler) == 2


def test_guclu_kanitta_dogrulandi_demek_serbest(monkeypatch):
    sonuc, zincir = uret(
        monkeypatch, kart(skor(orijinallik=1, ucuncu=3)), "Referansla doğrulanmış bir sistem."
    )
    assert sonuc == "Referansla doğrulanmış bir sistem."
    assert len(zincir.girdiler) == 1


def test_temiz_gerekce_tek_cagrida_doner(monkeypatch):
    sonuc, zincir = uret(monkeypatch, kart(skor(orijinallik=1)), "Sonuç sayıyla anlatılmış.")
    assert sonuc == "Sonuç sayıyla anlatılmış."
    assert len(zincir.girdiler) == 1


# --- Canlı: gerçek model zayıf kanıtta "doğrulanmış" diyor mu? ---------------------


@pytest.mark.skipif(os.environ.get("CANLI_TEST") != "1", reason="gerçek LLM çağrısı: CANLI_TEST=1")
def test_canli_model_zayif_kanitta_dogrulanmis_demez():
    """Korumayı değil istemi sınar: modelin ham çıktısına bakılır, 3 deneme."""
    zayif = kart(skor(orijinallik=1, olculebilirlik=3, rol=0, ucuncu=0))
    zayif.somut_ciktilar[0].baslik = "Mahalle kütüphanesi ödünç takip sistemi"
    zayif.somut_ciktilar[0].aciklama = "400 kitap ve 120 üye takip ediliyor."
    girdiler = gerekce_girdileri(IHTIYAC, zayif)

    async def uc_kez():
        eslestirme._gerekce_zinciri.cache_clear()
        return [await eslestirme._gerekce_cagir(girdiler) for _ in range(3)]

    metinler = asyncio.run(uc_kez())
    iddialar = [m for m in metinler if dogrulama_iddiasi_var_mi(m)]
    assert not iddialar, f"Model zayıf kanıtta 'doğrulanmış' dedi: {iddialar}"
