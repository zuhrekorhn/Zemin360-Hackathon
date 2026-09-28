"""Eşleştirme pipeline'ının eşzamanlı çalışmaya dayanıklılığı.

Gerçek vaka: ihtiyaç kartı onaylanınca arka planda eşleştirme başlıyor; kurum
o sırada öneriler sayfasını açınca GET /oneriler ikinci bir pipeline
başlatıyordu. Sonuç mükerrer öneri satırları ve aday başına iki LLM çağrısı.
"""

import asyncio
import uuid
from types import SimpleNamespace

from sqlalchemy.dialects import postgresql

from app.agents.eslestirme import eslesme_ekle_ifadesi, kilit_anahtari
from app.models.eslesme import Eslesme
from app.servisler import eslestirme as eslestirme_servisi


def test_ayni_cift_icin_tek_eslesme_kisiti_var():
    kisitlar = {
        tuple(sorted(c.name for c in kisit.columns))
        for kisit in Eslesme.__table__.constraints
        if kisit.__class__.__name__ == "UniqueConstraint"
    }
    assert ("ihtiyac_karti_id", "yetenek_karti_id") in kisitlar


def test_ekleme_cakismada_hata_vermez():
    """Kilit atlansa bile UNIQUE ihlali 500'e dönüşmemeli."""
    sql = str(
        eslesme_ekle_ifadesi(
            ihtiyac_karti_id=uuid.uuid4(), yetenek_karti_id=uuid.uuid4(), skor=0.7
        ).compile(dialect=postgresql.dialect())
    )
    assert "ON CONFLICT (ihtiyac_karti_id, yetenek_karti_id) DO NOTHING" in sql


def test_kilit_anahtari_karta_bagli_ve_kararli():
    kart = uuid.uuid4()
    assert kilit_anahtari(kart) == kilit_anahtari(kart)
    assert kilit_anahtari(kart) != kilit_anahtari(uuid.uuid4())
    # pg_advisory_xact_lock işaretli 64 bit istiyor
    assert -(2**63) <= kilit_anahtari(kart) < 2**63


class KayitTutanOturum:
    """Pipeline'ın veritabanına ne sırayla gittiğini kaydeder."""

    def __init__(self):
        self.ifadeler: list[str] = []

    async def execute(self, ifade, *args, **kwargs):
        self.ifadeler.append(str(ifade))

    async def scalars(self, ifade, *args, **kwargs):
        self.ifadeler.append(str(ifade))
        return []

    async def commit(self):
        pass


def test_kilit_eslesmeler_okunmadan_once_alinir(monkeypatch):
    """İkinci pipeline, birincinin yazdıklarını görmeden okumaya başlamamalı."""
    ihtiyac = SimpleNamespace(id=uuid.uuid4(), kurum_id=uuid.uuid4(), embedding=[0.1], durum="acik")
    okunanlar: list[str] = []

    async def adaylar(oturum, ihtiyac_karti):
        okunanlar.append("adaylar")
        return []

    monkeypatch.setattr(eslestirme_servisi, "adaylari_getir", adaylar)

    oturum = KayitTutanOturum()
    asyncio.run(eslestirme_servisi.pipeline_calistir(oturum, ihtiyac))

    assert "pg_advisory_xact_lock" in oturum.ifadeler[0]
    # Eşleşme okumaları kilitten sonra
    assert all("eslesme" in ifade for ifade in oturum.ifadeler[1:])
    assert okunanlar == ["adaylar"]
