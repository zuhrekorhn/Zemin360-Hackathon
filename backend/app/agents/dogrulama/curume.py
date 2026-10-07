"""Link çürümesi kuralları (docs/dogrulama.md § 10.4). Saf: ağ, model ve veritabanı yok.

Bir kanıt linki zamanla silinebilir ya da gizlenebilir. Haftalık yoklama
(Canlılık taraması) linki yeniden açar ve bir sayaç tutar:
  - yalnızca `BULUNAMADI` ve `GIRIS_GEREKLI` sayılır (link silinmiş ya da gizlenmiş);
  - `ENGELLENDI` ve `HATA` sayılmaz (bot engeli, geçici arıza): sayaç olduğu gibi kalır;
  - `ACIK` sayacı sıfırlar.
Üst üste `CURUME_ESIGI` sayılan sonuçtan sonra link çürümüş sayılır: o parça
Kanıt'a girmez (başlıkta "—"), gence bildirim gider, önceki puan saklanır.

Yoklama yalnızca eskiden açık okunmuş linke yapılır: baştan giriş isteyen
(LinkedIn gibi) ya da hiç bulunamayan link zaten "—" ya da 0 almıştı, onun
"çürümesi" gence yanlış bir haber olurdu.
"""

from __future__ import annotations

import datetime as dt

from app.core.kanit_okuma.belge import ErisimDurumu

CURUME_ESIGI = 3
YOKLAMA_ARALIGI_GUN = 7

SAYILANLAR = frozenset({ErisimDurumu.BULUNAMADI, ErisimDurumu.GIRIS_GEREKLI})


def sayac_gecisi(sayac: int, erisim: ErisimDurumu) -> int:
    """Yeni yoklama sonucundan sonraki sayaç."""
    if erisim is ErisimDurumu.ACIK:
        return 0
    if erisim in SAYILANLAR:
        return sayac + 1
    return sayac


def curumus_mu(sayac: int) -> bool:
    return sayac >= CURUME_ESIGI


def yoklanacak_mi(
    erisim: str | None,
    sayac: int,
    son_yoklama: dt.datetime | None,
    simdi: dt.datetime,
    *,
    isleme_bekliyor: bool = False,
) -> bool:
    """Link bu taramada yoklanır mı?

    `isleme_bekliyor`: sayaç eşiği geçmiş ama sonucu (bildirim, yeniden
    değerlendirme) henüz işlenmemiş; beklemeden yeniden denenir.
    """
    if erisim != ErisimDurumu.ACIK.value and sayac == 0:
        return False
    if isleme_bekliyor:
        return True
    return son_yoklama is None or simdi - son_yoklama >= dt.timedelta(days=YOKLAMA_ARALIGI_GUN)
