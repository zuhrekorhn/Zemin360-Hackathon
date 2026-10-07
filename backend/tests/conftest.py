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
def kart_embedding_agi_yok(monkeypatch):
    """Kart embedding'i tek noktadan Voyage'a gider (app/servisler/embedding.py).
    Testlerde ağa çıkılmasın: Voyage ulaşılamaz sayılır, kart kaybolmaz. Başarılı
    embedding'i sınayan test kendi sahtesini aynı yere yazar (bunu ezer)."""
    from app.core.embeddings import EmbeddingHatasi
    from app.servisler import embedding

    async def ulasilamaz(_metin, girdi_turu="document"):
        raise EmbeddingHatasi("Testte Voyage'a gidilmez")

    monkeypatch.setattr(embedding, "embedding_uret", ulasilamaz)


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
def kalem_yeniden_puanlama_arka_plani_yok(monkeypatch):
    """Referansın Sonuç / Rol desteği değişince kalem arka planda yeniden puanlanır
    (gerçek oturum, LLM). Testlerde çalışmasın; çağrılar (kart, kalem, sürüm) kaydedilir."""
    from app.servisler import kart_hazirlama

    cagrilar: list = []

    async def kaydet(kart_id, cikti_id, versiyon):
        cagrilar.append((kart_id, cikti_id, versiyon))

    monkeypatch.setattr(kart_hazirlama, "kalemi_yeniden_puanla", kaydet)
    return cagrilar


@pytest.fixture(autouse=True)
def kalemleri_yeniden_okuma_arka_plani_yok(monkeypatch):
    """Bağlı hesap değişince linkli kalemler arka planda yeniden okunur (gerçek
    oturum, ağ, LLM). Testlerde çalışmasın; çağrılan kart kimlikleri kaydedilir."""
    from app.servisler import kart_hazirlama

    cagrilar: list = []

    async def kaydet(kart_id):
        cagrilar.append(kart_id)

    monkeypatch.setattr(kart_hazirlama, "kalemleri_yeniden_oku", kaydet)
    return cagrilar


@pytest.fixture(autouse=True)
def oauth_saglayicilari(monkeypatch):
    """Testler `.env`'deki OAuth ayarına bağlı kalmaz: varsayılan hiçbir sağlayıcı
    açık değil. Akışı sınayan test bu sözlüğe sahte sağlayıcı ekler."""
    from app.core.dis_servisler import kurulum

    saglayicilar: dict = {}
    monkeypatch.setattr(kurulum, "oauth_saglayicilari", lambda: saglayicilar)
    return saglayicilar


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


@pytest.fixture(autouse=True)
def firma_yeniden_eslestirme_arka_plani_yok(monkeypatch):
    """Firma profilinde şehir/tür değişince kart yanıttan sonra yeniden eşleşir (gerçek
    oturum, pipeline, LLM). Testlerde çalışmasın; çağrılan kart kimlikleri kaydedilir."""
    from app.servisler import firma_karti

    cagrilar: list = []

    async def kaydet(kart_id):
        cagrilar.append(kart_id)

    monkeypatch.setattr(firma_karti, "firma_kartini_yeniden_eslestir", kaydet)
    return cagrilar


@pytest.fixture(autouse=True)
def genc_uygunluk_yargisi_sahte(monkeypatch):
    """Genç ilanının öneri gerekçesini artık yargı çağrısı yazıyor (§ 8; gerçek LLM).
    Testlerde model yok: gerekçe testin kendi `gerekce_uret` sahtesinden gelir (çağrı
    anında aranır, test onu değiştirebilir), karar "uygun"; gerekçe alınamazsa "bilinmiyor".
    Kararı sınayan test `servis.genc_uygunluk_yargila`'yı kendisi değiştirir."""
    from app.agents.eslestirme import BILINMIYOR, Yargi
    from app.servisler import eslestirme as servis

    async def yargila(ihtiyac, aday):
        try:
            gerekce = await servis.gerekce_uret(ihtiyac, aday)
        except Exception:
            return BILINMIYOR
        return BILINMIYOR if gerekce is None else Yargi(gerekce=gerekce, uygunluk="uygun")

    monkeypatch.setattr(servis, "genc_uygunluk_yargila", yargila)


class SahteEpostaGonderici:
    kip = "sahte"

    def __init__(self) -> None:
        self.gonderilenler: list = []

    async def gonder(self, eposta) -> None:
        self.gonderilenler.append(eposta)


@pytest.fixture(autouse=True)
def eposta_gonderilmez(monkeypatch):
    """Hiçbir test gerçek e-posta göndermez ya da log kipine bağlı kalmaz.
    Gönderilenler kaydedilir; e-postayı sınayan test bu fixture'ı ister."""
    from app.core.dis_servisler import kurulum

    gonderici = SahteEpostaGonderici()
    monkeypatch.setattr(kurulum, "eposta_gonderici", lambda: gonderici)
    return gonderici


@pytest.fixture(autouse=True)
def depo(monkeypatch, tmp_path):
    """Testler `.env`'deki depoya ve virüs tarayıcısına bağlı kalmaz: dosyalar
    testin geçici klasörüne yazılır, tarama kapalı. Depoyu sınayan test bunu ister."""
    from app.core.dis_servisler import kurulum
    from app.core.dis_servisler.depo import YerelDepo
    from app.core.dis_servisler.virus import KapaliTarayici

    yerel = YerelDepo(tmp_path / "depo", "test-dosya-imzasi", "http://testserver")
    monkeypatch.setattr(kurulum, "depo", lambda: yerel)
    monkeypatch.setattr(kurulum, "virus_tarayici", lambda: KapaliTarayici())
    return yerel


@pytest.fixture(autouse=True)
def dosya_modele_okutulmaz(monkeypatch):
    """Taranmış PDF ve görsel yüklenirken modele okutuluyor (gerçek LLM). Testlerde
    sabit bir okunuş döner; okumayı sınayan test bu nesneyi değiştirir."""
    from app.agents.dogrulama.dosya_cikarimi import DosyaOkunusu
    from app.servisler.dogrulama import dosyalar

    okunus = {"deger": DosyaOkunusu(gorsel_metni="", betim="Boş bir sayfa")}
    cagrilar: list = []

    async def oku(veri, icerik_turu):
        cagrilar.append(icerik_turu)
        return okunus["deger"]

    monkeypatch.setattr(dosyalar, "dosyayi_oku", oku)
    okunus["cagrilar"] = cagrilar
    return okunus


@pytest.fixture(autouse=True)
def yedek_okuyucu_yok(monkeypatch):
    """Testler yerelde çalışan bir Playwright servisine, Jina'ya ya da Cloud Vision'a bağlı kalmaz:
    yedek ve uzak okuyucu kapalı, ekran görüntüsü okunuş önbelleği her testte boş.
    Yedek yolu sınayan test kanıt okumaya sahte bir yedek okuyucu verir."""
    from app.agents.dogrulama import okuma
    from app.core.dis_servisler import kurulum
    from app.core.dis_servisler.gorsel_arayici import KapaliGorselArayici
    from app.core.dis_servisler.uzak_okuyucu import KapaliUzakOkuyucu
    from app.core.dis_servisler.yedek_okuyucu import KapaliYedekOkuyucu

    monkeypatch.setattr(kurulum, "yedek_okuyucu", lambda: KapaliYedekOkuyucu())
    monkeypatch.setattr(kurulum, "uzak_okuyucu", lambda: KapaliUzakOkuyucu())
    # Görsel kaynak araması (Cloud Vision) da kapalı; sınayan test sahtesini verir.
    monkeypatch.setattr(kurulum, "gorsel_arayici", lambda: KapaliGorselArayici())
    okuma.EKRAN_OKUNUSLARI.temizle()


@pytest.fixture(autouse=True)
def link_yoklamasi_ag_yok(monkeypatch):
    """Canlılık taraması kanıt linklerini yoklar (gerçek ağ). Testlerde yerel
    veritabanındaki linklere gidilmesin: nötr sonuç (sayaç değişmez). Yoklamayı
    sınayan test okuyucuyu kendisi verir."""
    from app.core.kanit_okuma.belge import ErisimDurumu
    from app.servisler.dogrulama import curume

    async def notr(_url):
        return ErisimDurumu.ENGELLENDI

    monkeypatch.setattr(curume, "erisimi_oku", notr)
