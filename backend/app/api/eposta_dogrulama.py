"""Kayıt e-postasının doğrulanması (docs/dogrulama.md § 6.3).

Bağlantıyı açan kişi giriş yapmış olmak zorunda değil (e-postayı başka
cihazda açabilir): kimliği bağlantının kendisi taşır. Yeni bağlantı isteği
giriş ister. Orkestrasyon `app/servisler/kimlik_dogrulama.py`'de.
"""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.kimlik import mevcut_hesap
from app.db.session import get_session
from app.models.hesap import Hesap
from app.schemas.auth import EpostaDogrulamaIstegi, EpostaDogrulamaYaniti
from app.servisler import kart_hazirlama, kimlik_dogrulama

router = APIRouter(tags=["kimlik"])

ZATEN_DOGRULANDI = "E-posta adresin zaten doğrulanmış."


@router.post("/auth/eposta-dogrula", response_model=EpostaDogrulamaYaniti)
async def eposta_dogrula(
    istek: EpostaDogrulamaIstegi,
    arka_plan: BackgroundTasks,
    oturum: AsyncSession = Depends(get_session),
) -> EpostaDogrulamaYaniti:
    """Geçersiz ya da süresi dolmuş bağlantı 400; aynı bağlantının tekrarı 200.
    Gencin çapalı dosyaları varsa kalemleri arka planda yeniden okunur (kimlik koşulu)."""
    try:
        hesap = await kimlik_dogrulama.dogrula(oturum, istek.token)
    except kimlik_dogrulama.BaglantiGecersiz as hata:
        raise HTTPException(status_code=400, detail=str(hata)) from hata
    kart_id = await kimlik_dogrulama.dogrulama_sonrasi_kart(oturum, hesap)
    await oturum.commit()
    if kart_id is not None:
        arka_plan.add_task(kart_hazirlama.kalemleri_yeniden_oku, kart_id)
    return EpostaDogrulamaYaniti(eposta_dogrulandi=True)


@router.post("/auth/eposta-dogrulama/yeniden", status_code=202)
async def dogrulama_baglantisini_yeniden_gonder(
    arka_plan: BackgroundTasks,
    hesap: Hesap = Depends(mevcut_hesap),
    oturum: AsyncSession = Depends(get_session),
) -> None:
    """Yeni bağlantı gönderir, eskisi geçersiz olur. Zaten doğrulanmışsa 409, sık istekte 429."""
    try:
        token = await kimlik_dogrulama.yeniden_baglanti_olustur(oturum, hesap)
    except kimlik_dogrulama.ZatenDogrulandi as hata:
        raise HTTPException(status_code=409, detail=ZATEN_DOGRULANDI) from hata
    except kimlik_dogrulama.CokSikIstek as hata:
        raise HTTPException(status_code=429, detail=str(hata)) from hata
    await oturum.commit()
    arka_plan.add_task(
        kimlik_dogrulama.epostayi_gonder, kimlik_dogrulama.dogrulama_epostasi(hesap, token)
    )
