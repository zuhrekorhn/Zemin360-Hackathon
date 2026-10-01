"""Kayıt, giriş ve /me (docs/faz-b-kimlik-ve-dongu.md § 1-2).

Kayıt hesabı ve boş profili birlikte açar: genç için `kullanici(ad)`, kurum
için `kurum(ad)`. Profilin e-postası iletişim bilgisidir, hesap e-postasıyla
doldurulur. GİRVAK hesabı buradan açılamaz; `scripts/girvak_hesabi.py`
aynı `hesap_olustur` fonksiyonunu kullanır.
"""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.bildirimler import okunmamis_sayisi
from app.api.kimlik import mevcut_hesap
from app.api.profil import (
    firma_profilini_uygula,
    firmanin_eksikleri,
    profili_uygula,
    profilin_eksikleri,
)
from app.core.kimlik import sifre_dogru_mu, sifre_hashle, token_uret
from app.core.metin import eposta_normalize
from app.db.session import get_session
from app.models.firma_karti import FirmaKarti
from app.models.hesap import ROL_GENC, ROL_KURUM, Hesap
from app.models.ihtiyac_karti import IhtiyacKarti
from app.models.kullanici import Kullanici
from app.models.kurum import Kurum
from app.schemas.auth import (
    GirisIstegi,
    IhtiyacKartiOzeti,
    KayitIstegi,
    MeYaniti,
    TokenYaniti,
    YetenekKartiOzeti,
)
from app.schemas.profil import FirmaKayitProfili, GencKayitProfili
from app.servisler import kimlik_dogrulama

router = APIRouter(tags=["kimlik"])

EPOSTA_KAYITLI = "Bu e-posta ile zaten bir hesap var. Giriş yapmayı dene."
GIRIS_HATALI = "E-posta ya da şifre eşleşmedi."


class EpostaKayitli(Exception):
    """Aynı e-postayla hesap ya da profil zaten var."""


async def hesap_olustur(
    oturum: AsyncSession,
    *,
    email: str,
    sifre: str,
    rol: str,
    ad: str | None,
    genc_profili: GencKayitProfili | None = None,
    firma_profili: FirmaKayitProfili | None = None,
    kvkk_onay: bool = False,
    eposta_dogrulandi: bool = False,
) -> Hesap:
    """Hesabı ve (genç/kurum için) profilini açar, commit eder.

    E-posta normalize edilir. Aynı e-posta bir hesapta ya da Faz B öncesinden
    kalan hesapsız bir profilde varsa `EpostaKayitli`. Hesapsız profil
    sahiplenilmez: e-posta doğrulaması yok, başkasının eski kartlarını
    e-postasını yazarak almak mümkün olmamalı.

    Profil ve `kvkk_onay` uçta zorunlu (şema); burada isteğe bağlı,
    çünkü betikler ve testler profili ayrıca kuruyor. `eposta_dogrulandi`
    yalnızca betikler içindir (demo ve GİRVAK hesapları doğrulanmış açılır).
    """
    email = eposta_normalize(email)
    simdi = dt.datetime.now(dt.UTC)
    hesap = Hesap(
        email=email,
        sifre_hash=sifre_hashle(sifre),
        rol=rol,
        kvkk_onay_tarihi=simdi if kvkk_onay else None,
        eposta_dogrulandi_tarihi=simdi if eposta_dogrulandi else None,
    )
    oturum.add(hesap)
    try:
        await oturum.flush()
        if rol == ROL_GENC:
            kullanici = Kullanici(hesap_id=hesap.id, ad=ad, email=email)
            if genc_profili is not None:
                profili_uygula(kullanici, genc_profili.model_dump())
            oturum.add(kullanici)
        elif rol == ROL_KURUM:
            kurum = Kurum(hesap_id=hesap.id, ad=ad, iletisim_email=email)
            if firma_profili is not None:
                firma_profilini_uygula(kurum, firma_profili.model_dump())
            oturum.add(kurum)
        await oturum.commit()
    except IntegrityError as hata:
        await oturum.rollback()
        raise EpostaKayitli(email) from hata
    return hesap


@router.post("/auth/kayit", response_model=TokenYaniti, status_code=201)
async def kayit(
    istek: KayitIstegi, arka_plan: BackgroundTasks, oturum: AsyncSession = Depends(get_session)
) -> TokenYaniti:
    """Hesap açar; kayıtla birlikte giriş yapılmış olur (token döner).

    Doğrulama bağlantısı aynı istekte yazılır, e-posta yanıttan sonra gider:
    gönderim hatası kaydı düşürmez, kullanıcı menüden yeni bağlantı ister.
    """
    try:
        hesap = await hesap_olustur(
            oturum,
            email=str(istek.email),
            sifre=istek.sifre,
            rol=istek.rol,
            ad=istek.ad,
            genc_profili=istek.genc_profili,
            firma_profili=istek.firma_profili,
            kvkk_onay=istek.kvkk_onay,
        )
    except EpostaKayitli as hata:
        raise HTTPException(status_code=409, detail=EPOSTA_KAYITLI) from hata
    dogrulama_tokeni = await kimlik_dogrulama.baglanti_olustur(oturum, hesap)
    await oturum.commit()
    arka_plan.add_task(
        kimlik_dogrulama.epostayi_gonder,
        kimlik_dogrulama.dogrulama_epostasi(hesap, dogrulama_tokeni),
    )
    return TokenYaniti(token=token_uret(hesap.id, hesap.rol), hesap_id=hesap.id, rol=hesap.rol)


@router.post("/auth/giris", response_model=TokenYaniti)
async def giris(istek: GirisIstegi, oturum: AsyncSession = Depends(get_session)) -> TokenYaniti:
    """Yanlış e-posta da yanlış şifre de aynı 401'i alır; hangisi olduğu söylenmez."""
    hesap = await oturum.scalar(
        select(Hesap).where(Hesap.email == eposta_normalize(str(istek.email)))
    )
    # Hesap yoksa da şifre karşılaştırması yapılır (sahte hash'le): yanıt süresi
    # e-postanın kayıtlı olup olmadığını ele vermesin.
    if not sifre_dogru_mu(hesap.sifre_hash if hesap else None, istek.sifre) or hesap is None:
        raise HTTPException(
            status_code=401, detail=GIRIS_HATALI, headers={"WWW-Authenticate": "Bearer"}
        )
    return TokenYaniti(token=token_uret(hesap.id, hesap.rol), hesap_id=hesap.id, rol=hesap.rol)


@router.get("/me", response_model=MeYaniti)
async def me(
    hesap: Hesap = Depends(mevcut_hesap), oturum: AsyncSession = Depends(get_session)
) -> MeYaniti:
    yanit = MeYaniti(
        hesap_id=hesap.id,
        email=hesap.email,
        rol=hesap.rol,
        ad=None,
        okunmamis_bildirim=await okunmamis_sayisi(oturum, hesap.id),
        eposta_dogrulandi=kimlik_dogrulama.dogrulandi_mi(hesap),
    )

    if hesap.kullanici is not None:
        kullanici = await oturum.scalar(
            select(Kullanici)
            .options(selectinload(Kullanici.yetenek_karti))
            .where(Kullanici.id == hesap.kullanici.id)
        )
        yanit.ad = kullanici.ad
        yanit.kullanici_id = kullanici.id
        yanit.eksik_profil_alanlari = profilin_eksikleri(kullanici)
        yanit.kvkk_onayli = hesap.kvkk_onay_tarihi is not None
        if (kart := kullanici.yetenek_karti) is not None:
            yanit.yetenek_karti = YetenekKartiOzeti(
                id=kart.id,
                rol_alani=kart.rol_alani,
                deneyim_seviyesi=kart.deneyim_seviyesi,
                kanit_bekleyen=kart.kanit_bekleyen,
                embedding_var=kart.embedding is not None,
            )

    if hesap.kurum is not None:
        kartlar = await oturum.scalars(
            select(IhtiyacKarti)
            .where(IhtiyacKarti.kurum_id == hesap.kurum.id)
            .order_by(IhtiyacKarti.olusturma_tarihi.desc())
        )
        yanit.ad = hesap.kurum.ad
        yanit.kurum_id = hesap.kurum.id
        yanit.eksik_profil_alanlari = firmanin_eksikleri(hesap.kurum)
        yanit.firma_karti_var = bool(
            await oturum.scalar(
                select(func.count())
                .select_from(FirmaKarti)
                .where(FirmaKarti.kurum_id == hesap.kurum.id)
            )
        )
        yanit.kvkk_onayli = hesap.kvkk_onay_tarihi is not None
        yanit.ihtiyac_kartlari = [
            IhtiyacKartiOzeti(
                id=kart.id,
                problem_tanimi=kart.problem_tanimi,
                olusturma_tarihi=kart.olusturma_tarihi,
                embedding_var=kart.embedding is not None,
                durum=kart.durum,
                aranan=kart.aranan,
            )
            for kart in kartlar
        ]

    return yanit
