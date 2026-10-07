"""Dışarıya açılan kart görünümünün taşıdığı (ve taşımadığı) alanlar.

Frontend bu üç şeye dayanıyor: kurum kimliği (öneri uç noktası onu istiyor),
çıktı başına güven skoru (rubriği ayrı istek atmadan çizebilmek için) ve
skor eşiği (boş liste mesajı eşiği kendi içine yazmasın diye).
"""

import uuid

import pytest
from pydantic import ValidationError

from app.schemas.dogrulama import GuvenSkoruYaniti
from app.schemas.eslestirme import OnerilerYaniti
from app.schemas.kesif import SomutCiktiYaniti, YetenekKartiYaniti
from app.schemas.tanimlama import IhtiyacKartiYaniti, KurumYaniti


def _cikti(**degisiklik) -> SomutCiktiYaniti:
    return SomutCiktiYaniti(
        id=uuid.uuid4(),
        baslik="Kütüphane takip sistemi",
        aciklama=None,
        kanitlar=[],
        **degisiklik,
    )


def test_kanitsiz_cikti_skorsuz_gecerli():
    """Kanıt eklenmemiş çıktı "doğrulanmamış"tır; eksik alan değil."""
    assert _cikti().guven_skoru is None


def test_cikti_rubrigi_tasiyabilir():
    cikti = _cikti(
        guven_skoru=GuvenSkoruYaniti(
            kanit_orijinalligi=3,
            sonuc_olculebilirligi=2,
            rol_netligi=3,
            ucuncu_taraf_onayi=1,
            gerekce_metni="Link açıldı, sayı doğrulandı.",
        )
    )
    assert cikti.guven_skoru is not None
    assert cikti.guven_skoru.ucuncu_taraf_onayi == 1


def test_kart_gorunumu_eposta_tasimaz_ad_tasir():
    """agent-specs.md § 1.5 — e-posta kabulle açılır, ayrı `iletisim` alanında.

    Gencin adı iletişim bilgisi sayılmıyor, baştan görünür
    (docs/kimlik-ve-dongu.md § 5).
    """
    alanlar = set(YetenekKartiYaniti.model_fields) | set(SomutCiktiYaniti.model_fields)
    assert not {"email", "iletisim_email", "telefon", "iletisim"} & alanlar
    assert "genc_adi" in alanlar


def test_kurum_yaniti_kimlik_tasir_email_tasimaz():
    kurum = KurumYaniti(id=uuid.uuid4(), ad="Örnek Kooperatif", sektor=None, sehir=None)
    assert kurum.id is not None
    assert "iletisim_email" not in KurumYaniti.model_fields
    assert "iletisim_email" not in IhtiyacKartiYaniti.model_fields


def test_kurum_kimligi_zorunlu():
    """Öneri uç noktası kurum kimliğiyle çalışıyor; sessizce boş kalmamalı."""
    with pytest.raises(ValidationError):
        KurumYaniti(ad="Örnek Kooperatif", sektor=None, sehir=None)


def test_oneriler_yaniti_skor_esigi_tasimaz():
    """Skor eşiği kalktı: giriş kararı benzerlik tabanında, yanıtta eşik alanı yok."""
    yanit = OnerilerYaniti(ihtiyac_karti_id=uuid.uuid4(), oneriler=[], az_sonuc_uyarisi=True)
    assert "skor_esigi" not in yanit.model_dump()
