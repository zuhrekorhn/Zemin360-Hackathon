"""GİRVAK paneli uçları (docs/canlilik.md § 7-8), gerçek veritabanında.

Dünya: test_sahiplik.py — E1 (kurum1 "Koop Bir" ↔ genc1 "Elif") `onerildi`,
E2 (kurum2 "Koop İki" ↔ genc2 "Can") `ilgileniliyor`. Yerel veritabanında
başka kayıtlar da olabilir: sayılar farkla, listeler bu dünyanın kayıtlarıyla
doğrulanır.
"""

import datetime as dt

from sqlalchemy import func, select

from app.api import canlilik as canlilik_api
from app.models.canlilik_olayi import CanlilikOlayi
from tests.test_sahiplik import durumlar, senaryo


def _simdi():
    return dt.datetime.now(dt.UTC)


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
