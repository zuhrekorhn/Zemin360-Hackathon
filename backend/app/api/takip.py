"""Takip Ajanı uç noktaları (docs/faz-c-takip.md § 7).

İş birliği sayfası iki tarafa aynı görünümdür; GİRVAK yalnızca okur ve
e-postaları görmez. Kurallar iki saf fonksiyonda (app/agents/takip_durumu.py),
bu modül yalnızca uygular: yetki, veritabanı, bildirim.

Sahiplik (Faz B sözleşmesi): 401 token yok, 403 rol uygun değil (GİRVAK
yazamaz), 404 başkasının iş birliği.
"""

from __future__ import annotations

import datetime as dt
import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents import takip
from app.agents.takip_durumu import (
    ISARETI_GERI_AL,
    ISARETLE,
    ISBIRLIGI_AKTIF,
    ISBIRLIGI_PLAN_BEKLIYOR,
    ISBIRLIGI_TAMAMLANDI,
    MILESTONE_BEKLIYOR,
    MILESTONE_TAMAMLANDI,
    PLAN_DUZENLE,
    PLAN_KILITLI,
    PLAN_ONAYLA,
    GecersizTakipGecisi,
    Isaretler,
    PlanDurumu,
    PlanSonucu,
    RolUygunDegil,
    gecikmis_mi,
    isaret_gecisi,
    isbirligi_tamamlandi_mi,
    plan_gecisi,
)
from app.api import sahiplik
from app.api.bildirimler import bildirim_ekle
from app.api.kimlik import mevcut_hesap, rol_gerekli
from app.api.sahiplik import bulunamadi, eslesmedeki_taraf, girvak_mi, karsi_taraf
from app.db.session import get_session, get_sessionmaker
from app.models.bildirim import (
    TUR_ADIM_ISARETLENDI,
    TUR_ADIM_TAMAMLANDI,
    TUR_ISBIRLIGI_TAMAMLANDI,
    TUR_PLAN_DUZENLENDI,
    TUR_PLAN_ONAYI,
    TUR_PLAN_ONAYLANDI,
    TUR_PLAN_ONERILDI,
    Bildirim,
)
from app.models.eslesme import Eslesme
from app.models.firma_karti import FirmaKarti
from app.models.hesap import ROL_GENC, ROL_KURUM, Hesap
from app.models.ihtiyac_karti import IhtiyacKarti
from app.models.isbirligi import Isbirligi
from app.models.milestone import Milestone
from app.models.yetenek_karti import YetenekKarti
from app.schemas.takip import (
    Ilerleme,
    IsbirligiDetayi,
    MilestoneEkleIstegi,
    MilestoneGuncelleIstegi,
    MilestoneYaniti,
)
from app.servisler.eslestirme import iletisim

logger = logging.getLogger("zemin360.takip")

router = APIRouter(prefix="/isbirligi", tags=["takip"])

ISBIRLIGI_BULUNAMADI = "İş birliği bulunamadı"
ADIM_BULUNAMADI = "Adım bulunamadı"
KANIT_ONAYDAN_SONRA = "Kanıt linki, plan iki tarafça onaylandıktan sonra eklenir."
PLAN_ONERILEMEDI = (
    "Plan şu an önerilemedi. Adımları elle ekleyebilir ya da biraz sonra yeniden deneyebilirsin."
)


# --- Okuma ve yetki ---------------------------------------------------------------------


def _iliskileriyle(sorgu):
    """Görünüm, sahiplik ve plan istemi için gereken her şey tek seferde."""
    eslesme = selectinload(Isbirligi.eslesme)
    return sorgu.options(
        eslesme.selectinload(Eslesme.yetenek_karti).selectinload(YetenekKarti.kullanici),
        eslesme.selectinload(Eslesme.yetenek_karti).selectinload(YetenekKarti.somut_ciktilar),
        eslesme.selectinload(Eslesme.firma_karti).selectinload(FirmaKarti.kurum),
        eslesme.selectinload(Eslesme.ihtiyac_karti).selectinload(IhtiyacKarti.kurum),
        selectinload(Isbirligi.milestonelar),
    )


async def isbirligini_getir(
    oturum: AsyncSession, isbirligi_id: uuid.UUID, *, kilitle: bool = False
) -> Isbirligi | None:
    """`kilitle`: yazan istekler satırı kilitler; çift tıklama iki kez uygulanmasın."""
    sorgu = (
        _iliskileriyle(select(Isbirligi))
        .where(Isbirligi.id == isbirligi_id)
        .execution_options(populate_existing=True)
    )
    if kilitle:
        sorgu = sorgu.with_for_update(of=Isbirligi)
    return await oturum.scalar(sorgu)


def taraf_rolu(hesap: Hesap, isbirligi: Isbirligi) -> str | None:
    """Hesap bu iş birliğinin aday tarafı mı, ilan tarafı mı? Değilse None."""
    return eslesmedeki_taraf(hesap, isbirligi.eslesme)


async def okunabilir_isbirligi(
    oturum: AsyncSession, hesap: Hesap, isbirligi_id: uuid.UUID
) -> Isbirligi:
    isbirligi = await isbirligini_getir(oturum, isbirligi_id)
    if isbirligi is None or not (girvak_mi(hesap) or taraf_rolu(hesap, isbirligi)):
        raise bulunamadi(ISBIRLIGI_BULUNAMADI)
    return isbirligi


async def yazilabilir_isbirligi(
    oturum: AsyncSession, hesap: Hesap, isbirligi_id: uuid.UUID
) -> tuple[Isbirligi, str]:
    """Kilitli okur; yalnızca iki taraf. Döner: (iş birliği, çağıranın rolü)."""
    isbirligi = await isbirligini_getir(oturum, isbirligi_id, kilitle=True)
    rol = taraf_rolu(hesap, isbirligi) if isbirligi is not None else None
    if isbirligi is None or rol is None:
        raise bulunamadi(ISBIRLIGI_BULUNAMADI)
    return isbirligi, rol


# --- Yardımcılar ------------------------------------------------------------------------


def _simdi() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def taraf_adi(isbirligi: Isbirligi, rol: str) -> str:
    return sahiplik.taraf_adi(isbirligi.eslesme, rol)


def taraf_hesabi(isbirligi: Isbirligi, rol: str) -> uuid.UUID | None:
    return sahiplik.taraf_hesabi(isbirligi.eslesme, rol)


karsi_rol = karsi_taraf


def aktivite(isbirligi: Isbirligi) -> None:
    """Her Takip eylemi eşleşmenin aktivitesini tazeler; Canlılık bunu okuyacak."""
    isbirligi.eslesme.son_aktivite_tarihi = _simdi()


def plan_gecisini_uygula(isbirligi: Isbirligi, olay: str, rol: str) -> PlanSonucu:
    """Kuralı sorar, sonucu modele yazar. 409 kural dışı, 403 taraf olmayan rol."""
    mevcut = PlanDurumu(
        isbirligi.durum,
        genc_onayi=isbirligi.genc_plan_onayi is not None,
        kurum_onayi=isbirligi.kurum_plan_onayi is not None,
    )
    try:
        sonuc = plan_gecisi(mevcut, olay, rol, milestone_sayisi=len(isbirligi.milestonelar))
    except GecersizTakipGecisi as hata:
        raise HTTPException(status_code=409, detail=str(hata)) from hata
    except RolUygunDegil as hata:
        raise HTTPException(
            status_code=403, detail="Bu işlemi yalnızca iki taraf yapabilir."
        ) from hata
    if not sonuc.degisti:
        return sonuc
    simdi = _simdi()
    isbirligi.durum = sonuc.durum.durum
    isbirligi.genc_plan_onayi = (
        (isbirligi.genc_plan_onayi or simdi) if sonuc.durum.genc_onayi else None
    )
    isbirligi.kurum_plan_onayi = (
        (isbirligi.kurum_plan_onayi or simdi) if sonuc.durum.kurum_onayi else None
    )
    return sonuc


def plani_yaz(isbirligi: Isbirligi, adimlar: list[takip.AdimOnerisi]) -> None:
    """Ajanın önerisini plan yapar: eski adımlar silinir, onaylar sıfırlanır."""
    baslangic = isbirligi.baslangic_tarihi or dt.date.today()
    isbirligi.milestonelar.clear()
    for sira, adim in enumerate(adimlar):
        isbirligi.milestonelar.append(
            Milestone(
                baslik=adim.baslik.strip(),
                aciklama=adim.aciklama.strip(),
                sira=sira,
                hedef_tarih=takip.hedef_tarihi(baslangic, adim.hafta),
                durum=MILESTONE_BEKLIYOR,
            )
        )
    isbirligi.plan_onerildi_mi = True
    isbirligi.genc_plan_onayi = None
    isbirligi.kurum_plan_onayi = None


def ilerleme_hesapla(milestonelar, bugun: dt.date | None = None) -> Ilerleme:
    """Tamamlanan / toplam / geciken — gecikme okuma anında (saklanmaz)."""
    bugun = bugun or dt.date.today()
    tamam = [m.durum == MILESTONE_TAMAMLANDI for m in milestonelar]
    return Ilerleme(
        tamamlanan=sum(tamam),
        toplam=len(tamam),
        geciken=sum(
            gecikmis_mi(m.hedef_tarih, t, bugun) for m, t in zip(milestonelar, tamam, strict=True)
        ),
    )


def detay(isbirligi: Isbirligi, hesap: Hesap, bugun: dt.date | None = None) -> IsbirligiDetayi:
    bugun = bugun or dt.date.today()
    eslesme = isbirligi.eslesme
    adimlar = [
        MilestoneYaniti(
            id=m.id,
            sira=m.sira,
            baslik=m.baslik,
            aciklama=m.aciklama,
            hedef_tarih=m.hedef_tarih,
            durum=m.durum,
            genc_isaret=m.genc_isaret,
            kurum_isaret=m.kurum_isaret,
            kanit_linki=m.kanit_linki,
            gecikmis=gecikmis_mi(m.hedef_tarih, m.durum == MILESTONE_TAMAMLANDI, bugun),
        )
        for m in sorted(isbirligi.milestonelar, key=lambda m: m.sira)
    ]
    return IsbirligiDetayi(
        id=isbirligi.id,
        durum=isbirligi.durum,
        baslangic_tarihi=isbirligi.baslangic_tarihi,
        tamamlanma_tarihi=isbirligi.tamamlanma_tarihi,
        eslesme_id=eslesme.id,
        yetenek_karti_id=eslesme.yetenek_karti_id,
        firma_karti_id=eslesme.firma_karti_id,
        ihtiyac_karti_id=eslesme.ihtiyac_karti_id,
        aday_turu="firma" if eslesme.firma_karti_id else "genc",
        aday_adi=sahiplik.taraf_adi(eslesme, sahiplik.TARAF_ADAY),
        genc_adi=eslesme.yetenek_karti.kullanici.ad if eslesme.yetenek_karti else None,
        kurum_adi=eslesme.ihtiyac_karti.kurum.ad,
        rol_alani=eslesme.yetenek_karti.rol_alani if eslesme.yetenek_karti else None,
        problem_tanimi=eslesme.ihtiyac_karti.problem_tanimi,
        basari_kriteri=eslesme.ihtiyac_karti.basari_kriteri,
        genc_plan_onayi=isbirligi.genc_plan_onayi,
        kurum_plan_onayi=isbirligi.kurum_plan_onayi,
        plan_onerildi_mi=isbirligi.plan_onerildi_mi,
        milestonelar=adimlar,
        ilerleme=ilerleme_hesapla(isbirligi.milestonelar, bugun),
        durum_ozeti=isbirligi.durum_ozeti,
        ozet_tarihi=isbirligi.ozet_tarihi,
        iletisim=iletisim(eslesme, hesap),
    )


async def plan_duzenlendi_bildir(
    oturum: AsyncSession, isbirligi: Isbirligi, rol: str, metin: str
) -> None:
    """Karşı tarafa "plan değişti" der; okunmamış aynı bildirim varsa yenisini yazmaz.

    Art arda beş düzenleme beş bildirim olmasın: karşı taraf bildirimi
    açtığında zaten son hâli görecek.
    """
    alici = taraf_hesabi(isbirligi, karsi_rol(rol))
    if alici is None:
        return
    bekleyen = await oturum.scalar(
        select(Bildirim.id).where(
            Bildirim.hesap_id == alici,
            Bildirim.tur == TUR_PLAN_DUZENLENDI,
            Bildirim.eslesme_id == isbirligi.eslesme_id,
            Bildirim.okundu_tarihi.is_(None),
        )
    )
    if bekleyen is None:
        bildirim_ekle(oturum, alici, TUR_PLAN_DUZENLENDI, metin, isbirligi.eslesme_id)


def adimi_bul(isbirligi: Isbirligi, milestone_id: uuid.UUID) -> Milestone:
    for milestone in isbirligi.milestonelar:
        if milestone.id == milestone_id:
            return milestone
    raise bulunamadi(ADIM_BULUNAMADI)


def _sirala(isbirligi: Isbirligi) -> None:
    """Silmeden sonra sıra boşluksuz kalsın (0, 1, 2…)."""
    for sira, milestone in enumerate(sorted(isbirligi.milestonelar, key=lambda m: m.sira)):
        milestone.sira = sira


async def _duzenle(oturum: AsyncSession, isbirligi: Isbirligi, rol: str) -> None:
    """Plan düzenlemesinin ortak kısmı: kural (onaylar sıfırlanır), aktivite, bildirim."""
    plan_gecisini_uygula(isbirligi, PLAN_DUZENLE, rol)
    aktivite(isbirligi)
    await plan_duzenlendi_bildir(
        oturum,
        isbirligi,
        rol,
        f"{taraf_adi(isbirligi, rol)} planı düzenledi; son hâli onayını bekliyor.",
    )


async def _ajana_sor(isbirligi: Isbirligi) -> list[takip.AdimOnerisi] | None:
    eslesme = isbirligi.eslesme
    if eslesme.firma_karti is not None:
        # Firma–firma (docs/plans/firma-akisi.md § 9): ayrı istem, aynı kurallar.
        return await takip.firma_plan_oner(
            eslesme.ihtiyac_karti, eslesme.firma_karti, eslesme.ihtiyac_karti.kurum.ad
        )
    return await takip.plan_oner(
        eslesme.ihtiyac_karti, eslesme.yetenek_karti, eslesme.ihtiyac_karti.kurum.ad
    )


# --- Uç noktalar ----------------------------------------------------------------------


@router.post("/{isbirligi_id}/plan-oner", response_model=IsbirligiDetayi)
async def plan_oner(
    isbirligi_id: uuid.UUID,
    hesap: Hesap = Depends(rol_gerekli(ROL_GENC, ROL_KURUM)),
    oturum: AsyncSession = Depends(get_session),
) -> IsbirligiDetayi:
    """Ajandan (yeniden) plan ister. Yalnızca `plan_bekliyor`'da; mevcut adımları
    siler ve iki onayı sıfırlar (arayüz önce sorar). LLM yanıt vermezse plan
    olduğu gibi kalır: 429 hız sınırı / 503 arıza, kurala uymayan çıktıda 503."""
    isbirligi, rol = await yazilabilir_isbirligi(oturum, hesap, isbirligi_id)
    plan_gecisini_uygula(isbirligi, PLAN_DUZENLE, rol)
    adimlar = await _ajana_sor(isbirligi)
    if adimlar is None:
        raise HTTPException(status_code=503, detail=PLAN_ONERILEMEDI)
    plani_yaz(isbirligi, adimlar)
    aktivite(isbirligi)
    await plan_duzenlendi_bildir(
        oturum,
        isbirligi,
        rol,
        f"{taraf_adi(isbirligi, rol)} ajandan yeni bir plan istedi; son hâli onayını bekliyor.",
    )
    await oturum.commit()
    return detay(isbirligi, hesap)


async def plani_arka_planda_oner(isbirligi_id: uuid.UUID) -> None:
    """Genç kabul edince planı yanıt gönderildikten sonra önerir (§ 4).

    Eşleştirme'nin arka plan işiyle aynı desen: kendi oturumu, hata yutulur.
    Plan önerilmediyse (LLM yok ya da çıktı kurala uymadı) iş birliği planı
    boş kalır; taraflar sayfadan "Plan öner" diyebilir ya da elle ekleyebilir.
    Tarafların eline geçmiş bir planı ezmez.
    """
    async with get_sessionmaker()() as oturum:
        try:
            isbirligi = await isbirligini_getir(oturum, isbirligi_id, kilitle=True)
            if (
                isbirligi is None
                or isbirligi.durum != ISBIRLIGI_PLAN_BEKLIYOR
                or isbirligi.plan_onerildi_mi
                or isbirligi.milestonelar
            ):
                return
            adimlar = await _ajana_sor(isbirligi)
            if adimlar is None:
                return
            plani_yaz(isbirligi, adimlar)
            for rol in (ROL_GENC, ROL_KURUM):
                bildirim_ekle(
                    oturum,
                    taraf_hesabi(isbirligi, rol),
                    TUR_PLAN_ONERILDI,
                    f"{taraf_adi(isbirligi, karsi_rol(rol))} ile iş birliğin için bir plan "
                    "önerildi; gözden geçir ve onayla.",
                    isbirligi.eslesme_id,
                )
            await oturum.commit()
        except Exception:
            logger.exception("Arka plan plan önerisi başarısız (%s)", isbirligi_id)


@router.post("/{isbirligi_id}/milestone-ekle", response_model=IsbirligiDetayi, status_code=201)
async def milestone_ekle(
    isbirligi_id: uuid.UUID,
    istek: MilestoneEkleIstegi,
    hesap: Hesap = Depends(rol_gerekli(ROL_GENC, ROL_KURUM)),
    oturum: AsyncSession = Depends(get_session),
) -> IsbirligiDetayi:
    """Plana adım ekler (en sona). Yalnızca `plan_bekliyor`; iki onay sıfırlanır."""
    isbirligi, rol = await yazilabilir_isbirligi(oturum, hesap, isbirligi_id)
    await _duzenle(oturum, isbirligi, rol)
    isbirligi.milestonelar.append(
        Milestone(
            baslik=istek.baslik.strip(),
            aciklama=(istek.aciklama or "").strip() or None,
            hedef_tarih=istek.hedef_tarih,
            sira=len(isbirligi.milestonelar),
            durum=MILESTONE_BEKLIYOR,
        )
    )
    await oturum.commit()
    return detay(isbirligi, hesap)


@router.patch("/{isbirligi_id}/milestone/{milestone_id}", response_model=IsbirligiDetayi)
async def milestone_guncelle(
    isbirligi_id: uuid.UUID,
    milestone_id: uuid.UUID,
    istek: MilestoneGuncelleIstegi,
    hesap: Hesap = Depends(rol_gerekli(ROL_GENC, ROL_KURUM)),
    oturum: AsyncSession = Depends(get_session),
) -> IsbirligiDetayi:
    """Taslakta başlık/açıklama/tarih (iki onay sıfırlanır); `aktif`'te yalnızca kanıt linki.

    Gönderilmeyen alan değişmez. Onaylanmış planda içerik değişikliği 409.
    """
    isbirligi, rol = await yazilabilir_isbirligi(oturum, hesap, isbirligi_id)
    milestone = adimi_bul(isbirligi, milestone_id)
    gelen = istek.model_fields_set
    icerik = gelen & {"baslik", "aciklama", "hedef_tarih"}

    if isbirligi.durum == ISBIRLIGI_TAMAMLANDI:
        plan_gecisini_uygula(isbirligi, PLAN_DUZENLE, rol)  # 409, mesajıyla
    if isbirligi.durum == ISBIRLIGI_AKTIF and icerik:
        raise HTTPException(status_code=409, detail=PLAN_KILITLI)
    if isbirligi.durum == ISBIRLIGI_PLAN_BEKLIYOR and "kanit_linki" in gelen:
        raise HTTPException(status_code=409, detail=KANIT_ONAYDAN_SONRA)

    if icerik:
        await _duzenle(oturum, isbirligi, rol)
        if "baslik" in icerik:
            if not (istek.baslik or "").strip():
                raise HTTPException(status_code=422, detail="Adımın başlığı boş olamaz.")
            milestone.baslik = istek.baslik.strip()
        if "aciklama" in icerik:
            milestone.aciklama = (istek.aciklama or "").strip() or None
        if "hedef_tarih" in icerik:
            milestone.hedef_tarih = istek.hedef_tarih
    if "kanit_linki" in gelen:
        milestone.kanit_linki = (istek.kanit_linki or "").strip() or None
        aktivite(isbirligi)
    await oturum.commit()
    return detay(isbirligi, hesap)


@router.delete("/{isbirligi_id}/milestone/{milestone_id}", response_model=IsbirligiDetayi)
async def milestone_sil(
    isbirligi_id: uuid.UUID,
    milestone_id: uuid.UUID,
    hesap: Hesap = Depends(rol_gerekli(ROL_GENC, ROL_KURUM)),
    oturum: AsyncSession = Depends(get_session),
) -> IsbirligiDetayi:
    """Taslaktan adım siler; sıra yeniden numaralanır, iki onay sıfırlanır."""
    isbirligi, rol = await yazilabilir_isbirligi(oturum, hesap, isbirligi_id)
    milestone = adimi_bul(isbirligi, milestone_id)
    await _duzenle(oturum, isbirligi, rol)
    isbirligi.milestonelar.remove(milestone)
    _sirala(isbirligi)
    await oturum.commit()
    return detay(isbirligi, hesap)


@router.post("/{isbirligi_id}/plan-onayla", response_model=IsbirligiDetayi)
async def plan_onayla(
    isbirligi_id: uuid.UUID,
    arka_plan: BackgroundTasks,
    hesap: Hesap = Depends(rol_gerekli(ROL_GENC, ROL_KURUM)),
    oturum: AsyncSession = Depends(get_session),
) -> IsbirligiDetayi:
    """Çağıranın tarafı mevcut planı onaylar; iki onay da varsa iş birliği `aktif`.

    Boş plan onaylanamaz (409). Aynı onayın tekrarı 200, yan etkisiz.
    """
    isbirligi, rol = await yazilabilir_isbirligi(oturum, hesap, isbirligi_id)
    sonuc = plan_gecisini_uygula(isbirligi, PLAN_ONAYLA, rol)
    if sonuc.degisti:
        aktivite(isbirligi)
        if isbirligi.durum == ISBIRLIGI_AKTIF:
            ozeti_sirala(arka_plan, isbirligi)
            for taraf in (ROL_GENC, ROL_KURUM):
                bildirim_ekle(
                    oturum,
                    taraf_hesabi(isbirligi, taraf),
                    TUR_PLAN_ONAYLANDI,
                    f"{taraf_adi(isbirligi, karsi_rol(taraf))} ile planınız iki tarafça "
                    "onaylandı; iş birliği başladı.",
                    isbirligi.eslesme_id,
                )
        else:
            bildirim_ekle(
                oturum,
                taraf_hesabi(isbirligi, karsi_rol(rol)),
                TUR_PLAN_ONAYI,
                f"{taraf_adi(isbirligi, rol)} planı onayladı; senin onayın bekleniyor.",
                isbirligi.eslesme_id,
            )
    await oturum.commit()
    return detay(isbirligi, hesap)


@router.get("/{isbirligi_id}", response_model=IsbirligiDetayi)
async def isbirligi_getir(
    isbirligi_id: uuid.UUID,
    hesap: Hesap = Depends(mevcut_hesap),
    oturum: AsyncSession = Depends(get_session),
) -> IsbirligiDetayi:
    """İki tarafa aynı görünüm: plan, zaman çizelgesi (gecikme hesaplı), onaylar,
    özet. GİRVAK okur ama e-postaları görmez; başkasının iş birliği 404."""
    return detay(await okunabilir_isbirligi(oturum, hesap, isbirligi_id), hesap)


@router.post("/{isbirligi_id}/milestone/{milestone_id}/isaretle", response_model=IsbirligiDetayi)
async def isaretle(
    isbirligi_id: uuid.UUID,
    milestone_id: uuid.UUID,
    arka_plan: BackgroundTasks,
    hesap: Hesap = Depends(rol_gerekli(ROL_GENC, ROL_KURUM)),
    oturum: AsyncSession = Depends(get_session),
) -> IsbirligiDetayi:
    """Çağıranın tarafı adımı "tamamlandı" der. İki taraf da derse adım tamamlanır;
    son adım da tamamlanınca iş birliği kendiliğinden `tamamlandi` olur (kural)."""
    return await _isaret(oturum, hesap, isbirligi_id, milestone_id, ISARETLE, arka_plan)


@router.post(
    "/{isbirligi_id}/milestone/{milestone_id}/isareti-geri-al",
    response_model=IsbirligiDetayi,
)
async def isareti_geri_al(
    isbirligi_id: uuid.UUID,
    milestone_id: uuid.UUID,
    hesap: Hesap = Depends(rol_gerekli(ROL_GENC, ROL_KURUM)),
    oturum: AsyncSession = Depends(get_session),
) -> IsbirligiDetayi:
    """Kendi işaretini geri alır; iki tarafça tamamlanmış adım geri açılmaz (409)."""
    return await _isaret(oturum, hesap, isbirligi_id, milestone_id, ISARETI_GERI_AL)


async def _isaret(
    oturum: AsyncSession,
    hesap: Hesap,
    isbirligi_id: uuid.UUID,
    milestone_id: uuid.UUID,
    olay: str,
    arka_plan: BackgroundTasks | None = None,
) -> IsbirligiDetayi:
    isbirligi, rol = await yazilabilir_isbirligi(oturum, hesap, isbirligi_id)
    milestone = adimi_bul(isbirligi, milestone_id)
    mevcut = Isaretler(
        genc=milestone.genc_isaret is not None, kurum=milestone.kurum_isaret is not None
    )
    try:
        sonuc = isaret_gecisi(isbirligi.durum, mevcut, olay, rol)
    except GecersizTakipGecisi as hata:
        raise HTTPException(status_code=409, detail=str(hata)) from hata
    except RolUygunDegil as hata:
        raise HTTPException(
            status_code=403, detail="Bu işlemi yalnızca iki taraf yapabilir."
        ) from hata

    if sonuc.degisti:
        simdi = _simdi()
        milestone.genc_isaret = (milestone.genc_isaret or simdi) if sonuc.isaretler.genc else None
        milestone.kurum_isaret = (
            (milestone.kurum_isaret or simdi) if sonuc.isaretler.kurum else None
        )
        milestone.durum = MILESTONE_TAMAMLANDI if sonuc.tamamlandi else MILESTONE_BEKLIYOR
        aktivite(isbirligi)
        if olay == ISARETLE:
            _isaret_bildirimleri(oturum, isbirligi, milestone, rol, sonuc.tamamlandi, simdi)
        if sonuc.tamamlandi and arka_plan is not None:
            ozeti_sirala(arka_plan, isbirligi)
    await oturum.commit()
    return detay(isbirligi, hesap)


def _isaret_bildirimleri(
    oturum: AsyncSession,
    isbirligi: Isbirligi,
    milestone: Milestone,
    rol: str,
    adim_tamamlandi: bool,
    simdi: dt.datetime,
) -> None:
    """İşaretin yan etkileri: bildirim ve (son adımsa) tamamlanma kuralı."""
    if not adim_tamamlandi:
        bildirim_ekle(
            oturum,
            taraf_hesabi(isbirligi, karsi_rol(rol)),
            TUR_ADIM_ISARETLENDI,
            f"{taraf_adi(isbirligi, rol)} “{milestone.baslik}” adımını tamamlandı olarak "
            "işaretledi; sen de onayla.",
            isbirligi.eslesme_id,
        )
        return

    if isbirligi_tamamlandi_mi([m.durum == MILESTONE_TAMAMLANDI for m in isbirligi.milestonelar]):
        # Kural karar verir, ajan değil: her adım iki tarafça onaylandı.
        isbirligi.durum = ISBIRLIGI_TAMAMLANDI
        isbirligi.tamamlanma_tarihi = simdi
        metinler = {
            ROL_GENC: f"{taraf_adi(isbirligi, ROL_KURUM)} ile iş birliğin tamamlandı; "
            "kartına tamamlanmış pilot olarak eklendi.",
            ROL_KURUM: f"{taraf_adi(isbirligi, ROL_GENC)} ile iş birliğiniz tamamlandı.",
        }
        for taraf, metin in metinler.items():
            bildirim_ekle(
                oturum,
                taraf_hesabi(isbirligi, taraf),
                TUR_ISBIRLIGI_TAMAMLANDI,
                metin,
                isbirligi.eslesme_id,
            )
        return

    for taraf in (ROL_GENC, ROL_KURUM):
        bildirim_ekle(
            oturum,
            taraf_hesabi(isbirligi, taraf),
            TUR_ADIM_TAMAMLANDI,
            f"“{milestone.baslik}” adımı iki tarafça tamamlandı.",
            isbirligi.eslesme_id,
        )


# --- Durum özeti (§ 5) — kesilebilir iş --------------------------------------------------
#
# Yalnızca iki yerden sıraya konur (plan onaylanınca, adım tamamlanınca) ve
# yanıttan sonra çalışır. Başarısız olursa `durum_ozeti` boş ya da eski kalır;
# hiçbir kural ona bakmaz. Bu bölüm silinirse döngü aynen çalışır.


def ozeti_sirala(arka_plan: BackgroundTasks, isbirligi: Isbirligi) -> None:
    arka_plan.add_task(ozeti_arka_planda_yaz, isbirligi.id)


async def ozeti_arka_planda_yaz(isbirligi_id: uuid.UUID) -> None:
    async with get_sessionmaker()() as oturum:
        try:
            isbirligi = await isbirligini_getir(oturum, isbirligi_id)
            if isbirligi is None:
                return
            eslesme = isbirligi.eslesme
            girdi = takip.ozet_girdisi(
                durum=isbirligi.durum,
                genc_adi=sahiplik.taraf_adi(eslesme, sahiplik.TARAF_ADAY),
                kurum_adi=eslesme.ihtiyac_karti.kurum.ad,
                aday_etiketi="ortak firma" if eslesme.firma_karti_id else "genç",
                adimlar=[
                    takip.AdimDurumu(
                        baslik=m.baslik,
                        hedef_tarih=m.hedef_tarih,
                        genc_isaretledi=m.genc_isaret is not None,
                        kurum_isaretledi=m.kurum_isaret is not None,
                    )
                    for m in sorted(isbirligi.milestonelar, key=lambda m: m.sira)
                ],
                son_hareket=eslesme.son_aktivite_tarihi.date()
                if eslesme.son_aktivite_tarihi
                else None,
                bugun=dt.date.today(),
            )
            metin = await takip.durum_ozeti_yaz(girdi)
            if metin is None:
                return
            # Yalnızca özet alanları: LLM beklenirken yapılan başka bir
            # değişikliği ezmesin diye satırın geri kalanına dokunulmuyor.
            await oturum.execute(
                update(Isbirligi)
                .where(Isbirligi.id == isbirligi_id)
                .values(durum_ozeti=metin, ozet_tarihi=_simdi())
            )
            await oturum.commit()
        except Exception:
            logger.exception("Durum özeti yazılamadı (%s)", isbirligi_id)
