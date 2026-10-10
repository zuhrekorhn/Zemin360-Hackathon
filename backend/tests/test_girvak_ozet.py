"""GİRVAK özeti ve iş birlikleri listesi (docs/canlilik.md § 7), gerçek veritabanında.

Dünya: test_sahiplik.py. Yerel veritabanında başka kayıtlar da olabilir: sayılar
FARKLA, listeler bu dünyanın kayıtlarıyla doğrulanır.
"""

import datetime as dt

from app.models.guven_skoru import GuvenSkoru
from app.models.ihtiyac_karti import IhtiyacKarti
from app.models.inceleme_isareti import TUR_AD_DEGISIKLIGI, IncelemeIsareti
from app.models.yetenek_karti import YetenekKarti
from tests.takip_dunyasi import isbirligi_ac
from tests.test_firma_eslestirme import gerekce_sahte as gerekce_sahte  # noqa: F401
from tests.test_firma_isbirligi import _karsilikli
from tests.test_sahiplik import _hesap, durumlar, senaryo
from tests.test_takip_isaret import aktif_isbirligi


async def _ozet(istemci, d):
    yanit = await istemci.get("/girvak/ozet", headers=d.girvak.baslik)
    assert yanit.status_code == 200, yanit.text
    return yanit.json()


def test_ozet_sayilari_elle_kurulan_veriyle_birebir():
    async def adimlar(istemci, d):
        once = await _ozet(istemci, d)

        # 01 Keşif: kartı olan yeni bir genç.
        kartli = await _hesap(d.oturum, "genc", "Kartlı")
        d.oturum.add(
            YetenekKarti(kullanici_id=kartli.profil.id, rol_alani="r", deneyim_seviyesi="orta")
        )
        # 02 Doğruluk: değerlendirilmiş bir çalışma + açık bir inceleme.
        d.oturum.add(
            GuvenSkoru(somut_cikti_id=d.C1.id, degerlendirme_tarihi=dt.datetime.now(dt.UTC))
        )
        d.oturum.add(
            IncelemeIsareti(tur=TUR_AD_DEGISIKLIGI, kullanici_id=d.genc1.profil.id, ayrinti={})
        )
        # 05 Tanım: biri ölçülebilir, biri ölçüsüz iki ihtiyaç.
        kurum = await _hesap(d.oturum, "kurum", "Yeni Koop")
        d.oturum.add(
            IhtiyacKarti(
                kurum_id=kurum.profil.id,
                problem_tanimi="p",
                basari_olcutu={"hedef_deger": "yarısı"},
            )
        )
        d.oturum.add(
            IhtiyacKarti(
                kurum_id=kurum.profil.id,
                problem_tanimi="q",
                basari_olcutu={"olcum_bilinmiyor": True},
            )
        )
        # 03 ve 06: kabul edilmiş eşleşme, tamamlanmış iş birliği.
        isb = await aktif_isbirligi(d, adimlar=1)
        isb.durum = "tamamlandi"
        await d.oturum.commit()

        sonra = await _ozet(istemci, d)
        assert sonra["kesif"]["kayitli_genc"] == once["kesif"]["kayitli_genc"] + 1
        assert sonra["kesif"]["kart_olusturan_genc"] == once["kesif"]["kart_olusturan_genc"] + 1
        assert (
            sonra["dogruluk"]["degerlendirilen_calisma"]
            == once["dogruluk"]["degerlendirilen_calisma"] + 1
        )
        assert sonra["dogruluk"]["bekleyen_inceleme"] == once["dogruluk"]["bekleyen_inceleme"] + 1
        assert sonra["tanim"]["ihtiyac"] == once["tanim"]["ihtiyac"] + 2
        assert sonra["tanim"]["olculebilir_ihtiyac"] == once["tanim"]["olculebilir_ihtiyac"] + 1
        assert sonra["eslesme"]["karsilikli_ilgi"] == once["eslesme"]["karsilikli_ilgi"] + 1
        assert sonra["takip"]["isbirligi"] == once["takip"]["isbirligi"] + 1
        assert sonra["takip"]["tamamlanan"] == once["takip"]["tamamlanan"] + 1

    senaryo(adimlar)


def test_takilan_surec_ve_hatirlatma_sayilir():
    async def adimlar(istemci, d):
        once = await _ozet(istemci, d)
        d.E1.son_aktivite_tarihi = dt.datetime.now(dt.UTC) - dt.timedelta(days=8)  # önerildi, 7 gün
        await d.oturum.commit()
        sonra = await _ozet(istemci, d)
        assert sonra["ag"]["takilan_surec"] == once["ag"]["takilan_surec"] + 1
        # Hatırlatma sayısı yalnızca tarama sonrası değişir; okuma bir şey yazmaz.
        assert sonra["ag"]["hatirlatma_30_gun"] == once["ag"]["hatirlatma_30_gun"]

    senaryo(adimlar)


def test_isbirlikleri_listesi_taraflar_ve_ilerleme_eposta_yok():
    async def adimlar(istemci, d):
        isb = await isbirligi_ac(d, adimlar=2)
        yanit = await istemci.get("/girvak/isbirlikleri", headers=d.girvak.baslik)
        assert yanit.status_code == 200, yanit.text
        satir = next(s for s in yanit.json() if s["isbirligi_id"] == str(isb.id))
        assert satir["aday_turu"] == "genc"
        assert satir["aday_adi"] == "Elif" and satir["kurum_adi"] == "Koop Bir"
        assert satir["ilerleme"]["toplam"] == 2 and satir["ilerleme"]["tamamlanan"] == 0
        assert satir["durum"] in {"plan_bekliyor", "aktif"}
        # Gizlilik: yanıtın hiçbir yerinde e-posta ya da iletişim alanı yok.
        assert "@" not in yanit.text
        assert "iletisim" not in yanit.text

    senaryo(adimlar)


def test_firma_firma_isbirligi_satirda_firma_adiyla():
    """Aday firmanın kurumu yüklü olmalı (lazy yükleme patlıyordu)."""

    async def adimlar(istemci, d):
        aday, ilan, eid, isb = await _karsilikli(istemci, d)
        yanit = await istemci.get("/girvak/isbirlikleri", headers=d.girvak.baslik)
        assert yanit.status_code == 200, yanit.text
        satir = next(s for s in yanit.json() if s["isbirligi_id"] == isb)
        assert satir["aday_turu"] == "firma"
        assert satir["rol_alani"] is None
        assert "@" not in yanit.text

    senaryo(adimlar)


def test_yetki():
    async def adimlar(istemci, d):
        for yol in ("/girvak/ozet", "/girvak/isbirlikleri"):
            await durumlar(
                istemci, "GET", yol, {None: 401, d.genc1: 403, d.kurum1: 403, d.girvak: 200}
            )

    senaryo(adimlar)
