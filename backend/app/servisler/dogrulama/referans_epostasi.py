"""Referans kişiye giden e-postalar: istek ve tek hatırlatma (plan § 7).

Yanıt bağlantısı yalnızca bu e-postada bulunur; hiçbir API yanıtı token
taşımaz (bulgu 31). Referans kişiye "siz" diye hitap edilir (firmaya giden
metinlerle aynı, docs/icerik-rehberi.md). Gönderim yanıttan sonra arka planda;
hata akışı düşürmez (İ9).
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote

from app.core.config import get_settings
from app.core.dis_servisler import kurulum
from app.core.dis_servisler.eposta import Eposta, dusmeden_gonder


@dataclass(frozen=True)
class ReferansEpostaBaglami:
    alici: str
    token: str
    genc_adi: str
    baslik: str


def yanit_baglantisi(token: str) -> str:
    return f"{get_settings().uygulama_adresi.rstrip('/')}/referans?token={quote(token)}"


def istek_epostasi(b: ReferansEpostaBaglami, gecerlilik_gun: int) -> Eposta:
    return Eposta(
        alici=b.alici,
        konu=f"Zemin360: {b.genc_adi} sizi referans gösterdi",
        metin=(
            "Merhaba,\n\n"
            f"{b.genc_adi}, Zemin360'taki yetenek kartına eklediği “{b.baslik}” "
            "çalışması için sizi referans gösterdi. Çalışmanın anlatıldığı gibi olup "
            "olmadığını dört kısa soruyla söylemeniz yeterli; üye olmanız gerekmiyor.\n\n"
            f"{yanit_baglantisi(b.token)}\n\n"
            f"Bağlantı {gecerlilik_gun} gün geçerli ve tek kullanımlık. "
            f"{b.genc_adi} adlı kişiyi tanımıyorsanız bu e-postayı yok sayabilirsiniz."
        ),
    )


def hatirlatma_epostasi(b: ReferansEpostaBaglami, kalan_gun: int) -> Eposta:
    return Eposta(
        alici=b.alici,
        konu=f"Zemin360: {b.genc_adi} için referans yanıtınız bekleniyor",
        metin=(
            "Merhaba,\n\n"
            f"{b.genc_adi}, “{b.baslik}” çalışması için sizden referans istemişti. "
            "Yanıt vermeye vaktiniz olduysa bağlantı hâlâ açık:\n\n"
            f"{yanit_baglantisi(b.token)}\n\n"
            f"Bağlantı {kalan_gun} gün daha geçerli. Yanıt vermemeniz kimse için "
            "olumsuz bir işaret sayılmaz; bu tek hatırlatmamız."
        ),
    )


async def epostalari_gonder(epostalar: list[Eposta]) -> None:
    """Arka plan işi (ya da taramada commit'ten sonra): hata yutulur, akış sürer."""
    gonderici = kurulum.eposta_gonderici()
    for eposta in epostalar:
        await dusmeden_gonder(gonderici, eposta)
