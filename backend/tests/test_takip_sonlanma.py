"""Erken sonlanma (docs/plans/takip-surecleri.md § Erken sonlanma).

Kural saf (`takip_durumu.sonlanma_gecisi`, `_kapali_degil`); uç gerçek
veritabanında: yetki, geri açılmama, karşı tarafa nedensiz nötr bildirim.
"""

import typing

import pytest

from app.agents.takip_durumu import (
    ISARETLE,
    ISBIRLIGI_BITTI,
    PLAN_DUZENLE,
    SONLANMA_NEDENLERI,
    SUREC_SONLANDI,
    GecersizTakipGecisi,
    Isaretler,
    PlanDurumu,
    isaret_gecisi,
    plan_gecisi,
    sonlanma_gecisi,
)
from app.models.bildirim import TUR_ISBIRLIGI_SONLANDI
from app.schemas.takip import SonlandirIstegi
from tests.takip_dunyasi import bildirimleri, isbirligi_ac
from tests.test_sahiplik import durumlar, senaryo

# --- Kural (saf) --------------------------------------------------------------------------


@pytest.mark.parametrize("durum", ["plan_bekliyor", "aktif"])
def test_acik_surec_sonlandirilabilir(durum):
    assert sonlanma_gecisi(durum, "genc") is True
    assert sonlanma_gecisi(durum, "kurum") is True


def test_sonlanmis_surecin_tekrari_yan_etkisiz():
    assert sonlanma_gecisi("sonlandi", "kurum") is False


def test_tamamlanmis_surec_sonlandirilamaz():
    with pytest.raises(GecersizTakipGecisi, match=ISBIRLIGI_BITTI):
        sonlanma_gecisi("tamamlandi", "genc")


def test_sonlanmis_surec_geri_acilmaz():
    with pytest.raises(GecersizTakipGecisi, match=SUREC_SONLANDI):
        plan_gecisi(PlanDurumu("sonlandi", False, False), PLAN_DUZENLE, "genc", milestone_sayisi=1)
    with pytest.raises(GecersizTakipGecisi, match=SUREC_SONLANDI):
        isaret_gecisi("sonlandi", Isaretler(False, False), ISARETLE, "kurum")


def test_istek_semasi_neden_kumesiyle_ayni():
    alan = SonlandirIstegi.model_fields["neden"].annotation
    assert typing.get_args(alan) == SONLANMA_NEDENLERI


# --- Uç: POST /isbirligi/{id}/sonlandir -----------------------------------------------------

NEDEN = {"neden": "karar_olumsuz"}


def _yol(isb) -> str:
    return f"/isbirligi/{isb.id}/sonlandir"


def test_sonlandirma_yetkisi_ve_neden_dogrulamasi():
    async def adimlar(istemci, d):
        isb = await isbirligi_ac(d, adimlar=2)
        await durumlar(
            istemci,
            "POST",
            _yol(isb),
            {None: 401, d.girvak: 403, d.genc2: 404, d.kurum2: 404},
            json=NEDEN,
        )
        for govde in ({}, {"neden": "bilmiyorum"}, {**NEDEN, "not": "x"}):
            yanit = await istemci.post(_yol(isb), headers=d.genc1.baslik, json=govde)
            assert yanit.status_code == 422, govde

    senaryo(adimlar)


def test_sonlandirilan_surec_geri_acilmaz_karsi_tarafa_neden_yazilmaz():
    async def adimlar(istemci, d):
        isb = await isbirligi_ac(d, adimlar=2)
        yanit = await istemci.post(_yol(isb), headers=d.genc1.baslik, json=NEDEN)
        assert yanit.status_code == 200
        assert yanit.json()["durum"] == "sonlandi"
        assert "sonlanma_nedeni" not in yanit.json()

        # Karşı taraf (firma) nötr bildirim alır; neden yok, "siz" hitabı.
        kuruma = [b for b in await bildirimleri(d, d.kurum1) if b.tur == TUR_ISBIRLIGI_SONLANDI]
        assert len(kuruma) == 1
        assert kuruma[0].metin == "Elif ile süreciniz sonlandı."
        assert not any(k in kuruma[0].metin.casefold() for k in ("karar", "olumsuz", "neden"))
        assert await bildirimleri(d, d.genc1) == []  # sonlandıran bildirim almaz

        # Tekrar: 200, yan etkisiz, ilk neden korunur.
        tekrar = await istemci.post(
            _yol(isb), headers=d.kurum1.baslik, json={"neden": "iletisim_kurulamadi"}
        )
        assert tekrar.status_code == 200 and tekrar.json()["durum"] == "sonlandi"
        await d.oturum.refresh(isb)
        assert isb.sonlanma_nedeni == "karar_olumsuz" and isb.sonlanma_tarihi is not None
        assert len(await bildirimleri(d, d.kurum1)) == 1

        # Geri açılmaz: plan onayı, düzenleme, yeniden plan hepsi 409.
        adim = yanit.json()["milestonelar"][0]["id"]
        for yontem, yol, govde in (
            ("POST", f"/isbirligi/{isb.id}/plan-onayla", None),
            ("POST", f"/isbirligi/{isb.id}/plan-oner", None),
            ("POST", f"/isbirligi/{isb.id}/milestone-ekle", {"baslik": "Yeni"}),
            ("POST", f"/isbirligi/{isb.id}/milestone/{adim}/isaretle", None),
        ):
            sonuc = await istemci.request(yontem, yol, headers=d.genc1.baslik, json=govde)
            assert sonuc.status_code == 409, yol
            assert sonuc.json()["detail"] == SUREC_SONLANDI
        await d.oturum.refresh(isb)
        assert isb.durum == "sonlandi"

    senaryo(adimlar)


def test_tamamlanmis_isbirligi_sonlandirilamaz():
    async def adimlar(istemci, d):
        isb = await isbirligi_ac(d, adimlar=1)
        isb.durum = "tamamlandi"
        await d.oturum.commit()
        yanit = await istemci.post(_yol(isb), headers=d.kurum1.baslik, json=NEDEN)
        assert yanit.status_code == 409
        assert yanit.json()["detail"] == ISBIRLIGI_BITTI

    senaryo(adimlar)
