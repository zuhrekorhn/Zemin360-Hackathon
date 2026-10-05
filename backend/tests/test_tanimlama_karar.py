"""Tanımlama Ajanı'nın karar mantığı — LLM çağrısı olmadan.

Keşif'ten en önemli farkı: fallback dalı YOK (docs/agent-specs.md § 2'de
böyle bir dal tanımlanmamış). Sadece eksik alan takibi var.
"""

import asyncio

from app.agents import sohbet_motoru as motor
from app.agents.tanimlama import (
    HEDEF_SORUSU,
    MAKS_ZORUNLU_TURU,
    TANIMLAMA,
    TANIMLAMA_ORTAK,
    IhtiyacCikarimi,
    bos_taslak,
)


def karar(durum: dict) -> dict:
    return asyncio.run(motor.karar(TANIMLAMA, durum))


def dolu_taslak(**degisiklikler) -> dict:
    taslak = {
        "problem_tanimi": "Destek ekibi gelen talepleri elle sınıflandırıyor",
        "basari_kriteri": "Tier-1 biletlerin %50'si insan müdahalesi olmadan çözülsün",
        "basari_olcutu": {"metrik": "insansız çözülen tier-1 bilet", "hedef_deger": "%50"},
        "kisitlar": None,
        "sehir_tercihi": None,
        "musaitlik_tercihi": None,
    }
    taslak.update(degisiklikler)
    return taslak


def test_bos_taslak_ihtiyac_alanlarini_icerir():
    assert set(bos_taslak()) == {
        "problem_tanimi",
        "basari_kriteri",
        "kisitlar",
        "sehir_tercihi",
        "calisma_modeli",
        "musaitlik_tercihi",
        "basari_olcutu",
    }


def test_olculebilir_kriter_yoksa_takip_sorusu_gelir():
    sonuc = karar({"taslak": dolu_taslak(basari_kriteri=None), "takip_turu": 0})
    assert sonuc["taslak_hazir"] is False
    assert sonuc["sonraki_soru"]


def test_llm_soru_uretmezse_sokratik_yedek_soru_kullanilir():
    sonuc = karar({"taslak": dolu_taslak(basari_kriteri=None), "takip_turu": 1})
    assert "sayıyla" in sonuc["sonraki_soru"].casefold()


def test_tavana_kadar_sorulur_sonra_taslak_bos_alanla_kapanir():
    """Yer tutucu yazılmaz: "belirtilmedi" ilana ve eşleştirme metnine giriyordu.
    Boş alan taslak ekranında zorunlu görünür, onay boş alanı kabul etmez."""
    eksik = dolu_taslak(basari_kriteri=None)
    son_soru = karar({"taslak": eksik, "takip_turu": MAKS_ZORUNLU_TURU - 1})
    assert son_soru["taslak_hazir"] is False

    sonuc = karar({"taslak": eksik, "takip_turu": MAKS_ZORUNLU_TURU})
    assert sonuc["taslak_hazir"] is True
    assert sonuc["taslak"]["basari_kriteri"] is None


def test_iki_kapida_tavan_ayni():
    assert TANIMLAMA.maks_zorunlu_turu == TANIMLAMA_ORTAK.maks_zorunlu_turu == 4


def test_alanlar_tamamsa_dogrudan_taslak():
    sonuc = karar({"taslak": dolu_taslak(), "takip_turu": 0})
    assert sonuc["taslak_hazir"] is True
    assert sonuc["sonraki_soru"] is None


def test_fallback_dali_yok():
    """Keşif'teki 'hiç projem yok' zincirinin karşılığı burada olmamalı."""
    assert TANIMLAMA.ek_dal is None


def test_bos_cikarim_mevcut_taslagi_silmez():
    onceki = dolu_taslak(kisitlar="Bütçe 100 bin TL")
    assert motor.birlestir(TANIMLAMA, onceki, IhtiyacCikarimi()) == onceki


def test_yeni_deger_eskisinin_uzerine_yazar():
    taslak = motor.birlestir(
        TANIMLAMA,
        dolu_taslak(),
        IhtiyacCikarimi(basari_kriteri="Ortalama yanıt süresi 4 saatin altına insin"),
    )
    assert taslak["basari_kriteri"] == "Ortalama yanıt süresi 4 saatin altına insin"
    # Dokunulmayan alan yerinde kalmalı
    assert taslak["problem_tanimi"] == dolu_taslak()["problem_tanimi"]


# --- Rol tarifi problem değildir -------------------------------------------
# Gerçek turda "3 yıl deneyimli full stack developer arıyoruz" doğrudan
# problem_tanimi'na yazılmıştı. Kural artık prompt'ta yazılı.


def test_rol_tarifi_problem_sayilmiyor():
    from app.agents.tanimlama import SISTEM_TALIMATI

    assert "ROL TARİFİ PROBLEM DEĞİLDİR" in SISTEM_TALIMATI
    assert "iş ilanı" in SISTEM_TALIMATI


def test_yedek_soru_hangi_sorunu_cozecegini_soruyor():
    from app.agents.tanimlama import YEDEK_SORULAR

    assert "hangi sorunu çözecek" in YEDEK_SORULAR["problem_tanimi"]


def test_basari_kriteri_sorusu_degismedi():
    """Bu soru sahada iyi çalışıyor; dokunulmadı."""
    from app.agents.tanimlama import YEDEK_SORULAR

    assert "Sayıyla ifade edebilir" in YEDEK_SORULAR["basari_kriteri"]


def test_calisma_modeli_musaitlikten_ayri_soruluyor():
    """İkisi farklı şey: biri işin nerede, diğeri ne kadar süreyle yapıldığı."""
    from app.agents.tanimlama import SISTEM_TALIMATI

    assert "calisma_modeli" in SISTEM_TALIMATI
    assert "müsaitlikten (tam/yarı zamanlı) FARKLI" in SISTEM_TALIMATI


def test_zorunlu_fazda_baska_konulu_llm_sorusu_kullanilmaz():
    """Başarı kriteri eksikken model kısıtları sorduysa sabit kriter sorusu gelir."""
    from app.agents.tanimlama import YEDEK_SORULAR

    sonuc = karar(
        {
            "taslak": dolu_taslak(basari_kriteri=None),
            "takip_turu": 0,
            "son_takip_sorusu": "Bütçeniz ne kadar?",
            "son_takip_konusu": "kisitlar",
        }
    )
    assert sonuc["sonraki_soru"] == YEDEK_SORULAR["basari_kriteri"]


def test_zorunlu_konulu_sokratik_soru_kullanilir():
    soru = "Geciken iadelerin yüzde kaçı hatırlatmayla dönerse başarılı sayarsınız?"
    sonuc = karar(
        {
            "taslak": dolu_taslak(basari_kriteri=None),
            "takip_turu": 0,
            "son_takip_sorusu": soru,
            "son_takip_konusu": "basari_kriteri",
        }
    )
    assert sonuc["sonraki_soru"] == soru


# --- Başarı ölçütü (model çıkarır, kural karar verir) ---------------------------------


def test_hedef_yoksa_bir_kez_sorulur_sonra_kapanir():
    taslak = dolu_taslak(basari_kriteri="Müşteri memnuniyeti artsın", basari_olcutu={})
    soru = karar({"taslak": taslak, "takip_turu": 1})
    assert soru["sonraki_soru"] == HEDEF_SORUSU
    assert soru["sorulan_ekler"] == ["basari_hedefi"]

    # Firma yine değer vermedi: ısrar yok, kart "belirlenecek" olarak kapanır.
    sonuc = karar({"taslak": taslak, "takip_turu": 1, **soru})
    assert sonuc["taslak_hazir"] is True


def test_olcmedigini_soyleyen_firmaya_hedef_sorulmaz():
    taslak = dolu_taslak(
        basari_kriteri="Müşteri memnuniyeti artsın", basari_olcutu={"olcum_bilinmiyor": True}
    )
    assert karar({"taslak": taslak, "takip_turu": 1})["taslak_hazir"] is True


def test_basari_kriteri_yoksa_hedef_degil_kriter_sorulur():
    taslak = dolu_taslak(basari_kriteri=None, basari_olcutu=None)
    assert karar({"taslak": taslak, "takip_turu": 0})["sonraki_soru"] != HEDEF_SORUSU


def test_olcut_alan_alan_birlesir_bos_gelen_silmez():
    from app.agents.tanimlama import BasariOlcutuCikarimi

    olcut = BasariOlcutuCikarimi(metrik="sayım süresi", mevcut_deger="1 hafta")
    ilk = motor.birlestir(TANIMLAMA, bos_taslak(), IhtiyacCikarimi(basari_olcutu=olcut))
    sonra = motor.birlestir(
        TANIMLAMA, ilk, IhtiyacCikarimi(basari_olcutu=BasariOlcutuCikarimi(hedef_deger="yarısı"))
    )
    assert sonra["basari_olcutu"] == {
        "metrik": "sayım süresi",
        "mevcut_deger": "1 hafta",
        "hedef_deger": "yarısı",
    }
    assert motor.birlestir(TANIMLAMA, sonra, IhtiyacCikarimi()) == sonra
