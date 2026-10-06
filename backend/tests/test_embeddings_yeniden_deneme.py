"""Voyage çağrısının hız sınırı (429) davranışı: yalnızca 429 yeniden denenir (1, 2, 4 sn).

Gerçek ağ ve gerçek bekleme yok: httpx istemcisi ve `_bekle` sahtesi.
"""

import asyncio
from types import SimpleNamespace

import pytest

from app.core import embeddings
from app.db.base import EMBEDDING_DIM


class SahteYanit:
    def __init__(self, durum: int, metin: str = ""):
        self.status_code = durum
        self.text = metin

    def json(self):
        return {"data": [{"index": 0, "embedding": [0.1] * EMBEDDING_DIM}]}


@pytest.fixture
def voyage(monkeypatch):
    """`ayarla(*durumlar)`: sıradaki yanıt durumları; dönen nesne çağrı ve bekleme kaydını tutar."""
    kayit = SimpleNamespace(cagri=0, beklemeler=[])

    def ayarla(*durumlar: int):
        kuyruk = list(durumlar)

        class SahteIstemci:
            def __init__(self, **_):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_):
                return False

            async def post(self, *_, **__):
                kayit.cagri += 1
                return SahteYanit(kuyruk.pop(0), "hata gövdesi")

        async def sahte_bekle(saniye):
            kayit.beklemeler.append(saniye)

        monkeypatch.setattr(embeddings.httpx, "AsyncClient", SahteIstemci)
        monkeypatch.setattr(embeddings, "_bekle", sahte_bekle)
        monkeypatch.setattr(
            embeddings,
            "get_settings",
            lambda: SimpleNamespace(voyage_api_key="x", voyage_model="m"),
        )
        return kayit

    return ayarla


def test_429_sonrasi_basarili_olursa_vektor_doner(voyage):
    kayit = voyage(429, 429, 200)
    vektor = asyncio.run(embeddings.embedding_uret("metin"))
    assert len(vektor) == EMBEDDING_DIM
    assert kayit.cagri == 3
    assert kayit.beklemeler == [1.0, 2.0]


def test_429_surekliyse_uc_yeniden_denemeden_sonra_embedding_hatasi(voyage):
    kayit = voyage(429, 429, 429, 429)
    with pytest.raises(embeddings.EmbeddingHatasi, match="Voyage 429"):
        asyncio.run(embeddings.embedding_uret("metin"))
    # İlk çağrı + en fazla 3 yeniden deneme; beklemeler 1, 2, 4 sn.
    assert kayit.cagri == 4
    assert kayit.beklemeler == [1.0, 2.0, 4.0]


@pytest.mark.parametrize("durum", [401, 400, 500])
def test_429_disindaki_hata_yeniden_denenmez(voyage, durum):
    kayit = voyage(durum)
    with pytest.raises(embeddings.EmbeddingHatasi, match=f"Voyage {durum}"):
        asyncio.run(embeddings.embedding_uret("metin"))
    assert kayit.cagri == 1
    assert kayit.beklemeler == []
