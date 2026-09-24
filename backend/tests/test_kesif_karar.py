"""Keşif Ajanı'nın karar mantığı — LLM çağrısı olmadan.

Buradaki sınırlar docs/agent-specs.md § 1'den geliyor; LLM'in ne cevap
verdiğinden bağımsız olarak tutmaları gerekiyor.
"""

import asyncio

from langchain_google_genai.chat_models import (
    ChatGoogleGenerativeAIError,
    GoogleAPIError,
    GoogleRateLimitError,
)

from app.agents import sohbet_motoru as motor
from app.agents.kesif import (
    FALLBACK_SORULARI,
    MAKS_TAKIP_TURU,
    SomutCiktiTaslak,
    TaslakCikarimi,
    _birlestir,
    _cikarim_zinciri,
    _karar,
    bos_taslak,
)
from app.core.config import get_settings


def karar(durum: dict) -> dict:
    return asyncio.run(_karar(durum))


def dolu_taslak(**degisiklikler) -> dict:
    taslak = {
        "rol_alani": "backend geliştirici",
        "deneyim_seviyesi": "orta",
        "sektor_ilgi_alani": ["eğitim"],
        "araclar_teknolojiler": ["Python"],
        "somut_ciktilar": [{"baslik": "Kütüphane sistemi", "aciklama": None, "kanit_linki": None}],
    }
    taslak.update(degisiklikler)
    return taslak


def test_bos_cikarim_mevcut_taslagi_silmez():
    """LLM bir turda alanı boş döndürürse önceki cevap kaybolmamalı."""
    onceki = dolu_taslak()
    sonraki = _birlestir(onceki, TaslakCikarimi())
    assert sonraki == onceki


def test_yeni_degerler_listeye_eklenir_tekrarlanmaz():
    taslak = _birlestir(
        dolu_taslak(),
        TaslakCikarimi(
            araclar_teknolojiler=["Python", "Docker"], sektor_ilgi_alani=["sivil toplum"]
        ),
    )
    assert taslak["araclar_teknolojiler"] == ["Python", "Docker"]
    assert taslak["sektor_ilgi_alani"] == ["eğitim", "sivil toplum"]


def test_ayni_cikti_iki_kez_eklenmez():
    taslak = _birlestir(
        dolu_taslak(),
        TaslakCikarimi(somut_ciktilar=[SomutCiktiTaslak(baslik="kütüphane sistemi")]),
    )
    assert len(taslak["somut_ciktilar"]) == 1


def test_eksik_alan_takip_sorusu_getirir():
    sonuc = karar({"taslak": dolu_taslak(rol_alani=None), "takip_turu": 0, "fallback_indeksi": 0})
    assert sonuc["sonraki_soru"]
    assert sonuc["taslak_hazir"] is False


def test_zorunlu_alan_icin_iki_turdan_sonra_da_sorulur():
    """Eksik zorunlu alanla kart kapatmak sohbeti uzatmaktan kötü.

    Gerçek turda "sektör ilgisi" boş kalmıştı: tur hakkı bitmiş, kart eksik
    kaydedilmişti. Boş alan eşleştirmede doğrudan skora yansıyor.
    """
    sonuc = karar(
        {
            "taslak": dolu_taslak(rol_alani=None),
            "takip_turu": MAKS_TAKIP_TURU,
            "fallback_indeksi": 0,
        }
    )
    assert sonuc["taslak_hazir"] is False
    assert sonuc["sonraki_soru"]


def test_zorunlu_tavaninda_kart_yine_de_kapanir():
    """Sonsuz döngü olmasın: tavanda alanlar yer tutucuyla dolup kart çıkar."""
    sonuc = karar(
        {
            "taslak": dolu_taslak(rol_alani=None),
            "takip_turu": motor.MAKS_ZORUNLU_TURU,
            "fallback_indeksi": 0,
        }
    )
    assert sonuc["taslak_hazir"] is True
    assert sonuc["taslak"]["rol_alani"] == "belirtilmedi"


def test_cikti_olcutu_eksikse_sorulur():
    """Rubrik "ölçülebilir sonuç" puanlıyor; Keşif bunu sormalı."""
    sonuc = karar(
        {
            "taslak": dolu_taslak(
                somut_ciktilar=[{"baslik": "Kütüphane sistemi", "kendi_rolu": "hepsini ben yaptım"}]
            ),
            "takip_turu": 0,
            "fallback_indeksi": 0,
        }
    )
    assert sonuc["taslak_hazir"] is False
    assert "sayıyla" in sonuc["sonraki_soru"]


def test_cikti_rolu_eksikse_sorulur():
    sonuc = karar(
        {
            "taslak": dolu_taslak(
                somut_ciktilar=[{"baslik": "Kütüphane sistemi", "olculebilir_sonuc": "400 kitap"}]
            ),
            "takip_turu": 0,
            "fallback_indeksi": 0,
        }
    )
    assert sonuc["taslak_hazir"] is False
    assert "payın" in sonuc["sonraki_soru"]


def test_cikti_detaylari_tamsa_kart_kapanir():
    sonuc = karar(
        {
            "taslak": dolu_taslak(
                somut_ciktilar=[
                    {
                        "baslik": "Kütüphane sistemi",
                        "aciklama": "Ödünç takibi",
                        "olculebilir_sonuc": "400 kitap, 120 üye",
                        "kendi_rolu": "backend'i ben yazdım",
                    }
                ]
            ),
            "takip_turu": 0,
            "fallback_indeksi": 0,
        }
    )
    assert sonuc["taslak_hazir"] is True


def test_olcut_ve_rol_aciklamaya_giriyor():
    """Doğrulama Ajanı yalnızca açıklamayı okuyor; bilgi oraya taşınmalı."""
    sonuc = karar(
        {
            "taslak": dolu_taslak(
                somut_ciktilar=[
                    {
                        "baslik": "Kütüphane sistemi",
                        "aciklama": "Ödünç takip sistemi yazdım.",
                        "olculebilir_sonuc": "400 kitap ve 120 üye takip ediliyor.",
                        "kendi_rolu": "Backend'i ben yazdım.",
                    }
                ]
            ),
            "takip_turu": 0,
            "fallback_indeksi": 0,
        }
    )
    aciklama = sonuc["taslak"]["somut_ciktilar"][0]["aciklama"]
    assert "400 kitap" in aciklama
    assert "Backend'i ben yazdım" in aciklama


def test_cikti_yoksa_once_fallback_sorulur():
    sonuc = karar(
        {"taslak": dolu_taslak(somut_ciktilar=[]), "takip_turu": 0, "fallback_indeksi": 0}
    )
    assert sonuc["sonraki_soru"] == FALLBACK_SORULARI[0]
    assert sonuc["fallback_indeksi"] == 1


def test_fallback_bitince_kart_potansiyel_olur():
    """agent-specs.md § 1.4 — çıktısı olmayan kart yine de oluşur."""
    sonuc = karar(
        {
            "taslak": dolu_taslak(somut_ciktilar=[]),
            "takip_turu": 0,
            "fallback_indeksi": len(FALLBACK_SORULARI),
        }
    )
    assert sonuc["taslak_hazir"] is True
    assert sonuc["taslak"]["deneyim_seviyesi"] == "potansiyel"
    assert sonuc["sonraki_soru"] is None


def test_bos_taslak_tum_zorunlu_alanlari_icerir():
    assert set(bos_taslak()) >= {
        "rol_alani",
        "deneyim_seviyesi",
        "sektor_ilgi_alani",
        "araclar_teknolojiler",
        "somut_ciktilar",
    }


def test_kota_veya_ariza_ayni_sema_ile_yedek_modele_dusuyor(monkeypatch):
    """Ana model kullanılamazsa aynı çağrı yedek modelle tekrarlanmalı.

    İki sebep de model başına oluşuyor: günlük kota (`GoogleRateLimitError`)
    ve sağlayıcı kaynaklı geçici arıza (`GoogleAPIError`, yalnızca 5xx).
    """
    monkeypatch.setenv("GOOGLE_API_KEY", "test-anahtari")
    get_settings.cache_clear()
    _cikarim_zinciri.cache_clear()
    try:
        zincir = _cikarim_zinciri()
        ayarlar = get_settings()

        assert zincir.exceptions_to_handle == (GoogleRateLimitError, GoogleAPIError)
        assert zincir.runnable.first.model.endswith(ayarlar.gemini_model)
        # Model adı sağlayıcıya göre "models/" önekiyle gelebiliyor.
        yedekler = [f.first.model for f in zincir.fallbacks]
        assert len(yedekler) == 1
        assert yedekler[0].endswith(ayarlar.gemini_yedek_model)
        # Yedek de aynı yapılandırılmış şemayı kullanmalı, yoksa çıkarım bozulur.
        assert zincir.fallbacks[0].last == zincir.runnable.last
    finally:
        get_settings.cache_clear()
        _cikarim_zinciri.cache_clear()


def test_hatali_istek_yedek_modeli_bosuna_yormaz(monkeypatch):
    """4xx hataları yedeğe düşürmemeli: aynı istek orada da başarısız olur."""
    monkeypatch.setenv("GOOGLE_API_KEY", "test-anahtari")
    get_settings.cache_clear()
    _cikarim_zinciri.cache_clear()
    try:
        yakalananlar = _cikarim_zinciri().exceptions_to_handle
        assert not any(issubclass(ChatGoogleGenerativeAIError, h) for h in yakalananlar)
    finally:
        get_settings.cache_clear()
        _cikarim_zinciri.cache_clear()


# --- Aynı işi anlatan çıktılar --------------------------------------------


def test_ayni_is_farkli_yazimla_iki_kayit_acmaz():
    """Gerçek turda görülen vaka: "Team To Do" ve "Team ToDo" iki satır olmuştu."""
    taslak = dolu_taslak(
        somut_ciktilar=[
            {"baslik": "Team To Do Web Uygulaması", "aciklama": None, "kanit_linki": None}
        ]
    )
    sonuc = _birlestir(
        taslak,
        TaslakCikarimi(
            somut_ciktilar=[
                SomutCiktiTaslak(
                    baslik="Team ToDo Web Uygulaması",
                    kanit_linki="github.com/ornek/teamtodo",
                )
            ]
        ),
    )
    assert len(sonuc["somut_ciktilar"]) == 1


def test_ikinci_anlatimdaki_link_bos_alani_doldurur():
    taslak = dolu_taslak(
        somut_ciktilar=[
            {"baslik": "Team To Do", "aciklama": "Ekip için görev takibi", "kanit_linki": None}
        ]
    )
    sonuc = _birlestir(
        taslak,
        TaslakCikarimi(
            somut_ciktilar=[SomutCiktiTaslak(baslik="team todo", kanit_linki="github.com/ornek/x")]
        ),
    )
    cikti = sonuc["somut_ciktilar"][0]
    assert cikti["kanit_linki"] == "github.com/ornek/x"
    # İlk anlatılan açıklama korunur, üzerine yazılmaz
    assert cikti["aciklama"] == "Ekip için görev takibi"


def test_gercekten_farkli_isler_ayri_kalir():
    taslak = dolu_taslak(
        somut_ciktilar=[{"baslik": "Team To Do", "aciklama": None, "kanit_linki": None}]
    )
    sonuc = _birlestir(
        taslak, TaslakCikarimi(somut_ciktilar=[SomutCiktiTaslak(baslik="Kütüphane takip sistemi")])
    )
    assert len(sonuc["somut_ciktilar"]) == 2
