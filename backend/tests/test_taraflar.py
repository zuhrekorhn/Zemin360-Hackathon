"""Eşleşmenin tarafları (docs/plans/firma-akisi.md § 3, karar 12).

Durum makinesindeki roller hesabın rolü değil, eşleşmedeki taraf. Bu adımda
davranış değişmiyor: aday tarafı gencin, ilan tarafı ihtiyacın firmasının.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace

from app.agents.eslesme_durumu import (
    OLAY_GENC_ILGI,
    OLAY_ILGILENIYORUM,
    OLAYIN_ROLU,
    gecis,
)
from app.agents.eslestirme import DURUM_GENC_ILGILENDI, DURUM_ONERILDI
from app.models.hesap import ROL_GENC, ROL_GIRVAK, ROL_KURUM
from app.servisler.sahiplik import (
    TARAF_ADAY,
    TARAF_ILAN,
    eslesmedeki_taraf,
    karsi_taraf,
    taraf_adi,
    taraf_hesabi,
)


def _dunya():
    genc_hesap, kurum_hesap = uuid.uuid4(), uuid.uuid4()
    kullanici = SimpleNamespace(id=uuid.uuid4(), ad="Ayşe", hesap_id=genc_hesap)
    kurum = SimpleNamespace(id=uuid.uuid4(), ad="Koop Bir", hesap_id=kurum_hesap)
    eslesme = SimpleNamespace(
        firma_karti=None,
        yetenek_karti=SimpleNamespace(kullanici_id=kullanici.id, kullanici=kullanici),
        ihtiyac_karti=SimpleNamespace(kurum_id=kurum.id, kurum=kurum),
    )
    genc = SimpleNamespace(rol=ROL_GENC, kullanici=kullanici, kurum=None)
    firma = SimpleNamespace(rol=ROL_KURUM, kullanici=None, kurum=kurum)
    return eslesme, genc, firma


def test_taraf_degerleri_eski_rol_adlariyla_ayni():
    # `eslesme.baslatan` ve gecis() tablosu bu değerleri saklıyor; değişirse
    # eski kayıtlar yanlış okunur.
    assert (TARAF_ADAY, TARAF_ILAN) == ("genc", "kurum")
    assert set(OLAYIN_ROLU.values()) <= {TARAF_ADAY, TARAF_ILAN, "sistem"}


def test_eslesmedeki_taraf():
    eslesme, genc, firma = _dunya()
    assert eslesmedeki_taraf(genc, eslesme) == TARAF_ADAY
    assert eslesmedeki_taraf(firma, eslesme) == TARAF_ILAN


def test_taraf_olmayan_hesap_none():
    eslesme, _, _ = _dunya()
    baska_genc = SimpleNamespace(
        rol=ROL_GENC, kullanici=SimpleNamespace(id=uuid.uuid4()), kurum=None
    )
    baska_firma = SimpleNamespace(
        rol=ROL_KURUM, kullanici=None, kurum=SimpleNamespace(id=uuid.uuid4())
    )
    girvak = SimpleNamespace(rol=ROL_GIRVAK, kullanici=None, kurum=None)
    for hesap in (baska_genc, baska_firma, girvak):
        assert eslesmedeki_taraf(hesap, eslesme) is None


def test_karsi_taraf():
    assert karsi_taraf(TARAF_ADAY) == TARAF_ILAN
    assert karsi_taraf(TARAF_ILAN) == TARAF_ADAY


def test_taraf_hesabi_ve_adi():
    eslesme, _, _ = _dunya()
    assert taraf_hesabi(eslesme, TARAF_ADAY) == eslesme.yetenek_karti.kullanici.hesap_id
    assert taraf_hesabi(eslesme, TARAF_ILAN) == eslesme.ihtiyac_karti.kurum.hesap_id
    assert taraf_adi(eslesme, TARAF_ADAY) == "Ayşe"
    assert taraf_adi(eslesme, TARAF_ILAN) == "Koop Bir"


def test_gecis_tarafla_calisir():
    assert gecis(DURUM_ONERILDI, OLAY_GENC_ILGI, TARAF_ADAY).durum == DURUM_GENC_ILGILENDI
    assert gecis(DURUM_GENC_ILGILENDI, OLAY_ILGILENIYORUM, TARAF_ILAN).degisti
