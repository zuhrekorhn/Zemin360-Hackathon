"""Tanımlama Ajanı'nın karar mantığı — LLM çağrısı olmadan.

Keşif'ten en önemli farkı: fallback dalı YOK (docs/agent-specs.md § 2'de
böyle bir dal tanımlanmamış). Sadece eksik alan takibi var.
"""

import asyncio

from app.agents import sohbet_motoru as motor
from app.agents.tanimlama import TANIMLAMA, IhtiyacCikarimi, bos_taslak


def karar(durum: dict) -> dict:
    return asyncio.run(motor.karar(TANIMLAMA, durum))


def dolu_taslak(**degisiklikler) -> dict:
    taslak = {
        "problem_tanimi": "Destek ekibi gelen talepleri elle sınıflandırıyor",
        "basari_kriteri": "Tier-1 biletlerin %50'si insan müdahalesi olmadan çözülsün",
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
        "musaitlik_tercihi",
    }


def test_olculebilir_kriter_yoksa_takip_sorusu_gelir():
    sonuc = karar({"taslak": dolu_taslak(basari_kriteri=None), "takip_turu": 0})
    assert sonuc["taslak_hazir"] is False
    assert sonuc["sonraki_soru"]


def test_llm_soru_uretmezse_sokratik_yedek_soru_kullanilir():
    sonuc = karar({"taslak": dolu_taslak(basari_kriteri=None), "takip_turu": 1})
    assert "sayıyla" in sonuc["sonraki_soru"].casefold()


def test_iki_tur_sonra_taslak_kapanir():
    sonuc = karar({"taslak": dolu_taslak(basari_kriteri=None), "takip_turu": motor.MAKS_TAKIP_TURU})
    assert sonuc["taslak_hazir"] is True
    assert sonuc["taslak"]["basari_kriteri"] == "belirtilmedi"


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
