"""LLM katmanları, yedek zincir ve token kaydı — ağa çıkmadan.

Katmanlar (app/core/llm.py): çıkarım işleri hızlı modelde, gerekçe ve rubrik
güçlü modelde. Model adları .env'den okunur. Yedek model sağlayıcı arızası
(5xx, zaman aşımı), anlık hız sınırı (429) ve kullanılamayan model (404) için;
diğer 4xx için değil. Açılışta model adları sağlayıcının listesiyle karşılaştırılır.
"""

import logging
import uuid

import httpx
import pytest
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, LLMResult
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_genai.chat_models import (
    GoogleAPIError,
    GoogleAuthenticationError,
    GoogleInvalidRequestError,
    GoogleModelNotFoundError,
    GooglePermissionDeniedError,
    GoogleRateLimitError,
)

from app.agents import eslestirme, firma_karti, kesif, tanimlama
from app.agents.dogrulama import cikarim as dogrulama_cikarim
from app.core.config import get_settings
from app.core.llm import (
    YEDEGE_DUSUREN_HATALAR,
    HizSinirHatasi,
    ModelMesgulHatasi,
    SureOlcer,
    llm_hatasini_cevir,
    model_adlarini_dogrula,
)

ZINCIRLER = (
    kesif._cikarim_zinciri,
    tanimlama._cikarim_zinciri,
    firma_karti._cikarim_zinciri,
    eslestirme._gerekce_zinciri,
    eslestirme._firma_gerekce_zinciri,
    dogrulama_cikarim._cikarim_zinciri,
)

ENV = {
    "GOOGLE_API_KEY": "test-anahtari",
    "GEMINI_HIZLI_MODEL": "hizli-ana",
    "GEMINI_HIZLI_YEDEK_MODEL": "hizli-yedek",
    "GEMINI_GUCLU_MODEL": "guclu-ana",
    "GEMINI_GUCLU_YEDEK_MODEL": "guclu-yedek",
    "GEMINI_ZAMAN_ASIMI_SN": "12",
}


@pytest.fixture
def ortam(monkeypatch):
    """.env yerine test değerleri; ayar ve zincir önbellekleri temizlenir."""
    for anahtar, deger in ENV.items():
        monkeypatch.setenv(anahtar, deger)
    get_settings.cache_clear()
    for zincir in ZINCIRLER:
        zincir.cache_clear()
    yield
    get_settings.cache_clear()
    for zincir in ZINCIRLER:
        zincir.cache_clear()


def _model(runnable) -> ChatGoogleGenerativeAI:
    """Zincirin içindeki Gemini modelini bulur (prompt | model | parser olabilir)."""
    bekleyenler = [runnable]
    while bekleyenler:
        adim = bekleyenler.pop()
        if isinstance(adim, ChatGoogleGenerativeAI):
            return adim
        bekleyenler.extend(getattr(adim, "steps", []) or [])
        for alan in ("bound", "first", "last"):
            alt = getattr(adim, alan, None)
            if alt is not None and alt is not adim:
                bekleyenler.append(alt)
    raise AssertionError("Zincirde Gemini modeli yok")


def _ana_ve_yedek(zincir) -> tuple[str, str]:
    assert len(zincir.fallbacks) == 1
    # Model adı sağlayıcıya göre "models/" önekiyle gelebiliyor.
    ana = _model(zincir.runnable).model.removeprefix("models/")
    yedek = _model(zincir.fallbacks[0]).model.removeprefix("models/")
    return ana, yedek


# --- Model adları .env'den, katmana göre -------------------------------------


def test_model_adlari_env_den_okunur(ortam):
    ayarlar = get_settings()
    assert ayarlar.gemini_hizli_model == "hizli-ana"
    assert ayarlar.gemini_guclu_yedek_model == "guclu-yedek"
    assert ayarlar.gemini_zaman_asimi_sn == 12


@pytest.mark.parametrize(
    "zincir", [kesif._cikarim_zinciri, tanimlama._cikarim_zinciri, firma_karti._cikarim_zinciri]
)
def test_cikarim_isleri_hizli_katmanda(ortam, zincir):
    assert _ana_ve_yedek(zincir()) == ("hizli-ana", "hizli-yedek")


@pytest.mark.parametrize(
    "zincir",
    [
        eslestirme._gerekce_zinciri,
        eslestirme._firma_gerekce_zinciri,
        dogrulama_cikarim._cikarim_zinciri,
    ],
)
def test_gerekce_ve_rubrik_guclu_katmanda(ortam, zincir):
    assert _ana_ve_yedek(zincir()) == ("guclu-ana", "guclu-yedek")


def test_zaman_asimi_modele_iletilir(ortam):
    assert _model(kesif._cikarim_zinciri().runnable).timeout == 12


def test_yedek_ayni_yapilandirilmis_semayi_kullanir(ortam):
    """Yedek modelin çıktısı da aynı şemaya dökülmeli, yoksa çıkarım bozulur."""
    zincir = kesif._cikarim_zinciri()
    assert zincir.fallbacks[0].last == zincir.runnable.last


def test_varsayilan_guclu_model_preview_degil(monkeypatch):
    """Demo günü preview modelin hız sınırı ya da kaldırılması sürpriz çıkarmasın."""
    for anahtar in ENV:
        monkeypatch.delenv(anahtar, raising=False)
    varsayilan = type(get_settings()).model_fields["gemini_guclu_model"].default
    assert "preview" not in varsayilan


# --- Yedek zincirin amacı: sağlayıcı arızası -----------------------------------


def test_yedege_dusuren_hatalar_ariza_ve_hiz_siniri(ortam):
    for zincir in ZINCIRLER:
        assert zincir().exceptions_to_handle == YEDEGE_DUSUREN_HATALAR
    assert set(YEDEGE_DUSUREN_HATALAR) == {
        GoogleAPIError,
        GoogleRateLimitError,
        httpx.TimeoutException,
        GoogleModelNotFoundError,
    }


def test_kullanilamayan_model_yedege_duser():
    """Gerçek vaka: gemini-2.5-pro listede görünüp çağrıda 404 dönüyor, tüm
    arka plan eşleştirmesini düşürmüştü. Model adresine özgü; yedek çalışır."""
    assert issubclass(GoogleModelNotFoundError, YEDEGE_DUSUREN_HATALAR)


@pytest.mark.parametrize(
    "hata", [GoogleInvalidRequestError, GoogleAuthenticationError, GooglePermissionDeniedError]
)
def test_diger_4xx_yedegi_bosuna_yormaz(hata):
    """400/401/403 aynı istekle yedekte de başarısız olur; çağrı israf olurdu."""
    assert not issubclass(hata, YEDEGE_DUSUREN_HATALAR)


def test_zaman_asimi_503_e_cevrilir():
    """Eskiden genel 500'e düşüyordu; kullanıcıya 'yoğun' denmeli."""
    hata = httpx.ConnectTimeout("_ssl.c:983: The handshake operation timed out")
    assert isinstance(llm_hatasini_cevir(hata), ModelMesgulHatasi)


def test_hiz_siniri_429_a_cevrilir():
    assert isinstance(llm_hatasini_cevir(Exception("429 RESOURCE_EXHAUSTED")), HizSinirHatasi)


# --- Token kaydı --------------------------------------------------------------


def _sonuc(usage_metadata) -> LLMResult:
    mesaj = AIMessage(content="tamam", usage_metadata=usage_metadata)
    return LLMResult(generations=[[ChatGeneration(message=mesaj)]])


def _calistir(olcer: SureOlcer, sonuc: LLMResult) -> None:
    run_id = uuid.uuid4()
    olcer.on_chat_model_start({}, [[]], run_id=run_id)
    olcer.on_llm_end(sonuc, run_id=run_id)


def test_token_sayilari_log_a_yazilir(caplog):
    olcer = SureOlcer("dogrulama_rubrik", "gemini-2.5-pro")
    kullanim = {
        "input_tokens": 812,
        "output_tokens": 140,
        "total_tokens": 952,
        "output_token_details": {"reasoning": 96},
    }
    with caplog.at_level(logging.INFO, logger="zemin360.llm"):
        _calistir(olcer, _sonuc(kullanim))

    satir = caplog.messages[-1]
    assert "[dogrulama_rubrik] gemini-2.5-pro" in satir
    assert "girdi 812, çıktı 140 (düşünme 96), toplam 952 token" in satir
    assert "deneme 1" in satir


def test_dusunme_yoksa_ayrica_gosterilmez(caplog):
    kullanim = {"input_tokens": 300, "output_tokens": 40, "total_tokens": 340}
    with caplog.at_level(logging.INFO, logger="zemin360.llm"):
        _calistir(SureOlcer("kesif_cikarim", "gemini-3.6-flash"), _sonuc(kullanim))
    assert "girdi 300, çıktı 40, toplam 340 token" in caplog.messages[-1]


def test_kullanim_bilgisi_yoksa_cagri_bozulmaz(caplog):
    with caplog.at_level(logging.INFO, logger="zemin360.llm"):
        _calistir(SureOlcer("eslestirme_gerekce", "gemini-2.5-pro"), _sonuc(None))
    assert "token bilgisi yok" in caplog.messages[-1]


def test_hata_satiri_is_ve_modeli_tasir(caplog):
    olcer = SureOlcer("eslestirme_gerekce", "gemini-2.5-pro")
    run_id = uuid.uuid4()
    with caplog.at_level(logging.WARNING, logger="zemin360.llm"):
        olcer.on_chat_model_start({}, [[]], run_id=run_id)
        olcer.on_llm_error(httpx.ReadTimeout("zaman aşımı"), run_id=run_id)
    satir = caplog.messages[-1]
    assert "[eslestirme_gerekce] gemini-2.5-pro" in satir
    assert "ReadTimeout" in satir


def test_kullanilamayan_model_log_a_yuksek_sesle_yazilir(caplog):
    """Yedek işi kurtarıyor ama .env düzeltilmeli; hangi değişken olduğu söylenmeli."""
    olcer = SureOlcer("eslestirme_gerekce", "gemini-2.5-pro", "GEMINI_GUCLU_MODEL")
    run_id = uuid.uuid4()
    with caplog.at_level(logging.WARNING, logger="zemin360.llm"):
        olcer.on_chat_model_start({}, [[]], run_id=run_id)
        olcer.on_llm_error(GoogleModelNotFoundError("404 NOT_FOUND"), run_id=run_id)
    kayit = caplog.records[-1]
    assert kayit.levelno == logging.ERROR
    assert "MODEL KULLANILAMIYOR" in kayit.getMessage()
    assert "GEMINI_GUCLU_MODEL=gemini-2.5-pro" in kayit.getMessage()


# --- Açılışta model adı kontrolü -------------------------------------------------


def _istemci(isleyici) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(isleyici))


def _liste(*adlar, sonraki=None):
    govde = {"models": [{"name": f"models/{ad}"} for ad in adlar]}
    if sonraki:
        govde["nextPageToken"] = sonraki
    return httpx.Response(200, json=govde)


def _dogrula(istemci):
    import asyncio

    return asyncio.run(model_adlarini_dogrula(istemci))


def test_acilis_kontrolu_eksik_modeli_degiskeniyle_uyarir(ortam, caplog):
    istekler = []

    def isleyici(istek):
        istekler.append(istek)
        return _liste("hizli-ana", "hizli-yedek", "guclu-yedek")  # guclu-ana yok

    with caplog.at_level(logging.WARNING, logger="zemin360.llm"):
        eksikler = _dogrula(_istemci(isleyici))

    assert eksikler == [("GEMINI_GUCLU_MODEL", "guclu-ana")]
    assert "GEMINI_GUCLU_MODEL=guclu-ana" in caplog.messages[-1]
    # Anahtar URL'de değil başlıkta: httpx URL'yi log'a yazıyor.
    assert "test-anahtari" not in str(istekler[0].url)
    assert istekler[0].headers["x-goog-api-key"] == "test-anahtari"


def test_acilis_kontrolu_hepsi_varsa_sessiz(ortam, caplog):
    def isleyici(_istek):
        return _liste("hizli-ana", "hizli-yedek", "guclu-ana", "guclu-yedek", "baska")

    with caplog.at_level(logging.WARNING, logger="zemin360.llm"):
        assert _dogrula(_istemci(isleyici)) == []
    assert not caplog.records


def test_acilis_kontrolu_sayfalari_birlestirir(ortam):
    def isleyici(istek):
        if istek.url.params.get("pageToken") == "2":
            return _liste("guclu-ana", "guclu-yedek")
        return _liste("hizli-ana", "hizli-yedek", sonraki="2")

    assert _dogrula(_istemci(isleyici)) == []


@pytest.mark.parametrize(
    "isleyici",
    [
        lambda _i: (_ for _ in ()).throw(httpx.ConnectError("ağ yok")),
        lambda _i: httpx.Response(500, text="sunucu hatası"),
        lambda _i: httpx.Response(200, text="json değil"),
    ],
    ids=["ag-yok", "5xx", "bozuk-yanit"],
)
def test_acilis_kontrolu_basarisizsa_sessizce_gecer(ortam, caplog, isleyici):
    """Açılışı engellememeli; hata fırlatmaz, uyarı basmaz."""
    with caplog.at_level(logging.WARNING, logger="zemin360.llm"):
        assert _dogrula(_istemci(isleyici)) == []
    assert not caplog.records


def test_acilis_kontrolu_anahtar_yoksa_istek_atmaz(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "")
    get_settings.cache_clear()
    try:

        def isleyici(_istek):
            raise AssertionError("anahtar yokken istek atılmamalı")

        assert _dogrula(_istemci(isleyici)) == []
    finally:
        get_settings.cache_clear()


# --- Hızlı katmanın düşünme seviyesi -----------------------------------------------


def test_dusunme_seviyesi_yalnizca_hizli_katmana_gider(ortam, monkeypatch):
    monkeypatch.setenv("GEMINI_HIZLI_DUSUNME", "low")
    get_settings.cache_clear()
    for zincir in ZINCIRLER:
        zincir.cache_clear()

    hizli = kesif._cikarim_zinciri()
    assert _model(hizli.runnable).thinking_level == "low"
    # Yedek model de aynı seviyede çalışmalı (arıza anında davranış değişmesin)
    assert _model(hizli.fallbacks[0]).thinking_level == "low"
    assert _model(tanimlama._cikarim_zinciri().runnable).thinking_level == "low"

    for guclu in (eslestirme._gerekce_zinciri(), dogrulama_cikarim._cikarim_zinciri()):
        assert _model(guclu.runnable).thinking_level is None


def test_varsayilan_dusunme_seviyesi_minimal(monkeypatch):
    """Ölçümle seçildi: modelin varsayılanı yavaştı ve taslağa uydurma ekledi."""
    monkeypatch.delenv("GEMINI_HIZLI_DUSUNME", raising=False)
    varsayilan = type(get_settings()).model_fields["gemini_hizli_dusunme"].default
    assert varsayilan == "minimal"


def test_dusunme_bossa_modelin_varsayilani_kullanilir(ortam, monkeypatch):
    monkeypatch.setenv("GEMINI_HIZLI_DUSUNME", "")
    get_settings.cache_clear()
    kesif._cikarim_zinciri.cache_clear()
    assert get_settings().gemini_hizli_dusunme == ""
    assert _model(kesif._cikarim_zinciri().runnable).thinking_level is None


def test_dusunme_seviyesi_buyuk_kucuk_harf_ve_bosluk_toleransli(ortam, monkeypatch):
    monkeypatch.setenv("GEMINI_HIZLI_DUSUNME", " Minimal ")
    get_settings.cache_clear()
    assert get_settings().gemini_hizli_dusunme == "minimal"


def test_gecersiz_dusunme_seviyesi_acilista_durdurur(ortam, monkeypatch):
    """Yanlış yazılmış seviye sessizce yok sayılmamalı."""
    from pydantic import ValidationError

    monkeypatch.setenv("GEMINI_HIZLI_DUSUNME", "dusuk")
    get_settings.cache_clear()
    with pytest.raises(ValidationError, match="GEMINI_HIZLI_DUSUNME"):
        get_settings()
