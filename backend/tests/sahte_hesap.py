"""Veritabanısız API testleri için giriş yapmış sahte hesap.

Sahipliğin kendisi tests/test_sahiplik.py'de gerçek veritabanında sınanıyor;
buradaki yardımcı, başka bir şeyi (onay tekrarı, müsaitlik doğrulaması…)
sınayan testlerin token üretmeden "giriş yapmış" olmasını sağlar.

    GENC = sahte_hesap("genc")
    with giris_yapmis(GENC):
        TestClient(app).post(...)
"""

from __future__ import annotations

import contextlib
import uuid
from collections.abc import Iterator
from types import SimpleNamespace

from app.api.kimlik import mevcut_hesap
from app.main import app


def sahte_hesap(rol: str) -> SimpleNamespace:
    """Profiliyle birlikte bir hesap: genç için `kullanici`, kurum için `kurum`."""
    return SimpleNamespace(
        id=uuid.uuid4(),
        rol=rol,
        email=f"{rol}@ornek.com",
        kullanici=(
            SimpleNamespace(
                id=uuid.uuid4(),
                ad="Elif",
                email=f"{rol}@ornek.com",
                sehir="İstanbul",
                calisma_modelleri=[],
                musaitlikler=[],
            )
            if rol == "genc"
            else None
        ),
        kurum=(
            SimpleNamespace(id=uuid.uuid4(), ad="Kooperatif", sektor=None, sehir=None)
            if rol == "kurum"
            else None
        ),
    )


@contextlib.contextmanager
def giris_yapmis(hesap: SimpleNamespace) -> Iterator[None]:
    """`mevcut_hesap`'ı bu hesapla değiştirir; `rol_gerekli` de onu kullanır."""
    app.dependency_overrides[mevcut_hesap] = lambda: hesap
    try:
        yield
    finally:
        app.dependency_overrides.pop(mevcut_hesap, None)


def sohbet_degerleri(hesap: SimpleNamespace, **degerler) -> dict:
    """Checkpoint durumu: sohbeti bu hesap açmış."""
    return {"sahip_hesap_id": str(hesap.id), **degerler}
