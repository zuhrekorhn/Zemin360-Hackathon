"""Durum özeti (docs/takip.md § 5) — kesilebilir iş.

Sabitlenenler: özet girdisi yalnızca yapılandırılmış bilgi (e-posta yok);
yalnızca plan onaylanınca ve adım tamamlanınca sıraya konur; özet çökerse
döngü etkilenmez.
"""

import asyncio
import contextlib
import datetime as dt

import pytest

from app.agents import takip
from app.api import takip as takip_api
from tests.takip_dunyasi import isbirligi_ac
from tests.test_sahiplik import senaryo
from tests.test_takip_isaret import aktif_isbirligi

# conftest fixture'ı modül özniteliğini sahtesiyle değiştirmeden önce yakalanıyor.
GERCEK_OZET_ISI = takip_api.ozeti_arka_planda_yaz

BUGUN = dt.date(2026, 10, 10)


def test_ozet_girdisi_yapilandirilmis_ve_epostasiz():
    girdi = takip.ozet_girdisi(
        durum="aktif",
        genc_adi="Elif",
        kurum_adi="Koop Bir",
        adimlar=[
            takip.AdimDurumu("Kayıtları incele", dt.date(2026, 10, 1), True, True),
            takip.AdimDurumu("Kayıt ekranı", dt.date(2026, 10, 7), True, False),
            takip.AdimDurumu("Aylık rapor", dt.date(2026, 11, 1), False, False),
        ],
        son_hareket=dt.date(2026, 10, 6),
        bugun=BUGUN,
    )
    assert "3 adımın 1 tanesi iki tarafça tamamlandı" in girdi
    assert "Kayıt ekranı: Elif tamamlandı dedi; Koop Bir tarafının onayı bekleniyor" in girdi
    assert "hedef tarihi 3 gün geçti (gecikmiş)" in girdi
    assert "Aylık rapor: sürüyor." in girdi  # hedefi gelecekte, gecikme yok
    assert "Son hareketten bu yana 4 gün geçti." in girdi
    assert "@" not in girdi


def _zincir(monkeypatch, metin):
    class Sahte:
        async def ainvoke(self, _girdi):
            return metin

    takip._ozet_zinciri.cache_clear()
    monkeypatch.setattr(takip, "_ozet_zinciri", lambda: Sahte())


def test_ozet_bosluklari_toplar(monkeypatch):
    _zincir(monkeypatch, "  İki adım tamamlandı.\n  Rapor adımı sürüyor.  ")
    assert asyncio.run(takip.durum_ozeti_yaz("x")) == "İki adım tamamlandı. Rapor adımı sürüyor."


@pytest.mark.parametrize("metin", ["", "   ", "a" * (takip.OZET_EN_UZUN + 1)])
def test_bos_ya_da_asiri_uzun_ozet_kullanilmaz(monkeypatch, metin):
    _zincir(monkeypatch, metin)
    assert asyncio.run(takip.durum_ozeti_yaz("x")) is None


# --- Tetikleyiciler ---------------------------------------------------------------------------


def test_ozet_yalnizca_plan_onayinda_ve_adim_tamamlaninca_siraya_konur(ozet_arka_plan_isi_yok):
    async def adimlar(istemci, d):
        isb = await isbirligi_ac(d, adimlar=1)
        yol = f"/isbirligi/{isb.id}"
        await istemci.post(f"{yol}/plan-onayla", headers=d.genc1.baslik)
        assert ozet_arka_plan_isi_yok == []  # tek onay: plan henüz yürürlükte değil
        await istemci.post(f"{yol}/plan-onayla", headers=d.kurum1.baslik)
        assert ozet_arka_plan_isi_yok == [isb.id]

        adim = f"{yol}/milestone/{isb.milestonelar[0].id}"
        await istemci.post(f"{adim}/isaretle", headers=d.genc1.baslik)
        assert len(ozet_arka_plan_isi_yok) == 1  # tek işaret: adım tamamlanmadı
        await istemci.post(f"{adim}/isaretle", headers=d.kurum1.baslik)
        assert ozet_arka_plan_isi_yok == [isb.id, isb.id]

    senaryo(adimlar)


# --- Arka plan işi --------------------------------------------------------------------------


def _ayni_oturum(monkeypatch, oturum):
    @contextlib.asynccontextmanager
    async def fabrika():
        yield oturum

    monkeypatch.setattr(takip_api, "get_sessionmaker", lambda: fabrika)


def test_arka_plan_isi_ozeti_yazar(monkeypatch):
    girdiler = []

    async def yaz(girdi):
        girdiler.append(girdi)
        return "Plan onaylandı, iki adım sürüyor."

    monkeypatch.setattr(takip, "durum_ozeti_yaz", yaz)

    async def adimlar(istemci, d):
        isb = await aktif_isbirligi(d, adimlar=2)
        _ayni_oturum(monkeypatch, d.oturum)
        await GERCEK_OZET_ISI(isb.id)
        govde = (await istemci.get(f"/isbirligi/{isb.id}", headers=d.genc1.baslik)).json()
        assert govde["durum_ozeti"] == "Plan onaylandı, iki adım sürüyor."
        assert govde["ozet_tarihi"] is not None
        assert "Elif" in girdiler[0] and "Koop Bir" in girdiler[0]

    senaryo(adimlar)


def test_ozet_cokerse_dongu_etkilenmez(monkeypatch):
    """Kesilebilirlik: özet hata verse de iş birliği tamamlanır, özet boş kalır."""

    async def coker(_girdi):
        raise RuntimeError("LLM yok")

    monkeypatch.setattr(takip, "durum_ozeti_yaz", coker)

    async def adimlar(istemci, d):
        isb = await aktif_isbirligi(d, adimlar=1)
        _ayni_oturum(monkeypatch, d.oturum)
        await GERCEK_OZET_ISI(isb.id)  # hata yutulur

        adim = f"/isbirligi/{isb.id}/milestone/{isb.milestonelar[0].id}"
        for kisi in (d.genc1, d.kurum1):
            yanit = await istemci.post(f"{adim}/isaretle", headers=kisi.baslik)
            assert yanit.status_code == 200
        govde = yanit.json()
        assert govde["durum"] == "tamamlandi"
        assert govde["durum_ozeti"] is None

    senaryo(adimlar)
