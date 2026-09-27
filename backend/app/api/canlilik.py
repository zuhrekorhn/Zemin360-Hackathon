"""Canlılık Ajanı — tarama (docs/faz-d-canlilik.md § 1-4, § 8).

Taramanın asıl işi bir uç nokta (Eşleştirme'nin "arka plan işi bir endpoint"
deseni; CLAUDE.md "zamanlayıcı yok"). Kim çağırır:
  - GİRVAK panelindeki "Taramayı şimdi çalıştır" düğmesi (GİRVAK token'ı),
  - canlıda platform cron'u (`X-Tarama-Anahtari` başlığı, `.env`'de
    TARAMA_ANAHTARI) — kullanıcı token'ı değil: o 7 günde düşer.
  - yerelde scripts/canlilik_taramasi.py.

Tarama hiçbir kaydın durumunu değiştirmez ve hareket sayılmaz
(`son_aktivite_tarihi`'ne dokunmaz). İdempotent: art arda iki tarama,
ikincisinde sıfır olay (tekrar kuralı, § 3).
"""

from __future__ import annotations

import datetime as dt
import hmac
import logging
import time
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents import canlilik
from app.agents.canlilik_kurallari import (
    ESIKLER,
    ILGI_YANITSIZ_1,
    ONERI_BEKLIYOR,
    AdimBilgisi,
    Hatirlatma,
    eslesme_hatirlatmalari,
    gecen_gun,
    gecikme_gunu,
    isbirligi_hatirlatmalari,
    tekrar_mi,
)
from app.agents.eslestirme import DURUM_ILGILENILIYOR, DURUM_ONERILDI
from app.agents.takip_durumu import (
    ISBIRLIGI_AKTIF,
    ISBIRLIGI_PLAN_BEKLIYOR,
    MILESTONE_TAMAMLANDI,
)
from app.api.bildirimler import bildirim_ekle
from app.api.kimlik import _bearer, _yetkisiz, mevcut_hesap
from app.core.config import get_settings
from app.db.session import get_session
from app.models.canlilik_olayi import CanlilikOlayi
from app.models.eslesme import Eslesme
from app.models.hesap import ROL_GENC, ROL_GIRVAK, ROL_KURUM
from app.models.ihtiyac_karti import IhtiyacKarti
from app.models.isbirligi import Isbirligi
from app.models.yetenek_karti import YetenekKarti
from app.schemas.canlilik import TaramaSonucu

logger = logging.getLogger("zemin360.canlilik")

router = APIRouter(prefix="/canlilik", tags=["canlilik"])

# Eşzamanlı taramalar (cron + düğme) sıraya girsin; ikincisi birincinin
# yazdıklarını görür ve tekrar kuralı gereği hiçbir şey yazmaz.
TARAMA_KILIDI = 0x7A_43_61_6E  # "zCan"

ANAHTAR_GECERSIZ = "Tarama anahtarı geçersiz."
ANAHTAR_TANIMSIZ = "Tarama anahtarı tanımlı değil; tarama yalnızca GİRVAK hesabıyla çalışır."
YALNIZCA_GIRVAK = "Taramayı yalnızca GİRVAK çalıştırabilir."


# --- Yetki: GİRVAK token'ı ya da cron anahtarı ---------------------------------------------


async def tarama_yetkisi(
    x_tarama_anahtari: str | None = Header(default=None),
    kimlik: HTTPAuthorizationCredentials | None = Depends(_bearer),
    oturum: AsyncSession = Depends(get_session),
) -> str:
    """Döner: çağıranın kim olduğu ("cron" ya da "girvak"), log için.

    Başlık gönderildiyse yalnızca başlığa bakılır: anahtar tanımlı değilse
    bu yol tamamen kapalı (401), yanlışsa 401. Başlık yoksa GİRVAK token'ı.
    """
    if x_tarama_anahtari is not None:
        beklenen = get_settings().tarama_anahtari
        if not beklenen:
            raise _yetkisiz(ANAHTAR_TANIMSIZ)
        if not hmac.compare_digest(x_tarama_anahtari.encode(), beklenen.encode()):
            raise _yetkisiz(ANAHTAR_GECERSIZ)
        return "cron"
    hesap = await mevcut_hesap(kimlik, oturum)
    if hesap.rol != ROL_GIRVAK:
        raise HTTPException(status_code=403, detail=YALNIZCA_GIRVAK)
    return "girvak"


@router.post("/tarama", response_model=TaramaSonucu)
async def tarama(
    cagiran: str = Depends(tarama_yetkisi),
    oturum: AsyncSession = Depends(get_session),
) -> TaramaSonucu:
    sonuc = await tarama_yap(oturum)
    logger.info(
        "Canlılık taraması (%s): %d olay, %d bildirim, %.1f sn",
        cagiran,
        sum(sonuc.olaylar.values()),
        sonuc.bildirim,
        sonuc.sure_sn,
    )
    return sonuc


# --- Tarama ---------------------------------------------------------------------------------


@dataclass
class _Yazilacak:
    """Tekrar kuralından geçmiş, yazılmayı bekleyen tek bir hatırlatma."""

    eslesme: Eslesme
    hatirlatma: Hatirlatma
    alici_hesap_id: uuid.UUID
    baglam: canlilik.HatirlatmaBaglami
    ihtiyac_karti_id: uuid.UUID | None = None


def _anahtar(eslesme_id, tur, alici_hesap_id, milestone_id) -> tuple:
    return (eslesme_id, tur, alici_hesap_id, milestone_id)


def _taraf_hesabi(eslesme: Eslesme, rol: str) -> uuid.UUID | None:
    if rol == ROL_GENC:
        return eslesme.yetenek_karti.kullanici.hesap_id
    return eslesme.ihtiyac_karti.kurum.hesap_id


def _karsi_ad(eslesme: Eslesme, rol: str) -> str:
    """Alıcının karşısındaki taraf: gence kurumun adı, kuruma gencin adı."""
    if rol == ROL_GENC:
        return eslesme.ihtiyac_karti.kurum.ad
    return eslesme.yetenek_karti.kullanici.ad


def _iliskiler():
    return (
        selectinload(Eslesme.yetenek_karti).selectinload(YetenekKarti.kullanici),
        selectinload(Eslesme.ihtiyac_karti).selectinload(IhtiyacKarti.kurum),
    )


async def _son_olaylar(oturum: AsyncSession, eslesme_idler: set) -> dict[tuple, dt.datetime]:
    """Her tekrar anahtarı için en son olayın zamanı (tek sorgu)."""
    if not eslesme_idler:
        return {}
    satirlar = await oturum.execute(
        select(
            CanlilikOlayi.eslesme_id,
            CanlilikOlayi.tur,
            CanlilikOlayi.alici_hesap_id,
            CanlilikOlayi.milestone_id,
            func.max(CanlilikOlayi.tetiklenme_tarihi),
        )
        .where(CanlilikOlayi.eslesme_id.in_(eslesme_idler))
        .group_by(
            CanlilikOlayi.eslesme_id,
            CanlilikOlayi.tur,
            CanlilikOlayi.alici_hesap_id,
            CanlilikOlayi.milestone_id,
        )
    )
    return {_anahtar(*satir[:4]): satir[4] for satir in satirlar.all()}


async def adaylari_topla(
    oturum: AsyncSession, simdi: dt.datetime, bugun: dt.date
) -> list[_Yazilacak]:
    """Kurallara göre hatırlatılması gerekenler, tekrar kuralından geçirilmiş."""
    esik = simdi - dt.timedelta(days=min(ESIKLER[ILGI_YANITSIZ_1], ESIKLER[ONERI_BEKLIYOR]))
    eslesmeler = list(
        await oturum.scalars(
            select(Eslesme)
            .options(*_iliskiler())
            .where(
                Eslesme.durum.in_([DURUM_ONERILDI, DURUM_ILGILENILIYOR]),
                Eslesme.son_aktivite_tarihi <= esik,
            )
        )
    )
    isbirlikleri = list(
        await oturum.scalars(
            select(Isbirligi)
            .options(
                selectinload(Isbirligi.eslesme)
                .selectinload(Eslesme.yetenek_karti)
                .selectinload(YetenekKarti.kullanici),
                selectinload(Isbirligi.eslesme)
                .selectinload(Eslesme.ihtiyac_karti)
                .selectinload(IhtiyacKarti.kurum),
                selectinload(Isbirligi.milestonelar),
            )
            .where(Isbirligi.durum.in_([ISBIRLIGI_PLAN_BEKLIYOR, ISBIRLIGI_AKTIF]))
        )
    )

    # (eşleşme, hatırlatma, bağlam) üçlüleri — henüz tekrar kuralına sorulmadı
    adaylar: list[tuple[Eslesme, Hatirlatma, canlilik.HatirlatmaBaglami]] = []
    for eslesme in eslesmeler:
        gun = gecen_gun(eslesme.son_aktivite_tarihi, simdi)
        for h in eslesme_hatirlatmalari(eslesme.durum, gun):
            adaylar.append(
                (
                    eslesme,
                    h,
                    canlilik.HatirlatmaBaglami(
                        tur=h.tur, alici=h.alici, gun=gun, karsi_ad=_karsi_ad(eslesme, h.alici)
                    ),
                )
            )

    for isbirligi in isbirlikleri:
        eslesme = isbirligi.eslesme
        gun = gecen_gun(eslesme.son_aktivite_tarihi, simdi)
        adimlar = sorted(isbirligi.milestonelar, key=lambda m: m.sira)
        sonraki = next((m.baslik for m in adimlar if m.durum != MILESTONE_TAMAMLANDI), None)
        adim_adi = {m.id: m.baslik for m in adimlar}
        gecikme = {
            m.id: gecikme_gunu(m.hedef_tarih, m.durum == MILESTONE_TAMAMLANDI, bugun)
            for m in adimlar
        }
        for h in isbirligi_hatirlatmalari(
            durum=isbirligi.durum,
            hareketsiz_gun=gun,
            genc_plan_onayi=isbirligi.genc_plan_onayi is not None,
            kurum_plan_onayi=isbirligi.kurum_plan_onayi is not None,
            adimlar=[
                AdimBilgisi(
                    id=m.id,
                    hedef_tarih=m.hedef_tarih,
                    genc_isaretledi=m.genc_isaret is not None,
                    kurum_isaretledi=m.kurum_isaret is not None,
                )
                for m in adimlar
            ],
            bugun=bugun,
        ):
            adaylar.append(
                (
                    eslesme,
                    h,
                    canlilik.HatirlatmaBaglami(
                        tur=h.tur,
                        alici=h.alici,
                        gun=gecikme[h.milestone_id] if h.milestone_id else gun,
                        karsi_ad=_karsi_ad(eslesme, h.alici),
                        adim=adim_adi[h.milestone_id] if h.milestone_id else sonraki,
                    ),
                )
            )

    son_olaylar = await _son_olaylar(oturum, {e.id for e, _, _ in adaylar})
    yazilacaklar: list[_Yazilacak] = []
    for eslesme, h, baglam in adaylar:
        alici = _taraf_hesabi(eslesme, h.alici)
        if alici is None:
            continue  # hesabı olmayan (Faz B öncesi) profil: okuyacak kimse yok
        son = son_olaylar.get(_anahtar(eslesme.id, h.tur, alici, h.milestone_id))
        if tekrar_mi(h.tur, son, eslesme.son_aktivite_tarihi):
            continue
        yazilacaklar.append(
            _Yazilacak(
                eslesme=eslesme,
                hatirlatma=h,
                alici_hesap_id=alici,
                baglam=baglam,
                ihtiyac_karti_id=eslesme.ihtiyac_karti_id,
            )
        )
    return yazilacaklar


async def metinleri_uret(yazilacaklar: list[_Yazilacak]) -> list[str]:
    """Her bildirim için metin. 3. adımda LLM kişiselleştirmesi buraya gelir;
    şimdilik (ve LLM kesilirse) türün şablon metni."""
    return [canlilik.sablon_metni(y.baglam) for y in yazilacaklar]


async def tarama_yap(oturum: AsyncSession, simdi: dt.datetime | None = None) -> TaramaSonucu:
    """Bütün taramayı tek işlemde yapar; olay ve bildirim birlikte yazılır."""
    baslangic = time.perf_counter()
    simdi = simdi or dt.datetime.now(dt.UTC)
    bugun = dt.date.today()
    await oturum.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": TARAMA_KILIDI})

    yazilacaklar = await adaylari_topla(oturum, simdi, bugun)

    # Bakılmayan öneriler kuruma ihtiyaç kartı başına TEK bildirimle gider
    # (§ 1): olay her eşleşme için ayrı, bildirim toplu.
    gruplar: dict[tuple, list[_Yazilacak]] = defaultdict(list)
    tekiller: list[_Yazilacak] = []
    for y in yazilacaklar:
        if y.hatirlatma.tur == ONERI_BEKLIYOR:
            gruplar[(y.ihtiyac_karti_id, y.alici_hesap_id)].append(y)
        else:
            tekiller.append(y)

    bildirimlik: list[tuple[_Yazilacak, list[_Yazilacak]]] = [(y, [y]) for y in tekiller]
    for grup in gruplar.values():
        temsilci = max(grup, key=lambda y: y.baglam.gun)
        temsilci.baglam = canlilik.HatirlatmaBaglami(
            tur=ONERI_BEKLIYOR,
            alici=ROL_KURUM,
            gun=temsilci.baglam.gun,
            karsi_ad=temsilci.baglam.karsi_ad,
            sayi=len(grup),
        )
        bildirimlik.append((temsilci, grup))

    metinler = await metinleri_uret([temsilci for temsilci, _ in bildirimlik])

    olaylar: Counter[str] = Counter()
    for (temsilci, grup), metin in zip(bildirimlik, metinler, strict=True):
        for y in grup:
            oturum.add(
                CanlilikOlayi(
                    eslesme_id=y.eslesme.id,
                    tur=y.hatirlatma.tur,
                    mesaj_metni=metin,
                    alici_hesap_id=y.alici_hesap_id,
                    milestone_id=y.hatirlatma.milestone_id,
                    ihtiyac_karti_id=y.ihtiyac_karti_id,
                )
            )
            olaylar[y.hatirlatma.tur] += 1
        bildirim_ekle(
            oturum, temsilci.alici_hesap_id, temsilci.hatirlatma.tur, metin, temsilci.eslesme.id
        )
    await oturum.commit()

    return TaramaSonucu(
        tarih=simdi,
        olaylar=dict(olaylar),
        bildirim=len(bildirimlik),
        sure_sn=round(time.perf_counter() - baslangic, 2),
    )
