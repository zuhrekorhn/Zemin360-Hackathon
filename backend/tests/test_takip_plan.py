"""Takip Ajanı — plan önerisi (docs/faz-c-takip.md § 4).

Saf kısım (kural, istem girdileri, tarih) DB'siz; uç nokta ve arka plan işi
gerçek veritabanında, geri alınan işlemde. LLM sahtesiyle değiştiriliyor.
"""

import asyncio
import contextlib
import datetime as dt
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.agents import takip
from app.api import takip as takip_api
from app.models.isbirligi import Isbirligi
from tests.takip_dunyasi import (
    BASLANGIC,
    ORNEK_PLAN,
    bildirimleri,
    isbirligi_ac,
    sahte_plan,
)
from tests.test_sahiplik import durumlar, senaryo

A = takip.AdimOnerisi
# Gerçek arka plan işi: conftest'in fixture'ı modül özniteliğini sahtesiyle
# değiştirmeden önce, içe aktarma anında yakalanıyor.
GERCEK_IS = takip_api.plani_arka_planda_oner

# --- Kural ve girdiler (saf) --------------------------------------------------------------


def _plan(*haftalar, baslik="Adım", aciklama="Tamam sayılır."):
    return takip.PlanOnerisi(
        adimlar=[A(baslik=baslik, aciklama=aciklama, hafta=h) for h in haftalar]
    )


@pytest.mark.parametrize(
    "plan,gecerli",
    [
        (_plan(1, 3, 6), True),
        (_plan(1, 2, 3, 4, 5), True),
        (_plan(2, 12, 12 - 1), False),  # artmıyor
        (_plan(1, 3), False),  # 3'ten az
        (_plan(1, 2, 3, 4, 5, 6), False),  # 5'ten fazla
        (_plan(0, 2, 4), False),  # hafta 1'den küçük
        (_plan(2, 6, 13), False),  # 12'den büyük
        (_plan(1, 1, 2), False),  # eşit hafta: kesin artan değil
        (_plan(1, 2, 3, baslik="  "), False),
        (_plan(1, 2, 3, aciklama=""), False),
    ],
)
def test_plan_kurali(plan, gecerli):
    assert takip.plan_gecerli_mi(plan) is gecerli


def test_hedef_tarihi_baslangictan_hafta_sayar():
    assert takip.hedef_tarihi(dt.date(2026, 9, 29), 2) == dt.date(2026, 10, 13)


def test_istem_girdileri_eposta_tasimaz():
    ihtiyac = SimpleNamespace(
        problem_tanimi="Bağışlar kâğıtta",
        basari_kriteri="Rapor 10 dakikada",
        kisitlar=None,
        musaitlik_tercihi="yarim_zamanli",
        calisma_modeli="hibrit",
    )
    kart = SimpleNamespace(
        rol_alani="backend geliştirici",
        deneyim_seviyesi="orta",
        araclar_teknolojiler=["Python"],
        somut_ciktilar=[SimpleNamespace(baslik="Kütüphane sistemi")],
        kullanici=SimpleNamespace(email="elif@ornek.com"),
    )
    girdiler = takip.plan_girdileri(ihtiyac, kart, "Koop")
    assert "elif@ornek.com" not in str(girdiler)
    assert girdiler["musaitlik"] == "Yarı zamanlı"
    assert girdiler["calisma_modeli"] == "Hibrit"
    assert girdiler["ciktilar"] == "Kütüphane sistemi"


def test_kurala_uymayan_cikti_bir_kez_duzeltme_notuyla_yeniden_istenir(monkeypatch):
    istenenler = []
    yanitlar = [_plan(1, 3), _plan(1, 3, 6)]

    async def cagir(girdiler):
        istenenler.append(girdiler["ek_not"])
        return yanitlar.pop(0)

    monkeypatch.setattr(takip, "_plan_cagir", cagir)
    adimlar = asyncio.run(takip.plan_oner(SimpleNamespace(**_ihtiyac()), _kart(), "Koop"))
    assert [a.hafta for a in adimlar] == [1, 3, 6]
    assert istenenler == ["", takip.DUZELTME_NOTU]


def test_iki_kez_kurala_uymazsa_plan_bos_kalir(monkeypatch):
    async def cagir(_girdiler):
        return _plan(1, 3)

    monkeypatch.setattr(takip, "_plan_cagir", cagir)
    assert asyncio.run(takip.plan_oner(SimpleNamespace(**_ihtiyac()), _kart(), "Koop")) is None


def _ihtiyac():
    return {
        "problem_tanimi": "p",
        "basari_kriteri": None,
        "kisitlar": None,
        "musaitlik_tercihi": None,
        "calisma_modeli": None,
    }


def _kart():
    return SimpleNamespace(
        rol_alani="r", deneyim_seviyesi="orta", araclar_teknolojiler=[], somut_ciktilar=[]
    )


# --- Uç nokta: POST /isbirligi/{id}/plan-oner -----------------------------------------------


def test_plan_oner_plani_yazar_ve_karsi_tarafa_bildirir(monkeypatch):
    cagrilar = sahte_plan(monkeypatch)

    async def adimlar(istemci, d):
        isb = await isbirligi_ac(d)
        yanit = await istemci.post(f"/isbirligi/{isb.id}/plan-oner", headers=d.kurum1.baslik)
        assert yanit.status_code == 200, yanit.text
        govde = yanit.json()
        assert [m["baslik"] for m in govde["milestonelar"]] == [a.baslik for a in ORNEK_PLAN]
        assert [m["sira"] for m in govde["milestonelar"]] == [0, 1, 2]
        assert [m["hedef_tarih"] for m in govde["milestonelar"]] == [
            str(BASLANGIC + dt.timedelta(weeks=a.hafta)) for a in ORNEK_PLAN
        ]
        assert all(m["durum"] == "bekliyor" for m in govde["milestonelar"])
        assert govde["plan_onerildi_mi"] is True
        assert govde["durum"] == "plan_bekliyor"
        assert govde["ilerleme"] == {"tamamlanan": 0, "toplam": 3, "geciken": 0}
        assert cagrilar[0][2] == "Koop Bir"

        # Kurum istedi: bildirim gence gider, kuruma değil.
        gence = await bildirimleri(d, d.genc1)
        assert [b.tur for b in gence] == ["plan_duzenlendi"]
        assert "Koop Bir" in gence[0].metin
        assert await bildirimleri(d, d.kurum1) == []

        # Yeniden öner: eski adımlar silinir, yenileri yazılır (3 adım kalır).
        yine = await istemci.post(f"/isbirligi/{isb.id}/plan-oner", headers=d.genc1.baslik)
        assert len(yine.json()["milestonelar"]) == 3

    senaryo(adimlar)


def test_plan_oner_yetkisi(monkeypatch):
    sahte_plan(monkeypatch)

    async def adimlar(istemci, d):
        isb = await isbirligi_ac(d)
        await durumlar(
            istemci,
            "POST",
            f"/isbirligi/{isb.id}/plan-oner",
            {None: 401, d.girvak: 403, d.genc2: 404, d.kurum2: 404},
        )

    senaryo(adimlar)


def test_onaylanmis_planda_yeniden_oneri_409(monkeypatch):
    cagrilar = sahte_plan(monkeypatch)

    async def adimlar(istemci, d):
        isb = await isbirligi_ac(d, adimlar=2)
        isb.durum = "aktif"
        await d.oturum.commit()
        yanit = await istemci.post(f"/isbirligi/{isb.id}/plan-oner", headers=d.genc1.baslik)
        assert yanit.status_code == 409
        assert "değiştirilemez" in yanit.json()["detail"]
        assert cagrilar == []  # LLM'e hiç gidilmedi

    senaryo(adimlar)


def test_ajan_plan_uretemezse_503_ve_plan_degismez(monkeypatch):
    sahte_plan(monkeypatch, sonuc=None)

    async def adimlar(istemci, d):
        isb = await isbirligi_ac(d, adimlar=2)
        yanit = await istemci.post(f"/isbirligi/{isb.id}/plan-oner", headers=d.genc1.baslik)
        assert yanit.status_code == 503
        assert yanit.json()["detail"] == takip_api.PLAN_ONERILEMEDI
        await d.oturum.refresh(isb, ["milestonelar"])
        assert len(isb.milestonelar) == 2

    senaryo(adimlar)


# --- Arka plan işi (kabulden sonra) -----------------------------------------------------------


def _ayni_oturum(monkeypatch, oturum):
    @contextlib.asynccontextmanager
    async def fabrika():
        yield oturum

    monkeypatch.setattr(takip_api, "get_sessionmaker", lambda: fabrika)


def test_kabul_plan_onerisini_arka_planda_baslatir(plan_arka_plan_isi_yok):
    """Kabul ucu işi yalnızca sıraya koyar; sonuç beklenmez."""

    async def adimlar(istemci, d):
        await istemci.post(
            "/eslestirme/ilgileniyorum",
            headers=d.kurum1.baslik,
            json={"eslesme_id": str(d.E1.id)},
        )
        yanit = await istemci.post(f"/eslestirme/{d.E1.id}/kabul", headers=d.genc1.baslik)
        assert yanit.json()["isbirligi_id"] is not None
        # Tekrar kabul yeni iş başlatmaz.
        await istemci.post(f"/eslestirme/{d.E1.id}/kabul", headers=d.genc1.baslik)
        assert [str(i) for i in plan_arka_plan_isi_yok] == [yanit.json()["isbirligi_id"]]

    senaryo(adimlar)


def test_arka_plan_isi_plani_yazar_iki_tarafa_bildirir_ve_ikinci_kez_ezmez(monkeypatch):
    cagrilar = sahte_plan(monkeypatch)

    async def adimlar(istemci, d):
        isb = await isbirligi_ac(d)
        _ayni_oturum(monkeypatch, d.oturum)
        await GERCEK_IS(isb.id)
        yeniden = await d.oturum.scalar(select(Isbirligi).where(Isbirligi.id == isb.id))
        await d.oturum.refresh(yeniden, ["milestonelar"])
        assert len(yeniden.milestonelar) == 3 and yeniden.plan_onerildi_mi
        assert [b.tur for b in await bildirimleri(d, d.genc1)] == ["plan_onerildi"]
        assert [b.tur for b in await bildirimleri(d, d.kurum1)] == ["plan_onerildi"]
        assert "Koop Bir" in (await bildirimleri(d, d.genc1))[0].metin
        assert "Elif" in (await bildirimleri(d, d.kurum1))[0].metin

        await GERCEK_IS(isb.id)  # ikinci çalışma: plan zaten önerildi, dokunmaz
        assert len(cagrilar) == 1

    senaryo(adimlar)
