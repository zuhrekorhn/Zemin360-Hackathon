"""Kart onayı tekrarlanabilir; embedding hatası kartı kaybettirmez.

Gerçek vaka: kart kaydedildikten sonra Voyage'a ulaşılamayınca kullanıcı 500
görüyordu. Taslak hâlâ "hazır" olduğu için "Kartı onayla"ya yeniden basınca
ikinci bir kart açılıyor, ilki de embedding'siz kaldığı için eşleştirmeye hiç
girmiyordu.

Veritabanı ve dış servis olmadan: oturum ve grafik taklit ediliyor, kartı
bulan/okuyan yardımcılar monkeypatch'le değiştiriliyor.
"""

import uuid
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.api import ihtiyac_kartlari as ihtiyac_api
from app.api import kesif as kesif_api
from app.api import tanimlama as tanimlama_api
from app.api import yetenek_kartlari as yetenek_api
from app.api.kimlik import mevcut_hesap
from app.core.embeddings import EmbeddingHatasi
from app.db.base import EMBEDDING_DIM
from app.db.session import get_session
from app.main import app
from app.models.ihtiyac_karti import IhtiyacKarti
from app.models.yetenek_karti import YetenekKarti
from app.schemas.kesif import YetenekKartiYaniti
from app.schemas.tanimlama import IhtiyacKartiYaniti, KurumYaniti
from tests.sahte_hesap import sahte_hesap, sohbet_degerleri

# Giriş yapmış genç ve kurum: sohbetleri onlar açmış, kartlar onların.
GENC = sahte_hesap("genc")
KURUM = sahte_hesap("kurum")

VEKTOR = [0.0] * EMBEDDING_DIM


class SahteOturum:
    def __init__(self, *, commit_hatasi: Exception | None = None, bulunan=None):
        self.eklenenler: list = []
        self.commit_sayisi = 0
        self.rollback_sayisi = 0
        self._commit_hatasi = commit_hatasi
        self._bulunan = bulunan

    def add(self, nesne):
        if getattr(nesne, "id", None) is None:
            nesne.id = uuid.uuid4()
        self.eklenenler.append(nesne)

    async def flush(self):
        pass

    async def commit(self):
        self.commit_sayisi += 1
        if self._commit_hatasi is not None:
            hata, self._commit_hatasi = self._commit_hatasi, None
            raise hata

    async def rollback(self):
        self.rollback_sayisi += 1

    async def scalar(self, *_args, **_kwargs):
        return self._bulunan


class SahteGrafik:
    def __init__(self, taslak: dict, sahip=GENC):
        self.taslak = taslak
        self.sahip = sahip

    async def aget_state(self, _config):
        return SimpleNamespace(
            values=sohbet_degerleri(self.sahip, taslak_hazir=True, taslak=self.taslak)
        )


def yetenek_karti(**degisiklik) -> YetenekKarti:
    kart = YetenekKarti(
        id=uuid.uuid4(),
        kullanici_id=GENC.kullanici.id,
        rol_alani="backend geliştirici",
        deneyim_seviyesi="orta",
        sektor_ilgi_alani=["eğitim"],
        araclar_teknolojiler=["Python"],
        kanit_bekleyen=False,
        versiyon=1,
        somut_ciktilar=[],
    )
    for alan, deger in degisiklik.items():
        setattr(kart, alan, deger)
    return kart


def yetenek_yaniti(kart: YetenekKarti) -> YetenekKartiYaniti:
    return YetenekKartiYaniti(
        id=kart.id,
        genc_adi="Elif",
        rol_alani=kart.rol_alani,
        deneyim_seviyesi=kart.deneyim_seviyesi,
        sektor_ilgi_alani=kart.sektor_ilgi_alani or [],
        araclar_teknolojiler=kart.araclar_teknolojiler or [],
        kanit_bekleyen=bool(kart.kanit_bekleyen),
        versiyon=kart.versiyon or 1,
        embedding_var=kart.embedding is not None,
        somut_ciktilar=[],
    )


@pytest.fixture
def kesif(monkeypatch):
    """Keşif onayı için hazır ortam; testler oturumu ve bulunan kartı seçer."""
    durum = SimpleNamespace(oturum=SahteOturum(), bulunanlar=[], kartlar={})

    async def oturumun_karti(_oturum, _oturum_id):
        return durum.bulunanlar.pop(0) if durum.bulunanlar else None

    async def kart_yaniti(oturum, kart_id):
        adaylar = [*oturum.eklenenler, *durum.kartlar.values()]
        return yetenek_yaniti(next(k for k in adaylar if k.id == kart_id))

    monkeypatch.setattr(kesif_api, "_oturumun_karti", oturumun_karti)
    monkeypatch.setattr(kesif_api, "kart_yaniti", kart_yaniti)
    app.state.kesif_grafigi = SahteGrafik(
        {
            "rol_alani": "backend geliştirici",
            "deneyim_seviyesi": "orta",
            "sektor_ilgi_alani": ["eğitim"],
            "araclar_teknolojiler": ["Python"],
            "somut_ciktilar": [],
        }
    )
    app.dependency_overrides[get_session] = lambda: durum.oturum
    app.dependency_overrides[mevcut_hesap] = lambda: GENC
    yield durum
    app.dependency_overrides.clear()
    del app.state.kesif_grafigi


def onayla() -> object:
    return TestClient(app).post(
        "/kesif/kart/onayla",
        json={
            "oturum_id": str(uuid.uuid4()),
            "profil": {"sehir": "İstanbul"},
        },
    )


def embedding_basarili(monkeypatch):
    async def uret(_metin, girdi_turu="document"):
        return VEKTOR

    monkeypatch.setattr(yetenek_api, "embedding_uret", uret)
    monkeypatch.setattr(ihtiyac_api, "embedding_uret", uret)


def embedding_basarisiz(monkeypatch):
    async def uret(_metin, girdi_turu="document"):
        raise EmbeddingHatasi("Voyage 503")

    monkeypatch.setattr(yetenek_api, "embedding_uret", uret)
    monkeypatch.setattr(ihtiyac_api, "embedding_uret", uret)


def test_ayni_oturum_ikinci_kez_onaylaninca_yeni_kart_acilmaz(kesif, monkeypatch):
    embedding_basarili(monkeypatch)
    mevcut = yetenek_karti(embedding=VEKTOR)
    kesif.bulunanlar.append(mevcut)
    kesif.kartlar[mevcut.id] = mevcut

    yanit = onayla()

    assert yanit.status_code == 200
    assert yanit.json()["id"] == str(mevcut.id)
    assert kesif.oturum.eklenenler == []


def test_embedding_hatasinda_kart_yine_doner(kesif, monkeypatch):
    """Kart kayıtlı; 500 yerine embedding'siz olduğu açıkça söylenir."""
    embedding_basarisiz(monkeypatch)

    yanit = onayla()

    assert yanit.status_code == 201
    assert yanit.json()["embedding_var"] is False
    assert len(kesif.oturum.eklenenler) == 1


def test_eszamanli_ikinci_onay_mevcut_karti_doner(kesif, monkeypatch):
    """İki istek aynı anda gelirse UNIQUE oturum_id ikincisini durdurur."""
    embedding_basarili(monkeypatch)
    diger_istegin_karti = yetenek_karti(embedding=VEKTOR)
    kesif.kartlar[diger_istegin_karti.id] = diger_istegin_karti
    # İlk arama boş (henüz yazılmamış), commit çakışır, ikinci arama bulur.
    kesif.bulunanlar.extend([None, diger_istegin_karti])
    kesif.oturum = SahteOturum(commit_hatasi=IntegrityError("INSERT", {}, Exception("uq")))
    app.dependency_overrides[get_session] = lambda: kesif.oturum

    yanit = onayla()

    assert yanit.status_code == 200
    assert yanit.json()["id"] == str(diger_istegin_karti.id)
    assert kesif.oturum.rollback_sayisi == 1


def test_mevcut_kartin_eksik_embeddingi_yeniden_denenir(kesif, monkeypatch):
    embedding_basarili(monkeypatch)
    mevcut = yetenek_karti(embedding=None)
    kesif.bulunanlar.append(mevcut)
    kesif.kartlar[mevcut.id] = mevcut

    yanit = onayla()

    assert yanit.status_code == 200
    assert yanit.json()["embedding_var"] is True


def test_embedding_yeniden_hesaplama_ucu(monkeypatch):
    embedding_basarili(monkeypatch)
    kart = yetenek_karti(embedding=None)
    oturum = SahteOturum(bulunan=kart)

    async def kart_yaniti(_oturum, _kart_id):
        return yetenek_yaniti(kart)

    monkeypatch.setattr(yetenek_api, "kart_yaniti", kart_yaniti)
    app.dependency_overrides[get_session] = lambda: oturum
    app.dependency_overrides[mevcut_hesap] = lambda: GENC
    try:
        yanit = TestClient(app).post(f"/yetenek-kartlari/{kart.id}/embedding")
    finally:
        app.dependency_overrides.clear()

    assert yanit.status_code == 200
    assert yanit.json()["embedding_var"] is True


def test_embedding_ucu_servis_yoksa_503_ve_net_mesaj(monkeypatch):
    embedding_basarisiz(monkeypatch)
    kart = yetenek_karti(embedding=None)
    app.dependency_overrides[get_session] = lambda: SahteOturum(bulunan=kart)
    app.dependency_overrides[mevcut_hesap] = lambda: GENC
    try:
        yanit = TestClient(app).post(f"/yetenek-kartlari/{kart.id}/embedding")
    finally:
        app.dependency_overrides.clear()

    assert yanit.status_code == 503
    assert "Kart kaydedildi" in yanit.json()["detail"]


# --- Tanımlama: embedding yoksa eşleştirme başlamaz -------------------------


@pytest.fixture
def tanimlama(monkeypatch):
    durum = SimpleNamespace(oturum=SahteOturum(), eslestirilenler=[])
    kurum_id = KURUM.kurum.id

    async def oturumun_karti(_oturum, _oturum_id):
        return None

    async def kart_yaniti(oturum, kart_id):
        kart: IhtiyacKarti = next(k for k in oturum.eklenenler if k.id == kart_id)
        return IhtiyacKartiYaniti(
            id=kart.id,
            problem_tanimi=kart.problem_tanimi,
            basari_kriteri=kart.basari_kriteri,
            kisitlar=None,
            sehir_tercihi=None,
            calisma_modeli=None,
            musaitlik_tercihi=None,
            embedding_var=kart.embedding is not None,
            kurum=KurumYaniti(id=kurum_id, ad="Kooperatif", sektor=None, sehir=None),
        )

    async def eslestir(kimlik):
        durum.eslestirilenler.append(kimlik)

    monkeypatch.setattr(tanimlama_api, "_oturumun_karti", oturumun_karti)
    monkeypatch.setattr(tanimlama_api, "kart_yaniti", kart_yaniti)
    monkeypatch.setattr(tanimlama_api, "eslestirmeyi_arka_planda_calistir", eslestir)
    app.state.tanimlama_grafigi = SahteGrafik(
        {"problem_tanimi": "Destek biletleri elle ayrılıyor", "basari_kriteri": "%50 otomatik"},
        sahip=KURUM,
    )
    app.dependency_overrides[get_session] = lambda: durum.oturum
    app.dependency_overrides[mevcut_hesap] = lambda: KURUM
    yield durum
    app.dependency_overrides.clear()
    del app.state.tanimlama_grafigi


def ihtiyac_onayla():
    return TestClient(app).post(
        "/tanimlama/kart/onayla",
        json={
            "oturum_id": str(uuid.uuid4()),
            "kurum_profili": {},
        },
    )


def test_ihtiyac_embeddingi_yoksa_eslestirme_baslamaz(tanimlama, monkeypatch):
    """Embedding'siz ihtiyaç kartı aday bulamaz; boş bir pipeline başlatılmamalı."""
    embedding_basarisiz(monkeypatch)

    yanit = ihtiyac_onayla()

    assert yanit.status_code == 201
    assert yanit.json()["embedding_var"] is False
    assert tanimlama.eslestirilenler == []


def test_ihtiyac_embeddingi_varsa_eslestirme_baslar(tanimlama, monkeypatch):
    embedding_basarili(monkeypatch)

    yanit = ihtiyac_onayla()

    assert yanit.status_code == 201
    assert len(tanimlama.eslestirilenler) == 1


# --- Tüm çıktılar silinirse "potansiyel" ------------------------------------
# Taslak ekranında kullanıcı çıktıların hepsini "Çıkar" diyebiliyor. Arayüz o
# anda "potansiyel olarak kaydedilecek" diyordu ama kart sohbetteki eski
# seviyeyle ("orta") kaydediliyordu (agent-specs.md § 1.4).


def duzeltilmis_onayla(somut_ciktilar: list[dict]):
    return TestClient(app).post(
        "/kesif/kart/onayla",
        json={
            "oturum_id": str(uuid.uuid4()),
            "profil": {"sehir": "İstanbul"},
            "duzeltilmis_taslak": {
                "rol_alani": "backend geliştirici",
                "deneyim_seviyesi": "orta",
                "sektor_ilgi_alani": ["eğitim"],
                "araclar_teknolojiler": ["Python"],
                "somut_ciktilar": somut_ciktilar,
            },
        },
    )


def test_tum_ciktilar_silinirse_kart_potansiyel_kaydedilir(kesif, monkeypatch):
    embedding_basarili(monkeypatch)

    yanit = duzeltilmis_onayla([])

    assert yanit.status_code == 201
    assert kesif.oturum.eklenenler[0].deneyim_seviyesi == "potansiyel"
    assert yanit.json()["deneyim_seviyesi"] == "potansiyel"


def test_ciktisi_kalan_kartin_seviyesi_korunur(kesif, monkeypatch):
    embedding_basarili(monkeypatch)

    duzeltilmis_onayla([{"baslik": "Kütüphane sistemi"}])

    assert kesif.oturum.eklenenler[0].deneyim_seviyesi == "orta"
