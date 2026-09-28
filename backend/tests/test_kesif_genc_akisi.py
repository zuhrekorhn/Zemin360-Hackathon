"""Keşif sohbetinin genç akışı eklemeleri (docs/plans/genc-akisi.md § 5.3-5.4).

- Kayıt formundaki bilgiler bağlam olarak gider ve sorulmaz.
- İş kalemi başına kanıt ve referans da sorulur (tek soruda), iş kalemine bağlanır.
"""

import asyncio
import uuid
from types import SimpleNamespace

from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.agents import sohbet_motoru as motor
from app.agents.kesif import (
    KESIF,
    TaslakCikarimi,
    _karar,
    profil_baglami,
)
from app.api.auth import hesap_olustur
from app.core.is_kalemi import birlesik_aciklama
from app.core.kimlik import token_uret
from app.core.metin import gecerli_eposta
from app.main import app
from app.models.kullanici import Kullanici
from app.models.somut_cikti import SomutCikti
from app.models.yetenek_karti import YetenekKarti
from tests.test_profil import HazirTaslakGrafigi, _embedding_sahte
from tests.veritabani import api_istemcisi, geri_alinan_oturum


def karar(durum: dict) -> dict:
    return asyncio.run(_karar(durum))


def taslak(**cikti) -> dict:
    return {
        "rol_alani": "backend geliştirici",
        "deneyim_seviyesi": "orta",
        "sektor_ilgi_alani": ["eğitim"],
        "araclar_teknolojiler": ["Python"],
        "somut_ciktilar": [{"baslik": "Kütüphane sistemi", **cikti}],
    }


# --- Profil bağlamı: form bilgileri tekrar sorulmaz -----------------------------------------


def _profil(**ek):
    temel = {
        "sehir": "İzmir",
        "calisma_modelleri": ["hibrit"],
        "musaitlikler": ["staj", "yarim_zamanli"],
        "kariyer_durumu": "ogrenci",
        "okul": "Ege Üniversitesi",
        "bolum": "Bilgisayar Mühendisliği",
    }
    return SimpleNamespace(**{**temel, **ek})


def test_profil_baglami_form_bilgilerini_tasir_ve_sorma_der():
    metin = profil_baglami(_profil())
    assert "SORMA" in metin
    for beklenen in ("İzmir", "Hibrit", "Staj", "Yarı zamanlı", "Öğrenci", "Ege Üniversitesi"):
        assert beklenen in metin


def test_bos_profilde_baglam_yok():
    bos = _profil(
        sehir=None,
        calisma_modelleri=[],
        musaitlikler=[],
        kariyer_durumu=None,
        okul=None,
        bolum=None,
    )
    assert profil_baglami(bos) is None


def test_baglam_cikarim_istemine_ayri_sistem_mesaji_olarak_girer():
    gorulen: list = []

    class Zincir:
        async def ainvoke(self, mesajlar):
            gorulen.extend(mesajlar)
            return TaslakCikarimi()

    cikar = motor._cikar_dugumu(KESIF, lambda: Zincir())
    asyncio.run(
        cikar(
            {
                "mesajlar": [HumanMessage(content="Bir kütüphane sistemi yaptım.")],
                "taslak": motor.bos_taslak(KESIF),
                "profil_baglami": "KULLANICININ PROFİLİ: Şehir: İzmir",
            }
        )
    )
    sistem = [m.content for m in gorulen if isinstance(m, SystemMessage)]
    assert sistem[0] == KESIF.sistem_talimati
    assert sistem[1] == "KULLANICININ PROFİLİ: Şehir: İzmir"


def test_form_alanini_soran_model_sorusu_kullanilmaz():
    """Model şehri sorsa bile (konusu zorunlu bir Keşif alanı değil) sabit soru gelir."""
    sonuc = karar(
        {
            "taslak": {**taslak(), "sektor_ilgi_alani": []},
            "takip_turu": 0,
            "fallback_indeksi": 0,
            "son_takip_sorusu": "Hangi şehirde yaşıyorsun?",
            "son_takip_konusu": "diger",
        }
    )
    assert "şehir" not in sonuc["sonraki_soru"].lower()
    assert sonuc["sonraki_soru"] == KESIF.yedek_sorular["sektor_ilgi_alani"]


def test_sabit_sorular_form_alanlarini_sormaz():
    sorular = " ".join(KESIF.yedek_sorular.values()).lower()
    for form_alani in ("şehir", "uzaktan", "hibrit", "tam zamanlı", "staj", "okul"):
        assert form_alani not in sorular


# --- Kanıt ve referans: iş kalemine bağlı, tek soruda ---------------------------------------


def test_kanit_ve_referans_rol_ve_sonuctan_sonra_sorulur():
    sonuc = karar(
        {
            "taslak": taslak(olculebilir_sonuc="400 kitap", kendi_rolu="hepsini ben yazdım"),
            "takip_turu": 0,
            "fallback_indeksi": 0,
        }
    )
    assert sonuc["sorulan_ekler"] == ["kanit:Kütüphane sistemi"]
    assert "link" in sonuc["sonraki_soru"] and "e-posta" in sonuc["sonraki_soru"]


def test_referansi_verilmis_kaleme_kanit_sorulmaz():
    sonuc = karar(
        {
            "taslak": taslak(
                olculebilir_sonuc="400 kitap",
                kendi_rolu="hepsini ben yazdım",
                referans_email="hoca@ornek.edu.tr",
            ),
            "takip_turu": 0,
            "fallback_indeksi": 0,
        }
    )
    assert sonuc["taslak_hazir"] is True


def test_birlesik_aciklama_eski_satirda_tekrar_etmez():
    """Bu alanlardan önceki satırlarda sonuç zaten açıklamanın içinde."""
    eski = "Ödünç takibi. 400 kitap takip ediliyor."
    assert birlesik_aciklama(eski, "400 kitap takip ediliyor.", None) == eski
    assert birlesik_aciklama("Ödünç takibi.", "400 kitap", "Backend'i ben yazdım") == (
        "Ödünç takibi. 400 kitap Backend'i ben yazdım"
    )
    assert birlesik_aciklama(None, None, None) is None


def test_gecerli_eposta_hosgorulu():
    assert gecerli_eposta(" Hoca@Ornek.edu.tr ") == "hoca@ornek.edu.tr"
    assert gecerli_eposta("hocamın maili") is None
    assert gecerli_eposta(None) is None


# --- Onay: yeni alanlar ve referans iş kalemine bağlanır (gerçek veritabanı) ----------------


def test_onay_is_kalemi_alanlarini_ve_referansi_kaydeder(monkeypatch):
    _embedding_sahte(monkeypatch)

    async def senaryo():
        async with geri_alinan_oturum() as oturum, api_istemcisi(oturum) as istemci:
            hesap = await hesap_olustur(
                oturum,
                email=f"test-{uuid.uuid4().hex[:8]}@ornek.com",
                sifre="yeterince-uzun",
                rol="genc",
                ad="Elif",
            )
            kullanici = await oturum.scalar(select(Kullanici).where(Kullanici.hesap_id == hesap.id))
            kullanici.sehir = "İzmir"
            await oturum.commit()
            baslik = {"Authorization": f"Bearer {token_uret(hesap.id, 'genc')}"}
            app.state.kesif_grafigi = HazirTaslakGrafigi(
                hesap.id,
                {
                    **taslak(
                        is_turu="gonulluluk",
                        olculebilir_sonuc="400 kitap",
                        kendi_rolu="backend'i ben yazdım",
                        referans_email="Hoca@Ornek.edu.tr",
                    ),
                    "sertifikalar": ["AWS Cloud Practitioner"],
                    "diller": ["İngilizce (B2)"],
                },
            )
            try:
                yanit = await istemci.post(
                    "/kesif/kart/onayla",
                    headers=baslik,
                    json={"oturum_id": str(uuid.uuid4())},
                )
            finally:
                del app.state.kesif_grafigi

            assert yanit.status_code == 201
            govde = yanit.json()
            assert govde["sertifikalar"] == ["AWS Cloud Practitioner"]
            assert govde["diller"] == ["İngilizce (B2)"]
            cikti_yaniti = govde["somut_ciktilar"][0]
            assert cikti_yaniti["is_turu"] == "gonulluluk"
            assert cikti_yaniti["kendi_rolu"] == "backend'i ben yazdım"
            assert "Hoca@" not in yanit.text  # referans e-postası kart görünümünde yok

            kart = await oturum.scalar(
                select(YetenekKarti)
                .options(
                    selectinload(YetenekKarti.somut_ciktilar).selectinload(
                        SomutCikti.referans_istekleri
                    )
                )
                .where(YetenekKarti.id == uuid.UUID(govde["id"]))
            )
            referanslar = kart.somut_ciktilar[0].referans_istekleri
            assert [r.referans_email for r in referanslar] == ["hoca@ornek.edu.tr"]

    asyncio.run(senaryo())
