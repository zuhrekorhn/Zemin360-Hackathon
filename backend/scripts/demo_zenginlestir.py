"""Demo verisini zenginleştirir: yeni firma, ilan ve genç kartları ekler.

`demo_hesaplari.py` ile aynı desen: hesaplar `hesap_olustur`'la açılır, kartlar
sohbetsiz yazılır, embedding mevcut işlevlerle hesaplanır (Voyage). Yalnızca
EKLER: var olan hesaba, karta, ilana ve eşleşmeye dokunmaz; bir kayıt zaten
varsa atlanır, yani yeniden çalıştırmak güvenli. Önce `demo_hesaplari.py`
çalışmış olmalı (Moda Dayanışma Kooperatifi ve Soğuk Lojistik hesabı bulunur).

    .venv/Scripts/python.exe scripts/demo_zenginlestir.py

Eklenenler: 3 firma kartı (soğuk zincir girişimi, e-ticaret kurumsalı, gıda
perakende danışmanlığı), Soğuk Lojistik adına bir ortak ilanı, kooperatif adına
ikinci bir genç ilanı ve farklı alanlardan 9 genç kartı (biri sosyal medya ilanı için).
Adların hepsi kurgusal, e-postalar `.example` alan adında. Hesapların e-postası doğrulanmış açılır.

Güven göstergeleri (bazı çalışmalarda) betikte elle yazılır: gerçek kanıt hattı
(bağlantı, dosya, referans) çalıştırılmaz. Amaç, doğrulama bonusunun sıralamaya
etkisinin demoda görünmesi; bu satırlar gerçek bir değerlendirmenin sonucu değil.

Sonunda üç ilan için eşleştirme çalışır (Soğuk Lojistik ortak ilanı, kooperatifin
iki genç ilanı); gerekçeler için LLM çağrılır. Anadolu Market ilanına ve elle
denenmiş iş birliği kaydına dokunulmaz, o ilan için pipeline çalıştırılmaz.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import sys
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.agents.dogrulama.cekirdek import KURAL_SURUMU
from app.api import ihtiyac_kartlari, yetenek_kartlari
from app.api.auth import hesap_olustur
from app.core.config import get_settings
from app.core.firma_dogrulama import DOGRULANDI
from app.core.metin import eposta_normalize
from app.db.session import get_sessionmaker
from app.models.firma_karti import FirmaKarti
from app.models.guven_skoru import GuvenSkoru
from app.models.hesap import ROL_GENC, ROL_KURUM, Hesap
from app.models.ihtiyac_karti import IhtiyacKarti
from app.models.kullanici import Kullanici
from app.models.kurum import Kurum
from app.models.somut_cikti import SomutCikti
from app.models.yetenek_karti import YetenekKarti
from app.schemas.profil import FirmaKayitProfili, GencKayitProfili
from app.servisler import firma_karti as firma_servisi
from app.servisler.eslestirme import pipeline_calistir
from scripts.demo_hesaplari import ALAN, KURUM_EPOSTA, kurumun_karti, sifreyi_dogrula

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SOGUK_LOJISTIK_EPOSTA = "ayse@soguklojistik.example"


# --- Firmalar ---------------------------------------------------------------


@dataclass
class FirmaTanimi:
    eposta: str
    ad: str
    profil: FirmaKayitProfili
    ne_yapiyoruz: str
    yetkinlikler: list[str]
    onceki_isler: str
    aranan_isbirligi: str
    isbirligi_turleri: list[str]
    dogrulanmis: bool = False


FIRMALAR = [
    FirmaTanimi(
        eposta="iletisim@ayazsensor.example",
        ad="Ayaz Sensör Teknolojileri",
        profil=FirmaKayitProfili(
            tur="girisim",
            sektor="lojistik teknolojisi",
            sehir="İstanbul",
            web_sitesi="https://ayazsensor.example",
            calisan_araligi="1-10",
            kurulus_yili=2022,
            tanitim="Soğuk zincirde sıcaklık takibi yapan bir girişim.",
        ),
        ne_yapiyoruz="Soğutmalı araçlarda ve soğuk depolarda IoT sensörüyle sıcaklığı "
        "anlık izleyen, sıcaklık ihlalinde yetkiliye hemen uyarı gönderen soğuk zincir "
        "takip yazılımı ve sensör seti.",
        yetkinlikler=[
            "soğuk zincir sıcaklık izleme",
            "IoT sensör",
            "sıcaklık ihlali uyarısı",
            "araç ve depo takibi",
        ],
        onceki_isler="İki lojistik firmasında soğutmalı araç ve depolarda pilot yaptık; "
        "sıcaklık ihlali artık dakikalar içinde yetkiliye ulaşıyor, elle okuma gerekmiyor.",
        aranan_isbirligi="Soğutmalı araç filosu ya da soğuk deposu olan, sensör pilotuna "
        "açık bir lojistik firması.",
        isbirligi_turleri=["pilot"],
        dogrulanmis=True,
    ),
    FirmaTanimi(
        eposta="iletisim@vitrinpark.example",
        ad="Vitrinpark Online Ticaret A.Ş.",
        profil=FirmaKayitProfili(
            tur="kurumsal",
            sektor="e-ticaret",
            sehir="İstanbul",
            web_sitesi="https://vitrinpark.example",
            calisan_araligi="250+",
            kurulus_yili=2011,
            tanitim="Elektronik, ev ve gıda ürünleri satan bir online pazaryeri.",
        ),
        ne_yapiyoruz="Elektronik, ev ve taze gıda ürünlerini online satan bir pazaryeri. "
        "Kendi müşteri hizmetlerimizi ve çağrı merkezimizi işletiyoruz; sipariş, iade ve "
        "teslimat operasyonunu yönetiyoruz. Talep tahmini ya da sensör yazılımı "
        "geliştirmiyoruz.",
        yetkinlikler=[
            "müşteri hizmetleri",
            "çağrı merkezi yönetimi",
            "sipariş ve teslimat operasyonu",
            "pazaryeri yönetimi",
        ],
        onceki_isler="Yılda 20 milyon siparişi karşılayan çağrı merkezi ve iade operasyonu; "
        "taze gıda teslimatında müşteri şikâyetlerini takip eden bir ekip.",
        aranan_isbirligi="Pazaryerimize ürün ya da hizmet sunacak satıcılar.",
        isbirligi_turleri=["diger"],
    ),
    FirmaTanimi(
        eposta="iletisim@yolguc.example",
        ad="Yolgüç Operasyon Danışmanlık",
        profil=FirmaKayitProfili(
            tur="kobi",
            sektor="danışmanlık",
            sehir="İstanbul",
            web_sitesi="https://yolguc.example",
            calisan_araligi="11-50",
            kurulus_yili=2016,
            tanitim="Gıda perakendecilerine operasyon ve tedarik danışmanlığı.",
        ),
        ne_yapiyoruz="Gıda perakendecilerine operasyon ve tedarik zinciri danışmanlığı: "
        "şube süreçleri, tedarikçi yönetimi, stok ve sevkiyat planlaması. Yazılım "
        "geliştirmiyoruz, ihtiyaç olduğunda yazılım ortaklarıyla çalışıyoruz.",
        yetkinlikler=[
            "operasyon iyileştirme",
            "tedarik zinciri danışmanlığı",
            "tedarikçi yönetimi",
            "gıda perakendesi",
        ],
        onceki_isler="Üç bölgesel market zincirinde şube sipariş ve sevkiyat süreçlerini "
        "yeniden tasarladık.",
        aranan_isbirligi="Yazılım çözümünü şubelerde uygulatmak isteyen teknoloji firmaları.",
        isbirligi_turleri=["pilot", "diger"],
    ),
]


# --- İlanlar ----------------------------------------------------------------


def sogukluk_ilani(kurum_id) -> IhtiyacKarti:
    return IhtiyacKarti(
        kurum_id=kurum_id,
        aranan="firma",
        # Boş = her tür: ilan tür seçseydi SQL kesin şartı kimin çıkacağını belirlerdi,
        # benzerlik testi anlamsızlaşırdı.
        aranan_firma_turleri=[],
        isbirligi_turu="pilot",
        problem_tanimi="Soğutmalı araçlarımızda ve depolarımızda sıcaklık takibi elle, saatte "
        "bir yapılan okumalarla yürüyor; sıcaklık ihlali geç fark ediliyor ve ürün kaybı "
        "yaşıyoruz. Araç ve depolarda sıcaklığı anlık izleyecek ve ihlal olduğunda yetkiliyi "
        "uyaracak bir teknoloji ortağı arıyoruz.",
        basari_kriteri="Pilot süresince 3 araçta sıcaklık ihlallerinin tamamı 5 dakika "
        "içinde uyarıyla yakalansın.",
        kisitlar="Pilot 3 araçta; sensör kurulumu kendi araç servisimizde yapılacak.",
    )


def kooperatif_sosyal_medya_ilani(kurum_id) -> IhtiyacKarti:
    return IhtiyacKarti(
        kurum_id=kurum_id,
        problem_tanimi="Kooperatifin sosyal medya hesapları düzensiz paylaşılıyor; bağış "
        "çağrılarımız ve etkinliklerimiz mahalleye ulaşmıyor. Haftalık bir içerik takvimi "
        "hazırlayacak, kısa görsel ve metinlerle kooperatifi tanıtacak bir sosyal medya "
        "ve tanıtım desteği arıyoruz.",
        basari_kriteri="3 ay içinde takipçi sayısı ikiye katlansın, her ay en az 8 paylaşım "
        "yapılsın.",
        kisitlar="Bütçe yok; haftada birkaç saatlik gönüllü destek yeterli.",
        sehir_tercihi="İstanbul",
        calisma_modeli="uzaktan",
        musaitlik_tercihi="proje_bazli",
    )


# --- Gençler ----------------------------------------------------------------


@dataclass
class CiktiTanimi:
    baslik: str
    aciklama: str
    is_turu: str
    kendi_rolu: str
    olculebilir_sonuc: str
    # (kanıt orijinalliği, ölçülebilirlik, rol netliği, üçüncü taraf onayı); None = gösterge yok
    gosterge: tuple[int | None, int | None, int | None, int | None] | None = None


@dataclass
class GencTanimi:
    ad: str
    eposta_on_eki: str
    rol: str
    deneyim: str
    sektorler: list[str]
    araclar: list[str]
    ciktilar: list[CiktiTanimi]
    kariyer_durumu: str = "ogrenci"
    okul: str | None = None
    bolum: str | None = None
    grup: str = ""  # yalnızca rapor için: uygun / kısmen / komşu / alakasız


GENCLER = [
    GencTanimi(
        ad="Burak Aydın",
        eposta_on_eki="burak.aydin",
        rol="web uygulaması geliştirici",
        deneyim="orta",
        sektorler=["sivil toplum", "sosyal yardım"],
        araclar=["Python", "Django", "PostgreSQL", "React"],
        kariyer_durumu="mezun",
        okul="Yıldız Teknik Üniversitesi",
        bolum="Bilgisayar Mühendisliği",
        grup="uygun",
        ciktilar=[
            CiktiTanimi(
                "Yardım derneği bağış ve dağıtım takip uygulaması",
                "Derneğin ayni bağışlarını ve ailelere yapılan dağıtımları kaydeden, aylık "
                "raporu otomatik çıkaran web uygulaması.",
                "proje",
                "Tasarım, veritabanı ve arayüzü tek başıma geliştirdim; derneğin gönüllüleri "
                "kullanıyor.",
                "900 bağışçı ve 350 aile kaydı; aylık rapor 1 günden 10 dakikaya indi.",
                (3, 2, 3, 2),
            ),
            CiktiTanimi(
                "Okul kantini stok takip sistemi",
                "Kantinin günlük stok giriş çıkışını tutan basit web uygulaması.",
                "gonulluluk",
                "Kodlamayı ve veritabanını yaptım.",
                "Haftalık fire listesi otomatik çıkıyor.",
                (2, 1, 2, None),
            ),
        ],
    ),
    GencTanimi(
        ad="Selin Karaca",
        eposta_on_eki="selin.karaca",
        rol="web uygulaması ve veritabanı geliştirici",
        deneyim="baslangic",
        sektorler=["sivil toplum", "gıda"],
        araclar=["Node.js", "PostgreSQL", "Next.js", "Excel"],
        okul="İstanbul Teknik Üniversitesi",
        bolum="Yazılım Mühendisliği",
        grup="uygun",
        ciktilar=[
            CiktiTanimi(
                "Gıda dağıtım noktası stok ve kayıt sistemi",
                "Bir mahalle dayanışma mutfağının stok girişlerini, günlük dağıtımları ve aile "
                "kayıtlarını tutan web uygulaması; haftalık rapor sayfası var.",
                "proje",
                "Veritabanını ve rapor sayfalarını ben yaptım.",
                "Gönüllüler kâğıt defteri bıraktı; rapor sayfası her hafta kullanılıyor.",
                (3, 2, 3, 2),
            ),
            CiktiTanimi(
                "Gönüllü kayıt formu ve rapor paneli",
                "Bir belediye etkinliği için gönüllü başvurularını toplayan form ve yöneticiler "
                "için özet panel.",
                "staj",
                "Staj boyunca formu ve paneli geliştirdim.",
                "280 gönüllü başvurusu tek panelde toplandı.",
                (3, 3, 2, 2),
            ),
        ],
    ),
    GencTanimi(
        ad="Emre Yıldız",
        eposta_on_eki="emre.yildiz",
        rol="mobil uygulama geliştirici",
        deneyim="orta",
        sektorler=["eğitim", "sivil toplum"],
        araclar=["Flutter", "Dart", "Firebase"],
        okul="Marmara Üniversitesi",
        bolum="Bilgisayar Mühendisliği",
        grup="kısmen",
        ciktilar=[
            CiktiTanimi(
                "Kampüs yemekhane menü ve doluluk uygulaması",
                "Öğrencilerin günlük menüyü ve yemekhane yoğunluğunu gördüğü mobil uygulama.",
                "proje",
                "Uygulamanın tamamını geliştirdim.",
                "1.200 öğrenci indirdi, günlük 300 kullanıcı.",
            ),
            CiktiTanimi(
                "Gönüllü etkinlik takvimi uygulaması",
                "Bir öğrenci topluluğunun etkinliklerini ve gönüllü vardiyalarını gösteren mobil "
                "uygulama.",
                "gonulluluk",
                "Arayüzü ve bildirimleri yaptım.",
                "4 etkinlikte gönüllü vardiyaları uygulamadan yönetildi.",
            ),
        ],
    ),
    GencTanimi(
        ad="Deniz Arslan",
        eposta_on_eki="deniz.arslan",
        rol="veri analisti",
        deneyim="orta",
        sektorler=["sivil toplum", "finans"],
        araclar=["SQL", "Python", "pandas", "Power BI", "Excel"],
        kariyer_durumu="mezun",
        okul="Boğaziçi Üniversitesi",
        bolum="İstatistik",
        grup="kısmen",
        ciktilar=[
            CiktiTanimi(
                "Bir derneğin bağış verisi analizi ve aylık panel",
                "Üç yıllık bağış kayıtlarını temizleyip bağışçı gruplarına ve aylara göre "
                "analiz ettim, Power BI'da aylık bir panel hazırladım.",
                "proje",
                "Veri temizliği, analiz ve panel bana ait.",
                "Dernek yönetimi bağış çağrılarını panele göre planlıyor.",
                (2, 2, 2, None),
            ),
            CiktiTanimi(
                "Öğrenci kulübü üye anketi raporu",
                "400 yanıtlık üye anketini analiz edip sonuçları rapora döktüm.",
                "gonulluluk",
                "Anket tasarımı ve analiz.",
                "Rapor kulüp yönetimine sunuldu.",
            ),
        ],
    ),
    GencTanimi(
        ad="Zeynep Kaya",
        eposta_on_eki="zeynep.kaya",
        rol="ziraat mühendisi",
        deneyim="orta",
        sektorler=["tarım", "gıda"],
        araclar=["Excel", "QGIS", "AutoCAD"],
        kariyer_durumu="mezun",
        okul="Ankara Üniversitesi",
        bolum="Ziraat Mühendisliği",
        grup="komşu",
        ciktilar=[
            CiktiTanimi(
                "Kooperatif için hasat sonrası kayıp analizi",
                "Bir üretici kooperatifinin sebze ve meyvede hasat sonrası kayıplarını "
                "ölçtüm, nedenlerini ve azaltma önerilerini raporladım.",
                "is",
                "Saha ölçümünü ve raporu ben yaptım.",
                "Kayıp oranı %18'den %11'e düştü.",
            ),
            CiktiTanimi(
                "Organik üretici envanteri",
                "Bölgedeki 40 küçük üreticinin ürün ve kapasite bilgisini tek tabloda topladım.",
                "gonulluluk",
                "Görüşmeleri ve tabloyu hazırladım.",
                "40 üretici tek envanterde.",
            ),
        ],
    ),
    GencTanimi(
        ad="Mert Özkan",
        eposta_on_eki="mert.ozkan",
        rol="endüstri mühendisi",
        deneyim="baslangic",
        sektorler=["lojistik", "üretim"],
        araclar=["Excel", "Python", "Arena", "AutoCAD"],
        okul="İstanbul Teknik Üniversitesi",
        bolum="Endüstri Mühendisliği",
        grup="komşu",
        ciktilar=[
            CiktiTanimi(
                "Depo yerleşim iyileştirme çalışması",
                "Bir dağıtım deposunda ürün yerleşimini sipariş sıklığına göre yeniden "
                "düzenleyen staj projesi.",
                "staj",
                "Veriyi analiz ettim, yerleşim önerisini hazırladım.",
                "Toplama süresi ortalama %12 kısaldı.",
            ),
            CiktiTanimi(
                "Stok seviyesi planlama modeli",
                "Bir market için ürün bazında güvenlik stoğu hesaplayan Excel modeli.",
                "proje",
                "Modeli kurdum.",
                "Raf boşluğu şikâyetleri azaldı.",
            ),
        ],
    ),
    GencTanimi(
        ad="Ceren Polat",
        eposta_on_eki="ceren.polat",
        rol="grafik animatör",
        deneyim="orta",
        sektorler=["medya", "reklam"],
        araclar=["After Effects", "Blender", "Illustrator"],
        okul="Mimar Sinan Güzel Sanatlar Üniversitesi",
        bolum="Grafik Tasarım",
        grup="alakasız",
        ciktilar=[
            CiktiTanimi(
                "Kısa tanıtım animasyonları",
                "Üç küçük işletme için 30 saniyelik hareketli tanıtım videosu hazırladım.",
                "is",
                "Hikâye, çizim ve animasyonun tamamı bende.",
                "Videolar işletmelerin sayfalarında yayında.",
            ),
            CiktiTanimi(
                "Belgesel başlık animasyonu",
                "Bir öğrenci belgeseli için açılış ve başlık animasyonu.",
                "proje",
                "Tasarım ve animasyon.",
                "Belgesel bir festivalde gösterildi.",
            ),
        ],
    ),
    GencTanimi(
        ad="Kaan Erdem",
        eposta_on_eki="kaan.erdem",
        rol="hukuk stajyeri",
        deneyim="baslangic",
        sektorler=["hukuk"],
        araclar=["UYAP", "Word", "mevzuat arama"],
        okul="İstanbul Üniversitesi",
        bolum="Hukuk",
        grup="alakasız",
        ciktilar=[
            CiktiTanimi(
                "Kira sözleşmesi inceleme notları",
                "Bir bürodaki kira uyuşmazlıkları için sözleşme maddelerini inceleyip özet "
                "notlar çıkardım.",
                "staj",
                "Maddeleri inceledim ve notları yazdım.",
                "18 dosyada avukata hazır özet sağlandı.",
            ),
            CiktiTanimi(
                "İş hukuku emsal karar derlemesi",
                "Kıdem tazminatı konusunda Yargıtay emsal kararlarını derleyen bir dosya.",
                "proje",
                "Karar taraması ve derleme.",
                "60 karar konularına göre derlendi.",
            ),
        ],
    ),
    # Kooperatifin sosyal medya ilanına uygun tek aday: ilan boş durum göstermesin.
    GencTanimi(
        ad="Defne Yalçın",
        eposta_on_eki="defne.yalcin",
        rol="sosyal medya ve içerik üreticisi",
        deneyim="orta",
        sektorler=["sivil toplum", "gıda", "kültür sanat"],
        araclar=["Instagram", "Canva", "CapCut", "Meta Business Suite"],
        okul="Kadir Has Üniversitesi",
        bolum="Yeni Medya ve İletişim",
        grup="uygun (sosyal medya ilanı)",
        ciktilar=[
            CiktiTanimi(
                "Bir mahalle kitap kafesinin Instagram hesabı yönetimi",
                "Kafenin Instagram hesabı için haftalık içerik takvimi hazırladım; "
                "gönderi, hikâye ve kısa video üretip yayınladım.",
                "gonulluluk",
                "İçerik planını, görselleri ve paylaşımları tek başıma yürüttüm.",
                "Takipçi sayısı 6 ayda 1.200'den 5.400'e çıktı; haftada 4 gönderi.",
            ),
            CiktiTanimi(
                "Öğrenci topluluğu için kısa video ve görsel içerik",
                "Bir öğrenci topluluğunun etkinlik duyuruları için 12 kısa video ve afiş "
                "hazırladım.",
                "proje",
                "Çekim, kurgu ve tanıtım metinlerini ben yaptım.",
                "Videolar ortalama 8.000 izlenme aldı; etkinlik katılımı arttı.",
            ),
        ],
    ),
]


def genc_profili(bolum: str | None, okul: str | None, durum: str) -> GencKayitProfili:
    # Şehir, çalışma modeli ve müsaitlik herkeste aynı: sert filtreler benzerlik
    # sınamasını karıştırmasın (kooperatifin iki ilanının da şartlarını karşılar).
    return GencKayitProfili(
        sehir="İstanbul",
        calisma_modelleri=["hibrit", "uzaktan"],
        kariyer_durumu=durum,
        musaitlikler=["yarim_zamanli", "proje_bazli"],
        okul=okul,
        bolum=bolum,
        sinif=3 if durum == "ogrenci" else None,
    )


# --- Yazma ------------------------------------------------------------------


async def _hesap_var_mi(oturum, email: str) -> bool:
    return (
        await oturum.scalar(select(Hesap.id).where(Hesap.email == eposta_normalize(email)))
    ) is not None


async def _kurum(oturum, email: str) -> Kurum:
    kurum = await oturum.scalar(
        select(Kurum)
        .join(Hesap, Hesap.id == Kurum.hesap_id)
        .where(Hesap.email == eposta_normalize(email))
    )
    if kurum is None:
        raise SystemExit(f"{email} hesabı yok; önce scripts/demo_hesaplari.py çalışmalı.")
    return kurum


async def _ilan_yoksa_ekle(oturum, ilan: IhtiyacKarti) -> tuple[IhtiyacKarti, bool]:
    """Aynı kurumun aynı metinli ilanı varsa onu döner; yoksa ekler ve embedding'ini hesaplar."""
    var = await oturum.scalar(
        select(IhtiyacKarti).where(
            IhtiyacKarti.kurum_id == ilan.kurum_id,
            IhtiyacKarti.problem_tanimi == ilan.problem_tanimi,
        )
    )
    if var is not None:
        return var, False
    oturum.add(ilan)
    await oturum.commit()
    await ihtiyac_kartlari.embedding_hesapla(oturum, ilan)
    return ilan, True


async def zenginlestir(sifre: str) -> list[str]:
    satirlar: list[str] = []
    async with get_sessionmaker()() as oturum:
        # A) Firma kartları
        for tanim in FIRMALAR:
            if await _hesap_var_mi(oturum, tanim.eposta):
                satirlar.append(f"firma  {tanim.ad}: zaten vardı, dokunulmadı")
                continue
            hesap = await hesap_olustur(
                oturum,
                email=tanim.eposta,
                sifre=sifre,
                rol=ROL_KURUM,
                ad=tanim.ad,
                firma_profili=tanim.profil,
                kvkk_onay=True,
                eposta_dogrulandi=True,
            )
            kurum = await oturum.scalar(select(Kurum).where(Kurum.hesap_id == hesap.id))
            if tanim.dogrulanmis:
                kurum.dogrulama_durumu = DOGRULANDI
                kurum.dogrulama_tarihi = dt.datetime.now(dt.UTC)
            oturum.add(
                FirmaKarti(
                    kurum_id=kurum.id,
                    ne_yapiyoruz=tanim.ne_yapiyoruz,
                    yetkinlikler=tanim.yetkinlikler,
                    onceki_isler=tanim.onceki_isler,
                    aranan_isbirligi=tanim.aranan_isbirligi,
                    isbirligi_turleri=tanim.isbirligi_turleri,
                )
            )
            await oturum.commit()
            kart = await firma_servisi.kurumun_karti(oturum, kurum.id)
            gomuldu = await firma_servisi.embedding_hesapla(oturum, kart)
            dogrulama = "doğrulanmış" if tanim.dogrulanmis else "doğrulama bekliyor"
            satirlar.append(
                f"firma  {tanim.ad} ({tanim.profil.tur}, {dogrulama}): eklendi"
                f"{'' if gomuldu else ' — EMBEDDING YOK'}"
            )

        # B) İlanlar
        soguk = await _kurum(oturum, SOGUK_LOJISTIK_EPOSTA)
        kooperatif = await _kurum(oturum, KURUM_EPOSTA)
        ilan_soguk, yeni = await _ilan_yoksa_ekle(oturum, sogukluk_ilani(soguk.id))
        satirlar.append(
            f"ilan   {soguk.ad} — ortak ilanı (sıcaklık izleme, pilot): "
            f"{'eklendi' if yeni else 'zaten vardı'}"
        )
        ilan_sosyal, yeni = await _ilan_yoksa_ekle(
            oturum, kooperatif_sosyal_medya_ilani(kooperatif.id)
        )
        satirlar.append(
            f"ilan   {kooperatif.ad} — genç ilanı (sosyal medya ve tanıtım): "
            f"{'eklendi' if yeni else 'zaten vardı'}"
        )

        # C) Gençler
        for tanim in GENCLER:
            eposta = f"{tanim.eposta_on_eki}@{ALAN}"
            if await _hesap_var_mi(oturum, eposta):
                satirlar.append(f"genç   {tanim.ad}: zaten vardı, dokunulmadı")
                continue
            hesap = await hesap_olustur(
                oturum,
                email=eposta,
                sifre=sifre,
                rol=ROL_GENC,
                ad=tanim.ad,
                genc_profili=genc_profili(tanim.bolum, tanim.okul, tanim.kariyer_durumu),
                kvkk_onay=True,
                eposta_dogrulandi=True,
            )
            kullanici = await oturum.scalar(select(Kullanici).where(Kullanici.hesap_id == hesap.id))
            gostergeli = [c for c in tanim.ciktilar if c.gosterge is not None]
            kart = YetenekKarti(
                kullanici_id=kullanici.id,
                rol_alani=tanim.rol,
                deneyim_seviyesi=tanim.deneyim,
                sektor_ilgi_alani=tanim.sektorler,
                araclar_teknolojiler=tanim.araclar,
                # Göstergesi olmayan çalışma varsa kanıt bekliyor (demo_hesaplari'ndaki gibi).
                kanit_bekleyen=len(gostergeli) < len(tanim.ciktilar),
                somut_ciktilar=[
                    SomutCikti(
                        baslik=c.baslik,
                        aciklama=c.aciklama,
                        is_turu=c.is_turu,
                        kendi_rolu=c.kendi_rolu,
                        olculebilir_sonuc=c.olculebilir_sonuc,
                    )
                    for c in tanim.ciktilar
                ],
            )
            oturum.add(kart)
            await oturum.flush()
            for cikti, tanimi in zip(kart.somut_ciktilar, tanim.ciktilar, strict=True):
                if tanimi.gosterge is None:
                    continue
                orijinallik, olculebilirlik, rol, onay = tanimi.gosterge
                oturum.add(
                    GuvenSkoru(
                        somut_cikti_id=cikti.id,
                        kanit_orijinalligi=orijinallik,
                        sonuc_olculebilirligi=olculebilirlik,
                        rol_netligi=rol,
                        ucuncu_taraf_onayi=onay,
                        gerekce_metni="Demo verisi: gösterge elle yazıldı.",
                        kural_surumu=KURAL_SURUMU,
                        degerlendirme_tarihi=dt.datetime.now(dt.UTC),
                    )
                )
            await oturum.commit()
            kart = await oturum.scalar(
                select(YetenekKarti)
                .where(YetenekKarti.id == kart.id)
                .options(selectinload(YetenekKarti.somut_ciktilar))
            )
            gomuldu = await yetenek_kartlari.embedding_hesapla(oturum, kart)
            gosterge = f"{len(gostergeli)}/{len(tanim.ciktilar)} çalışmada gösterge"
            satirlar.append(
                f"genç   {tanim.ad} ({tanim.rol}; {tanim.grup}; {gosterge}): eklendi"
                f"{'' if gomuldu else ' — EMBEDDING YOK'}"
            )

        # Eşleştirme: yalnızca yeni ilanlar ve kooperatifin gıda bankası ilanı (genç
        # kartları ona da aday). Anadolu Market ilanı bilerek dışarıda.
        gida_bankasi = await oturum.scalar(
            select(IhtiyacKarti).where(
                IhtiyacKarti.kurum_id == kooperatif.id,
                IhtiyacKarti.problem_tanimi == kurumun_karti(kooperatif.id).problem_tanimi,
            )
        )
        for ilan in (ilan_soguk, ilan_sosyal, gida_bankasi):
            if ilan is None:
                continue
            if ilan.embedding is None:
                satirlar.append(f"UYARI ilan {ilan.id} embedding'i yok; eşleştirme atlandı")
                continue
            sonuc = await pipeline_calistir(oturum, ilan)
            satirlar.append(f"eşleştirme {ilan.id}: {len(sonuc)} öneri")
    return satirlar


def main() -> None:
    sifre = sifreyi_dogrula(get_settings().demo_sifresi)
    for satir in asyncio.run(zenginlestir(sifre)):
        print(satir)
    print("Şifre: .env'deki DEMO_SIFRESI")


if __name__ == "__main__":
    main()
