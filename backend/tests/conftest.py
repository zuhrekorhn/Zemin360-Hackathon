import os

import pytest

# app.main import sırasında ayarları okuyor (CORS için). Testler veritabanına
# bağlanmıyor, ama DATABASE_URL tanımlı olmalı — gerçek .env yoksa da çalışsın.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres@localhost:5432/zemin360")
# Testler kendi imza anahtarını kullanır; gerçek .env'deki anahtara bağlı değil.
os.environ.setdefault("JWT_GIZLI_ANAHTAR", "test-icin-yeterince-uzun-bir-gizli-anahtar-0123456789")


@pytest.fixture(autouse=True)
def plan_arka_plan_isi_yok(monkeypatch):
    """Kabul ucu yanıttan sonra Takip'in plan önerisini başlatıyor (gerçek oturum,
    gerçek LLM). Testlerde çalışmasın; o işi sınayan test kendisi çağırır."""
    from app.api import takip

    cagrilar: list = []

    async def kaydet(isbirligi_id):
        cagrilar.append(isbirligi_id)

    monkeypatch.setattr(takip, "plani_arka_planda_oner", kaydet)
    return cagrilar


@pytest.fixture(autouse=True)
def ozet_arka_plan_isi_yok(monkeypatch):
    """Plan onayı ve adım tamamlanması yanıttan sonra durum özetini yazdırıyor
    (gerçek oturum, gerçek LLM). Testlerde çalışmasın; kayıt tutulur."""
    from app.api import takip

    cagrilar: list = []

    async def kaydet(isbirligi_id):
        cagrilar.append(isbirligi_id)

    monkeypatch.setattr(takip, "ozeti_arka_planda_yaz", kaydet)
    return cagrilar


@pytest.fixture(autouse=True)
def canlilik_llm_yok(monkeypatch):
    """Canlılık taraması hatırlatma metnini LLM'e yazdırıyor; testlerde şablon
    kullanılsın (kişisel metin None → şablon). Kişiselleştirmeyi sınayan test
    zinciri kendisi değiştirir."""
    from app.agents import canlilik

    async def yok(_baglam):
        return None

    monkeypatch.setattr(canlilik, "kisisel_metin", yok)


@pytest.fixture(autouse=True)
def kart_hazirlama_arka_plani_yok(monkeypatch):
    """Kart onayı ve düzenlemesi yanıttan sonra kartı hazırlıyor (gerçek oturum,
    embedding, LLM rubriği, pipeline). Testlerde çalışmasın; çağrılar kaydedilir,
    o işi sınayan test çekirdeği (`karti_hazirla_oturumla`) doğrudan çağırır."""
    from app.servisler import kart_hazirlama

    cagrilar: list = []

    async def kaydet(kart_id, versiyon, embedding_yenile=False):
        cagrilar.append((kart_id, versiyon, embedding_yenile))

    monkeypatch.setattr(kart_hazirlama, "karti_hazirla", kaydet)
    return cagrilar


@pytest.fixture(autouse=True)
def firma_karti_hazirlama_arka_plani_yok(monkeypatch):
    """Firma kartı onayı ve düzenlemesi yanıttan sonra kartı hazırlıyor (gerçek
    oturum, embedding). Testlerde çalışmasın; çağrılar kaydedilir, o işi sınayan
    test çekirdeği (`firma_kartini_hazirla_oturumla`) doğrudan çağırır."""
    from app.servisler import firma_karti

    cagrilar: list = []

    async def kaydet(kart_id, versiyon):
        cagrilar.append((kart_id, versiyon))

    monkeypatch.setattr(firma_karti, "firma_kartini_hazirla", kaydet)
    return cagrilar
