"""Değerlendirme notu: son puanlardan şablonla (docs/dogrulama.md § 11.3).

Not sayılarla hiçbir zaman çelişmez, çünkü onlardan kurulur; hitap ("sen") ve
terimler rehbere sabittir (docs/icerik-rehberi.md). Referans başlığı notta yok:
referans sonradan yanıt verdiğinde not eskirdi; referans durumu kanıt
bölümünde ayrıca görünüyor. Modelin tek cümlelik önerisi dil denetiminden
geçemezse atılır.
"""

from __future__ import annotations

from app.agents.dogrulama.kurallar import BaslikPuanlari, OkunanKanit
from app.core.kanit_okuma.belge import ErisimDurumu, KaynakSeviyesi
from app.core.kullanici_dili import metin_ihlalleri

_OKUNAMADI: dict[ErisimDurumu, str] = {
    ErisimDurumu.GIRIS_GEREKLI: "Linkin yalnızca giriş yapanlara açık; içeriğini göremedik.",
    ErisimDurumu.ENGELLENDI: "Siteye otomatik olarak ulaşamadık; bu senin hatan değil.",
    ErisimDurumu.ICERIK_YOK: "Sayfa açıldı ama içeriği okunamadı.",
    ErisimDurumu.HATA: "Linke şu an ulaşılamadı; daha sonra yeniden denenecek.",
}


_KANIT_ADI = {"link": "link", "dosya": "dosya", "gorsel": "görsel"}


def kanit_cumlesi(puan: int | None, okunan: OkunanKanit | None, *, celisiyor: bool) -> str:
    if okunan is None:
        return "Henüz kanıt eklemedin."
    # Yüklenen dosya ve görsele "link" demek yanlış okunuyordu.
    ad = _KANIT_ADI.get(okunan.tur, "link")
    if ad != "link":
        return _belge_cumlesi(ad, puan, okunan, celisiyor=celisiyor)
    if puan is None:
        return _OKUNAMADI.get(okunan.erisim, "Kanıt değerlendirilemedi.")
    if okunan.erisim is ErisimDurumu.BULUNAMADI:
        return "Bu adreste bir sayfa bulunamadı."
    if okunan.erisim is ErisimDurumu.GUVENSIZ:
        return "Bu adres herkese açık bir web sayfası değil."
    if puan == 0:
        return "Eklediğin link bu çalışmayla ilgili görünmüyor."
    if celisiyor:
        return "Kanıttaki bilgiler anlattığınla örtüşmüyor."
    if okunan.seviye is KaynakSeviyesi.BEYAN:
        return "Belgen çalışmanla ilgili ama doğrulanabilir bir işaret taşımıyor."
    if puan == 2:
        return "Link çalışmana götürüyor ama sana ait olduğunu gösteren bir işaret yok."
    return "Link çalışmana götürüyor ve senin olduğu görülüyor."


def _belge_cumlesi(ad: str, puan: int | None, okunan: OkunanKanit, *, celisiyor: bool) -> str:
    """Yüklenen dosya ve görselin kanıt cümlesi; kural `kanit_cumlesi` ile aynı."""
    if puan is None:
        return f"Yüklediğin {ad} değerlendirilemedi."
    if puan == 0:
        return f"Yüklediğin {ad} bu çalışmayla ilgili görünmüyor."
    if celisiyor:
        return "Kanıttaki bilgiler anlattığınla örtüşmüyor."
    if okunan.seviye is KaynakSeviyesi.BEYAN:
        return f"Yüklediğin {ad} çalışmanla ilgili ama doğrulanabilir bir işaret taşımıyor."
    if puan == 2:
        return f"Yüklediğin {ad} çalışmanla ilgili ama sana ait olduğunu gösteren bir işaret yok."
    return f"Yüklediğin {ad} çalışmanla ilgili ve senin olduğu görülüyor."


def sonuc_cumlesi(puan: int | None) -> str:
    return {
        None: "Sonuç henüz değerlendirilmedi.",
        0: "Çalışmanın sonucunu yazmamışsın.",
        1: "Sonucu sayıyla anlatırsan daha güçlü görünür.",
        2: "Sonucun sayıyla yazılmış ama henüz bağımsız bir kaynak doğrulamadı.",
        3: "Sonucun ölçülebilir ve bağımsız bir kaynakla doğrulanıyor.",
    }[puan]


def rol_cumlesi(puan: int | None) -> str:
    return {
        None: "Payın henüz değerlendirilmedi.",
        0: "Bu çalışmada senin ne yaptığını yazmamışsın.",
        1: "Payını daha somut yazarsan (ör. hangi bölümü sen yaptın) güçlenir.",
        2: "Payın açık ama henüz bağımsız bir kaynak doğrulamadı.",
        3: "Payın açık ve doğrulanıyor.",
    }[puan]


def temiz_oneri(oneri: str | None) -> str | None:
    """Modelin önerisi rehbere uyuyorsa (sen hitabı, yasak terim yok) kullanılır."""
    if not oneri or not oneri.strip():
        return None
    return None if metin_ihlalleri(oneri, hitap="sen") else oneri.strip()


def not_yaz(
    puanlar: BaslikPuanlari,
    okunan: OkunanKanit | None,
    *,
    kanit_celisiyor: bool,
    oneri: str | None,
) -> str:
    cumleler = [
        f"Kanıt: {kanit_cumlesi(puanlar.kanit, okunan, celisiyor=kanit_celisiyor)}",
        f"Sonuç: {sonuc_cumlesi(puanlar.sonuc)}",
        f"Rol: {rol_cumlesi(puanlar.rol)}",
    ]
    if (temiz := temiz_oneri(oneri)) is not None:
        cumleler.append(temiz)
    return " ".join(cumleler)
