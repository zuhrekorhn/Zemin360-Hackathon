"""GİRVAK paneli uçları (docs/canlilik.md § 7-8), gerçek veritabanında.

Dünya: test_sahiplik.py — E1 (kurum1 "Koop Bir" ↔ genc1 "Elif") `onerildi`,
E2 (kurum2 "Koop İki" ↔ genc2 "Can") `ilgileniliyor`. Yerel veritabanında
başka kayıtlar da olabilir: sayılar farkla, listeler bu dünyanın kayıtlarıyla
doğrulanır.
"""

import datetime as dt

from sqlalchemy import func, select

from app.api import canlilik as canlilik_api
from app.core.program import HEDEFLER
from app.models.canlilik_olayi import CanlilikOlayi
from app.models.ihtiyac_karti import IhtiyacKarti
from app.models.yetenek_karti import YetenekKarti
from tests.test_sahiplik import _hesap, durumlar, senaryo
from tests.test_takip_isaret import aktif_isbirligi


def _simdi():
    return dt.datetime.now(dt.UTC)


def test_program_hedefleri_iki_parcali_etiket_ve_olcum():
    async def adimlar(istemci, d):
        once = {
            h["anahtar"]: h
            for h in (await istemci.get("/girvak/sayilar", headers=d.girvak.baslik)).json()[
                "hedefler"
            ]
        }
        assert [h.anahtar for h in HEDEFLER] == ["basvuru", "kurum", "eslesme", "pilot"]
        assert [once[h.anahtar]["hedef"] for h in HEDEFLER] == [80, 20, 10, 5]
        assert once["basvuru"]["program_adi"] == "startup başvurusu"
        assert once["basvuru"]["olcum"] == "yetenek kartı oluşturan genç"

        # Kartı olmayan genç başvuru sayılmaz; kartı olan sayılır (gencin tek
        # kartı var: yetenek_karti.kullanici_id tekil).
        kartsiz = await _hesap(d.oturum, "genc", "Kartsız")
        kartli = await _hesap(d.oturum, "genc", "Kartlı")
        d.oturum.add(
            YetenekKarti(kullanici_id=kartli.profil.id, rol_alani="r", deneyim_seviyesi="orta")
        )
        # İhtiyaç kartı olan kurum sayılır.
        kurum = await _hesap(d.oturum, "kurum", "Yeni Koop")
        d.oturum.add(IhtiyacKarti(kurum_id=kurum.profil.id, problem_tanimi="p"))
        # Pilot: tamamlanmış iş birliği; eşleşme: kabul edilmiş.
        isb = await aktif_isbirligi(d, adimlar=1)
        isb.durum = "tamamlandi"
        await d.oturum.commit()
        assert kartsiz.profil.id  # kullanıldı

        sonra = {
            h["anahtar"]: h["sayi"]
            for h in (await istemci.get("/girvak/sayilar", headers=d.girvak.baslik)).json()[
                "hedefler"
            ]
        }
        assert sonra["basvuru"] == once["basvuru"]["sayi"] + 1
        assert sonra["kurum"] == once["kurum"]["sayi"] + 1
        assert sonra["eslesme"] == once["eslesme"]["sayi"] + 1  # E1 kabul_edildi
        assert sonra["pilot"] == once["pilot"]["sayi"] + 1

    senaryo(adimlar)


def test_pasifler_okuma_aninda_hicbir_sey_yazmaz():
    async def adimlar(istemci, d):
        d.E1.son_aktivite_tarihi = _simdi() - dt.timedelta(days=8)
        d.E2.son_aktivite_tarihi = _simdi() - dt.timedelta(days=11)
        await d.oturum.commit()
        olay_sayisi = await d.oturum.scalar(select(func.count()).select_from(CanlilikOlayi))

        yanit = await istemci.get("/canlilik/pasifler", headers=d.girvak.baslik)
        assert yanit.status_code == 200
        bizim = [p for p in yanit.json() if p["eslesme_id"] in {str(d.E1.id), str(d.E2.id)}]
        # En uzun süredir hareketsiz olan önce; iki alıcı tek satırda.
        assert [(p["tur"], p["gun"], sorted(p["alicilar"])) for p in bizim] == [
            ("ilgi_yanitsiz_2", 11, ["genc", "kurum"]),
            ("oneri_bekliyor", 8, ["kurum"]),
        ]
        assert bizim[0]["genc_adi"] == "Can" and bizim[0]["kurum_adi"] == "Koop İki"
        assert bizim[0]["son_hatirlatma"] is None
        assert "@" not in yanit.text
        assert (
            await d.oturum.scalar(select(func.count()).select_from(CanlilikOlayi))
        ) == olay_sayisi

        # Tarama sonrası son hatırlatma tarihi dolar.
        await canlilik_api.tarama_yap(d.oturum)
        sonra = {
            p["eslesme_id"]: p
            for p in (await istemci.get("/canlilik/pasifler", headers=d.girvak.baslik)).json()
        }
        assert sonra[str(d.E2.id)]["son_hatirlatma"] is not None

    senaryo(adimlar)


def test_son_olaylar_alici_adiyla():
    async def adimlar(istemci, d):
        d.E2.son_aktivite_tarihi = _simdi() - dt.timedelta(days=4)
        await d.oturum.commit()
        await canlilik_api.tarama_yap(d.oturum)
        liste = (await istemci.get("/canlilik/olaylar", headers=d.girvak.baslik)).json()
        bizim = [o for o in liste if o["eslesme_id"] == str(d.E2.id)]
        assert [(o["tur"], o["alici_adi"], o["alici_rol"]) for o in bizim] == [
            ("ilgi_yanitsiz_1", "Can", "genc")
        ]
        assert "Koop İki" in bizim[0]["mesaj_metni"]
        tek = await istemci.get("/canlilik/olaylar?limit=1", headers=d.girvak.baslik)
        assert len(tek.json()) == 1

    senaryo(adimlar)


def test_yetki():
    async def adimlar(istemci, d):
        for yol in ("/canlilik/pasifler", "/canlilik/olaylar"):
            await durumlar(
                istemci, "GET", yol, {None: 401, d.genc1: 403, d.kurum1: 403, d.girvak: 200}
            )

    senaryo(adimlar)
