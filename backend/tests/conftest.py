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
