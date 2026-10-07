"""Demo hesaplarını açar (docs/kimlik-ve-dongu.md § 9).

Beş hesap: genç, kurum, GİRVAK ve firma akışı için iki firma (bir girişim,
bir kurumsal; docs/kararlar.md F20). Şifre `.env`'deki
DEMO_SIFRESI'nden; repoda şifre yok. Genç hesabına bir yetenek kartı, kuruma
bir ihtiyaç kartı yazılır. Girişimin doğrulanmış bir firma kartı, kurumsalın
yalnızca girişim arayan açık bir ortak ilanı olur: iki kart birbirine önerilir.
Kartlar sohbetsiz, doğrudan yazılıyor: LLM çağrısı yok, yalnızca embedding
(Voyage). İki kart birbirine önerilecek şekilde seçildi; betik sonunda
benzerliği yazdırır, eşleştirmenin alt sınırının altındaysa uyarır.

Zaten açılmış hesaba dokunulmaz (yeniden çalıştırmak güvenli). Temiz başlangıç:

    .venv/Scripts/python.exe scripts/yerel_sifirla.py
    .venv/Scripts/python.exe scripts/demo_hesaplari.py

Adresler `.example` alan adında: belgeler için ayrılmış (RFC 2606), hiçbir
zaman gerçek bir posta kutusuna çözülmez. Nottaki `@demo.zemin360` giriş
formunun e-posta doğrulamasından geçmiyordu (geçerli üst alan adı değil).
"""

from __future__ import annotations

import asyncio
import datetime as dt
import math
import sys
from dataclasses import dataclass

from sqlalchemy import select

from app.agents.eslestirme import (
    BENZERLIK_ALT_SINIRI,
    benzerlik_yeterli_mi,
    firma_bonusu,
    skor_hesapla,
)
from app.api.auth import hesap_olustur
from app.core.config import get_settings
from app.core.firma_dogrulama import DOGRULANDI
from app.core.kimlik import SIFRE_EN_AZ
from app.core.metin import eposta_normalize
from app.db.session import get_sessionmaker
from app.models.firma_karti import FirmaKarti
from app.models.hesap import ROL_GENC, ROL_GIRVAK, ROL_KURUM, Hesap
from app.models.ihtiyac_karti import IhtiyacKarti
from app.models.kullanici import Kullanici
from app.models.kurum import Kurum
from app.models.somut_cikti import SomutCikti
from app.models.yetenek_karti import YetenekKarti
from app.schemas.profil import FirmaKayitProfili, GencKayitProfili
from app.servisler import embedding as embedding_servisi
from app.servisler import firma_karti as firma_servisi

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ALAN = "demo.zemin360.example"
GENC_EPOSTA = f"genc@{ALAN}"
KURUM_EPOSTA = f"kurum@{ALAN}"
GIRVAK_EPOSTA = f"girvak@{ALAN}"
GIRISIM_EPOSTA = f"girisim@{ALAN}"
KURUMSAL_EPOSTA = f"kurumsal@{ALAN}"

GENC_ADI = "Elif Demir"
KURUM_ADI = "Moda Dayanışma Kooperatifi"
KURUM_PROFILI = FirmaKayitProfili(
    tur="kobi",
    sektor="sivil toplum",
    sehir="İstanbul",
    calisan_araligi="11-50",
    kurulus_yili=2014,
    tanitim="Kadıköy'de gıda bankası ve dayanışma mutfağı işleten bir kooperatif.",
)

# Firma akışı (docs/kararlar.md F20). Web sitesi e-postanın
# alan adıyla aynı: GİRVAK'ın listesinde ipucu "uyuşuyor" görünür.
GIRISIM_ADI = "Tazele Analitik"
GIRISIM_PROFILI = FirmaKayitProfili(
    tur="girisim",
    sektor="perakende teknolojisi",
    sehir="İstanbul",
    web_sitesi=f"https://{ALAN}",
    calisan_araligi="1-10",
    kurulus_yili=2023,
    tanitim="Taze ürün satan perakendeciler için talep tahmini yazılımı geliştiren bir girişim.",
)
KURUMSAL_ADI = "Anadolu Market Zinciri A.Ş."
KURUMSAL_PROFILI = FirmaKayitProfili(
    tur="kurumsal",
    sektor="perakende",
    sehir="İstanbul",
    web_sitesi=f"https://{ALAN}",
    calisan_araligi="250+",
    kurulus_yili=1998,
    tanitim="Marmara'da 120 şubesi olan bir süpermarket zinciri.",
)


@dataclass
class Sonuc:
    email: str
    rol: str
    yeni: bool
    not_: str = ""


def sifreyi_dogrula(sifre: str) -> str:
    if len(sifre) < SIFRE_EN_AZ:
        raise SystemExit(
            f"DEMO_SIFRESI .env'de tanımlı değil ya da {SIFRE_EN_AZ} karakterden kısa."
        )
    return sifre


def benzerlik(a: list[float], b: list[float]) -> float:
    """Kosinüs benzerliği; eşleştirme pgvector'da aynı ölçüyü kullanıyor."""
    carpim = sum(x * y for x, y in zip(a, b, strict=True))
    return carpim / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))


def oneri_durumu(deger: float, dogrulama_bonus: float = 0.0) -> str:
    """Kurum demo kartı önerilerde görecek mi? Tek koşul benzerlik tabanı.

    Genç kartı kanıtsız, doğrulama bonusu 0: skor = 0.75 × benzerlik. Skor
    yalnızca sıralar, listeye girmeyi belirlemez.
    """
    skor = skor_hesapla(deger, dogrulama_bonus)
    baslik = f"İki demo kartın benzerliği {deger:.3f}, skoru {skor:.3f}"
    if not benzerlik_yeterli_mi(deger):
        return f"{baslik} — UYARI: alt sınırın ({BENZERLIK_ALT_SINIRI}) altında, öneri çıkmaz"
    return f"{baslik} — kurum bu kartı önerilerde görecek"


def gencin_karti(kullanici_id) -> YetenekKarti:
    return YetenekKarti(
        kullanici_id=kullanici_id,
        rol_alani="backend geliştirici",
        deneyim_seviyesi="orta",
        sektor_ilgi_alani=["sivil toplum", "eğitim"],
        araclar_teknolojiler=["Python", "FastAPI", "PostgreSQL"],
        # Çıktıların kanıtı yok: Doğrulama ekranı da denenebilsin.
        kanit_bekleyen=True,
        somut_ciktilar=[
            SomutCikti(
                baslik="Mahalle kütüphanesi ödünç takip sistemi",
                aciklama="400 kitabı ve 120 üyeyi takip eden web uygulaması; "
                "gecikmiş ödünçleri gönüllülere listeliyor.",
            ),
            SomutCikti(
                baslik="Dernek bağış ve dağıtım kayıt sistemi",
                aciklama="Bir yardım derneğinin ayni bağışlarını ve ailelere yapılan "
                "dağıtımları kaydeden, aylık raporu tek tıkla çıkaran web uygulaması.",
            ),
        ],
    )


# Kayıt formunun alanları (docs/agent-specs.md § 1); eşleştirme yalnızca
# şehir, çalışma modeli ve müsaitliğe bakar, gerisi profilde görünür.
GENC_PROFILI = GencKayitProfili(
    sehir="İstanbul",
    calisma_modelleri=["hibrit", "uzaktan"],
    kariyer_durumu="ogrenci",
    musaitlikler=["yarim_zamanli", "proje_bazli"],
    okul="Marmara Üniversitesi",
    bolum="Bilgisayar Mühendisliği",
    sinif=3,
    github_url="https://github.com/ornek-demo",
)


def kurumun_karti(kurum_id) -> IhtiyacKarti:
    return IhtiyacKarti(
        kurum_id=kurum_id,
        problem_tanimi="Kooperatifin gıda bankasında bağış ve dağıtım kayıtları kâğıt "
        "defterde tutuluyor; hangi aileye ne zaman ne verildiği takip edilemiyor. "
        "Bağışları ve ailelere yapılan dağıtımları kaydeden, aylık raporu kendisi "
        "çıkaran basit bir web uygulaması gerekiyor.",
        basari_kriteri="3 ay içinde tüm bağış ve dağıtımlar dijital kayıtta; aylık "
        "rapor 1 gün yerine 10 dakikada çıkıyor.",
        kisitlar="Bütçe yok; kayıtları giren gönüllüler teknik değil, arayüz sade olmalı.",
        sehir_tercihi="İstanbul",
        calisma_modeli="hibrit",
        musaitlik_tercihi="yarim_zamanli",
    )


def girisimin_karti(kurum_id) -> FirmaKarti:
    return FirmaKarti(
        kurum_id=kurum_id,
        ne_yapiyoruz="Perakendeciler için satış verisinden şube bazında günlük talep "
        "tahmini yapan ve taze ürün siparişini öneren bir yazılım.",
        yetkinlikler=[
            "talep tahmini",
            "taze ürün fire azaltma",
            "satış verisi analizi",
            "makine öğrenmesi",
        ],
        onceki_isler="İki bölgesel markette 3 aylık pilot; meyve-sebze firesi %15 azaldı.",
        aranan_isbirligi="Pilot uygulama için şube satış verisini paylaşabilecek bir "
        "market zinciri.",
        isbirligi_turleri=["pilot"],
    )


def kurumsalin_ilani(kurum_id) -> IhtiyacKarti:
    return IhtiyacKarti(
        kurum_id=kurum_id,
        aranan="firma",
        aranan_firma_turleri=["girisim"],
        isbirligi_turu="pilot",
        problem_tanimi="Şubelerde meyve-sebze fire oranı yüksek: sipariş miktarları "
        "şube müdürünün tahminine bırakılıyor, satış verisinden tahmin yapılmıyor. "
        "Taze ürün siparişini veriye dayandıracak bir ortak arıyoruz.",
        basari_kriteri="6 ay içinde pilot şubelerde meyve-sebze firesi %20 azalsın.",
        kisitlar="Pilot 5 şubede; şube verisi yalnızca anonim ve toplu paylaşılabilir.",
    )


async def _hesap_var_mi(oturum, email: str) -> bool:
    return (
        await oturum.scalar(select(Hesap.id).where(Hesap.email == eposta_normalize(email)))
    ) is not None


async def demo_ac(sifre: str) -> list[Sonuc]:
    sonuclar: list[Sonuc] = []
    async with get_sessionmaker()() as oturum:
        # Genç
        if await _hesap_var_mi(oturum, GENC_EPOSTA):
            sonuclar.append(Sonuc(GENC_EPOSTA, ROL_GENC, yeni=False))
            genc_karti = None
        else:
            hesap = await hesap_olustur(
                oturum,
                email=GENC_EPOSTA,
                sifre=sifre,
                rol=ROL_GENC,
                ad=GENC_ADI,
                genc_profili=GENC_PROFILI,
                kvkk_onay=True,
                eposta_dogrulandi=True,
            )
            kullanici = await oturum.scalar(select(Kullanici).where(Kullanici.hesap_id == hesap.id))
            genc_karti = gencin_karti(kullanici.id)
            oturum.add(genc_karti)
            await oturum.commit()
            gomuldu = await embedding_servisi.embedding_hesapla(oturum, genc_karti)
            sonuclar.append(
                Sonuc(GENC_EPOSTA, ROL_GENC, yeni=True, not_=_kart_notu("yetenek", gomuldu))
            )

        # Kurum
        if await _hesap_var_mi(oturum, KURUM_EPOSTA):
            sonuclar.append(Sonuc(KURUM_EPOSTA, ROL_KURUM, yeni=False))
            ihtiyac = None
        else:
            # Firma kayıt formunun alanları dolu (docs/kararlar.md
            # F2, F20): demo hesabı "Profilinizi tamamlayın" bandı görmesin.
            hesap = await hesap_olustur(
                oturum,
                email=KURUM_EPOSTA,
                sifre=sifre,
                rol=ROL_KURUM,
                ad=KURUM_ADI,
                firma_profili=KURUM_PROFILI,
                kvkk_onay=True,
                eposta_dogrulandi=True,
            )
            kurum = await oturum.scalar(select(Kurum).where(Kurum.hesap_id == hesap.id))
            ihtiyac = kurumun_karti(kurum.id)
            oturum.add(ihtiyac)
            await oturum.commit()
            gomuldu = await embedding_servisi.embedding_hesapla(oturum, ihtiyac)
            sonuclar.append(
                Sonuc(KURUM_EPOSTA, ROL_KURUM, yeni=True, not_=_kart_notu("ihtiyaç", gomuldu))
            )

        # GİRVAK
        if await _hesap_var_mi(oturum, GIRVAK_EPOSTA):
            sonuclar.append(Sonuc(GIRVAK_EPOSTA, ROL_GIRVAK, yeni=False))
        else:
            await hesap_olustur(
                oturum,
                email=GIRVAK_EPOSTA,
                sifre=sifre,
                rol=ROL_GIRVAK,
                ad=None,
                eposta_dogrulandi=True,
            )
            sonuclar.append(Sonuc(GIRVAK_EPOSTA, ROL_GIRVAK, yeni=True))

        # Firma akışı: girişim (doğrulanmış, kartlı) ve kurumsal (ortak ilanı).
        firma_karti = None
        if await _hesap_var_mi(oturum, GIRISIM_EPOSTA):
            sonuclar.append(Sonuc(GIRISIM_EPOSTA, ROL_KURUM, yeni=False))
        else:
            hesap = await hesap_olustur(
                oturum,
                email=GIRISIM_EPOSTA,
                sifre=sifre,
                rol=ROL_KURUM,
                ad=GIRISIM_ADI,
                firma_profili=GIRISIM_PROFILI,
                kvkk_onay=True,
                eposta_dogrulandi=True,
            )
            kurum = await oturum.scalar(select(Kurum).where(Kurum.hesap_id == hesap.id))
            kurum.dogrulama_durumu = DOGRULANDI
            kurum.dogrulama_tarihi = dt.datetime.now(dt.UTC)
            firma_karti = girisimin_karti(kurum.id)
            oturum.add(firma_karti)
            await oturum.commit()
            firma_karti = await firma_servisi.kurumun_karti(oturum, kurum.id)
            gomuldu = await embedding_servisi.embedding_hesapla(oturum, firma_karti)
            sonuclar.append(
                Sonuc(GIRISIM_EPOSTA, ROL_KURUM, yeni=True, not_=_kart_notu("firma", gomuldu))
            )

        ortak_ilani = None
        if await _hesap_var_mi(oturum, KURUMSAL_EPOSTA):
            sonuclar.append(Sonuc(KURUMSAL_EPOSTA, ROL_KURUM, yeni=False))
        else:
            hesap = await hesap_olustur(
                oturum,
                email=KURUMSAL_EPOSTA,
                sifre=sifre,
                rol=ROL_KURUM,
                ad=KURUMSAL_ADI,
                firma_profili=KURUMSAL_PROFILI,
                kvkk_onay=True,
                eposta_dogrulandi=True,
            )
            kurum = await oturum.scalar(select(Kurum).where(Kurum.hesap_id == hesap.id))
            ortak_ilani = kurumsalin_ilani(kurum.id)
            oturum.add(ortak_ilani)
            await oturum.commit()
            gomuldu = await embedding_servisi.embedding_hesapla(oturum, ortak_ilani)
            sonuclar.append(
                Sonuc(
                    KURUMSAL_EPOSTA,
                    ROL_KURUM,
                    yeni=True,
                    not_=_kart_notu("ortak ilanı", gomuldu),
                )
            )

        if firma_karti is not None and ortak_ilani is not None:
            if firma_karti.embedding is not None and ortak_ilani.embedding is not None:
                print(
                    "Firma–firma: "
                    + oneri_durumu(
                        benzerlik(list(firma_karti.embedding), list(ortak_ilani.embedding)),
                        dogrulama_bonus=firma_bonusu(True, 0),
                    )
                )

        if genc_karti is not None and ihtiyac is not None:
            if genc_karti.embedding is not None and ihtiyac.embedding is not None:
                print(oneri_durumu(benzerlik(list(genc_karti.embedding), list(ihtiyac.embedding))))
    return sonuclar


def _kart_notu(tur: str, gomuldu: bool) -> str:
    if gomuldu:
        return f"{tur} kartı yazıldı"
    return f"{tur} kartı yazıldı ama embedding hesaplanamadı (Voyage?); eşleştirmeye girmez"


def main() -> None:
    sifre = sifreyi_dogrula(get_settings().demo_sifresi)
    for sonuc in asyncio.run(demo_ac(sifre)):
        durum = "açıldı" if sonuc.yeni else "zaten vardı, dokunulmadı"
        ek = f" — {sonuc.not_}" if sonuc.not_ else ""
        print(f"{sonuc.rol:7} {sonuc.email}: {durum}{ek}")
    print("Şifre: .env'deki DEMO_SIFRESI")


if __name__ == "__main__":
    main()
