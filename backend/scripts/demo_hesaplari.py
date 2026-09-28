"""Demo hesaplarını açar (docs/faz-b-kimlik-ve-dongu.md § 9).

Üç hesap: genç, kurum, GİRVAK. Şifre `.env`'deki DEMO_SIFRESI'nden; repoda
şifre yok. Genç hesabına bir yetenek kartı, kuruma bir ihtiyaç kartı yazılır.
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
import math
import sys
from dataclasses import dataclass

from sqlalchemy import select

from app.agents.eslestirme import (
    BENZERLIK_ALT_SINIRI,
    SKOR_ESIGI,
    benzerlik_yeterli_mi,
    skor_hesapla,
)
from app.api import ihtiyac_kartlari, yetenek_kartlari
from app.api.auth import hesap_olustur
from app.core.config import get_settings
from app.core.kimlik import SIFRE_EN_AZ
from app.core.metin import eposta_normalize
from app.db.session import get_sessionmaker
from app.models.hesap import ROL_GENC, ROL_GIRVAK, ROL_KURUM, Hesap
from app.models.ihtiyac_karti import IhtiyacKarti
from app.models.kullanici import Kullanici
from app.models.kurum import Kurum
from app.models.somut_cikti import SomutCikti
from app.models.yetenek_karti import YetenekKarti

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ALAN = "demo.zemin360.example"
GENC_EPOSTA = f"genc@{ALAN}"
KURUM_EPOSTA = f"kurum@{ALAN}"
GIRVAK_EPOSTA = f"girvak@{ALAN}"

GENC_ADI = "Elif Demir"
KURUM_ADI = "Moda Dayanışma Kooperatifi"


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


def oneri_durumu(deger: float) -> str:
    """Kurum demo kartı önerilerde görecek mi? İki sınırın ikisi de geçilmeli.

    Kart kanıtsız, doğrulama bonusu 0: skor = 0.75 × benzerlik. Alt sınırı
    (0.45) geçip skor eşiğine (0.40) takılan kart da listede görünmez.
    """
    skor = skor_hesapla(deger, 0.0)
    baslik = f"İki demo kartın benzerliği {deger:.3f}, skoru {skor:.3f}"
    if not benzerlik_yeterli_mi(deger):
        return f"{baslik} — UYARI: alt sınırın ({BENZERLIK_ALT_SINIRI}) altında, öneri çıkmaz"
    if skor < SKOR_ESIGI:
        return f"{baslik} — UYARI: skor eşiğinin ({SKOR_ESIGI}) altında, öneri çıkmaz"
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
                oturum, email=GENC_EPOSTA, sifre=sifre, rol=ROL_GENC, ad=GENC_ADI
            )
            kullanici = await oturum.scalar(select(Kullanici).where(Kullanici.hesap_id == hesap.id))
            kullanici.sehir = "İstanbul"
            kullanici.calisma_modelleri = ["hibrit", "uzaktan"]
            kullanici.musaitlikler = ["yarim_zamanli"]
            genc_karti = gencin_karti(kullanici.id)
            oturum.add(genc_karti)
            await oturum.commit()
            gomuldu = await yetenek_kartlari.embedding_hesapla(oturum, genc_karti)
            sonuclar.append(
                Sonuc(GENC_EPOSTA, ROL_GENC, yeni=True, not_=_kart_notu("yetenek", gomuldu))
            )

        # Kurum
        if await _hesap_var_mi(oturum, KURUM_EPOSTA):
            sonuclar.append(Sonuc(KURUM_EPOSTA, ROL_KURUM, yeni=False))
            ihtiyac = None
        else:
            hesap = await hesap_olustur(
                oturum, email=KURUM_EPOSTA, sifre=sifre, rol=ROL_KURUM, ad=KURUM_ADI
            )
            kurum = await oturum.scalar(select(Kurum).where(Kurum.hesap_id == hesap.id))
            kurum.sektor = "sivil toplum"
            kurum.sehir = "İstanbul"
            ihtiyac = kurumun_karti(kurum.id)
            oturum.add(ihtiyac)
            await oturum.commit()
            gomuldu = await ihtiyac_kartlari.embedding_hesapla(oturum, ihtiyac)
            sonuclar.append(
                Sonuc(KURUM_EPOSTA, ROL_KURUM, yeni=True, not_=_kart_notu("ihtiyaç", gomuldu))
            )

        # GİRVAK
        if await _hesap_var_mi(oturum, GIRVAK_EPOSTA):
            sonuclar.append(Sonuc(GIRVAK_EPOSTA, ROL_GIRVAK, yeni=False))
        else:
            await hesap_olustur(oturum, email=GIRVAK_EPOSTA, sifre=sifre, rol=ROL_GIRVAK, ad=None)
            sonuclar.append(Sonuc(GIRVAK_EPOSTA, ROL_GIRVAK, yeni=True))

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
