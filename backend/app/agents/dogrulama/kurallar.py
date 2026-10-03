"""Doğrulamanın saf kuralları: referans puanı, üçüncü taraf onayı, yeniden
isteme ve otomatik puanlama. LLM, ağ ve veritabanı yok; tabloyla test edilir.
"""

from __future__ import annotations

import datetime as dt
import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from app.agents.dogrulama.referans_durumu import (
    DURUM_BEKLIYOR,
    DURUM_GERI_CEKILDI,
    DURUM_YANITLANDI,
)
from app.core.kanit_okuma.belge import ErisimDurumu, KaynakSeviyesi, SahiplikKaynagi

# 1-5 referans skalasını rubriğin 0-3 aralığına indirger.
# 3 ("ne iyi ne kötü") bir onay değildir, o yüzden 2'den fazlasını vermiyor;
# tam puan yalnızca açık bir olumlu referansta (5) veriliyor.
REFERANS_PUAN_ESLEMESI = {1: 0, 2: 1, 3: 1, 4: 2, 5: 3}


def referans_puanina_cevir(skala_1_5: int) -> int:
    """Referansın 1-5 puanını rubriğin 0-3 aralığına indirger."""
    if skala_1_5 not in REFERANS_PUAN_ESLEMESI:
        raise ValueError("Referans puanı 1-5 aralığında olmalı")
    return REFERANS_PUAN_ESLEMESI[skala_1_5]


def ucuncu_taraf_onayi_hesapla(puanlar: Sequence[int]) -> int | None:
    """Yanıtlamış tüm referanslardan tek bir 0-3 puanı üretir; yanıt yoksa None ("—").

    "Yanıt yok" ile "olumsuz yanıt" (0) ayrı şeylerdir: ikisi de 0 olsaydı
    referans istememiş genç, olumsuz yanıt almış gibi görünürdü (bulgu 19).

    Ortalama alınıyor, en yüksek değil: en yüksek, "olumlu diyen birini
    bulana kadar referans sor" davranışını ödüllendirirdi. Ortalama, zayıf
    bir referansın puanı aşağı çekmesine izin verir — göstergenin işi
    sinyal taşımak, parlatmak değil.

    Ortalama normal (0.5 yukarı) yuvarlanıyor: aşağı yuvarlamak iki güçlü
    referansı (5+4 → 2.5 → 2) tek bir 5'ten (3) daha düşük gösteriyordu.
    Referans eklemek puanı düşürmemeli. Python'ın round()'u 2.5'i 2'ye
    çevirdiği için (bankacı yuvarlaması) elle +0.5 uygulanıyor.
    """
    return _ortalama([referans_puanina_cevir(p) for p in puanlar])


def _ortalama(degerler: Sequence[float]) -> int | None:
    """0-3 değerlerin ortalaması, 0.5 yukarı yuvarlanır; değer yoksa None ("—")."""
    if not degerler:
        return None
    return math.floor(sum(degerler) / len(degerler) + 0.5)


# --- 4 soruluk form (docs/plans/dogrulama-iyilestirme.md § 7) ------------------------------
# (2) çalışma, (3) pay, (4) sonuç için yanıtlar. "Bilmiyorum" bir değerlendirme değil:
# ortalamaya girmez. "Kısmen" 1: anlatılanın bir kısmı doğruysa iddia büyütülmüş demektir.

YANIT_EVET, YANIT_KISMEN, YANIT_HAYIR, YANIT_BILMIYORUM = "evet", "kismen", "hayir", "bilmiyorum"
YANITLAR = (YANIT_EVET, YANIT_KISMEN, YANIT_HAYIR, YANIT_BILMIYORUM)
YANIT_PUANLARI = {YANIT_EVET: 3, YANIT_KISMEN: 1, YANIT_HAYIR: 0}

ILISKILER = ("yonetici", "takim_arkadasi", "ogretmen_danisman", "musteri", "diger")


ZATEN_BEKLENIYOR = "Bu kişiden yanıt zaten bekleniyor."


def referans_yeniden_istenebilir_mi(
    *, durum: str, guncel: bool, ayni_kisiden_bekleyen_var: bool
) -> str | None:
    """ "Referansı yeniden iste" bu istek için anlamlı mı? Değilse nedeni (409).

    Anlamlı olduğu durumlar: yanıt iş kaleminin önceki hâline verildi (geçmiş),
    ya da süresi doldu (yanıt yok). Aynı kişiden güncel bir yanıt zaten
    bekleniyorsa ikinci istek açılmaz.
    """
    if ayni_kisiden_bekleyen_var:
        return ZATEN_BEKLENIYOR
    if durum == DURUM_BEKLIYOR:
        return ZATEN_BEKLENIYOR
    if durum == DURUM_YANITLANDI and guncel:
        return "Bu referans işin güncel hâli için zaten yanıt verdi."
    if durum == DURUM_GERI_CEKILDI:
        return "Geri çektiğin istek yeniden gönderilmez. Doğru adresle yeni bir referans iste."
    return None


# --- Referans yanıtının geçerliliği (docs/plans/genc-akisi.md § 0, karar 8) ---------
# İş kalemi değişince eski yanıt geçmişte kalır, puana girmez. Kart düzenleme
# (sıfırlama) ve Doğrulama (üçüncü taraf onayı) aynı kuralı buradan kullanır.


@dataclass(frozen=True)
class ReferansYaniti:
    # Eski 1-5 yanıt; 4 soruluk formla gelen yanıtta None.
    puan: int | None
    yanit_tarihi: dt.datetime | None
    iddia: str | None = None
    pay: str | None = None
    sonuc: str | None = None

    @property
    def yanitlandi(self) -> bool:
        return self.puan is not None or any((self.iddia, self.pay, self.sonuc))


def referans_gecerli_mi(
    yanit_tarihi: dt.datetime | None, icerik_tarihi: dt.datetime | None
) -> bool:
    """Bu referans yanıtı iş kaleminin güncel hâli için mi verildi?

    İçerik hiç değişmediyse (NULL) bütün yanıtlar geçerli, eski satırlar dahil.
    Değiştiyse yalnızca değişiklikten sonra verilen yanıt geçerli; tarihi
    bilinmeyen eski yanıt geçmişte kalır.
    """
    if icerik_tarihi is None:
        return True
    return yanit_tarihi is not None and yanit_tarihi >= icerik_tarihi


def gecerli_referans_yanitlari(
    yanitlar: Iterable[ReferansYaniti], icerik_tarihi: dt.datetime | None
) -> list[ReferansYaniti]:
    """Göstergeye girecek yanıtlar (yanıtlanmış ve güncel)."""
    return [
        y for y in yanitlar if y.yanitlandi and referans_gecerli_mi(y.yanit_tarihi, icerik_tarihi)
    ]


def referans_yanit_puani(yanit: ReferansYaniti) -> float | None:
    """Bir kişinin yanıtının 0-3 değeri; yalnızca "bilmiyorum" dediyse None.

    Eski 1-5 yanıt `REFERANS_PUAN_ESLEMESI` ile okunur. Formda kişinin bilinen
    yanıtlarının ortalaması alınır: her referans kişi ortalamaya bir kez girer,
    çok soruya yanıt veren daha ağır basmaz.
    """
    if yanit.puan is not None:
        return referans_puanina_cevir(yanit.puan)
    bilinen = [
        YANIT_PUANLARI[y] for y in (yanit.iddia, yanit.pay, yanit.sonuc) if y in YANIT_PUANLARI
    ]
    return sum(bilinen) / len(bilinen) if bilinen else None


def referans_basligi(yanitlar: Iterable[ReferansYaniti]) -> int | None:
    """Referans başlığı: güncel yanıtların kişi başına ortalaması (0.5 yukarı).

    Yanıt yoksa ya da herkes "bilmiyorum" dediyse None ("—"), 0 değil (bulgu 19).
    """
    puanlar = [p for p in map(referans_yanit_puani, yanitlar) if p is not None]
    return _ortalama(puanlar)


@dataclass(frozen=True)
class ReferansDestegi:
    """Referansın Sonuç ve Rol'e bağımsız desteği (§ 7): ilgili soruya "evet"."""

    sonuc: bool = False
    pay: bool = False


def referans_destegi(yanitlar: Iterable[ReferansYaniti]) -> ReferansDestegi:
    """Güncel yanıtlardan birinin "evet"i yeter: destek bir kanıt gibidir, oylama değil.

    Aynı kalemdeki "hayır" başlığın ortalamasını zaten düşürür."""
    liste = list(yanitlar)
    return ReferansDestegi(
        sonuc=any(y.sonuc == YANIT_EVET for y in liste),
        pay=any(y.pay == YANIT_EVET for y in liste),
    )


# --- Güç işaretleri (puan değil, satırda görünür; § 7) ---------------------------------------
# Ücretsiz posta sağlayıcısı dışındaki alan adı "kurumsal" sayılır. Plan alan adının
# kuruluşun web sitesiyle aynı olmasını söylüyor; kalemde kuruluşun sitesi tutulmadığı
# için bugünkü yaklaşım bu (bilinen sınır, plan § 18).
UCRETSIZ_POSTA = frozenset(
    {
        "gmail.com",
        "googlemail.com",
        "hotmail.com",
        "hotmail.com.tr",
        "outlook.com",
        "outlook.com.tr",
        "live.com",
        "msn.com",
        "yahoo.com",
        "yahoo.com.tr",
        "yandex.com",
        "yandex.com.tr",
        "icloud.com",
        "me.com",
        "proton.me",
        "protonmail.com",
        "gmx.com",
        "mail.com",
        "aol.com",
    }
)
GUC_KURUMSAL = "kurumsal_eposta"
GUC_EGITIM = "egitim_eposta"


def eposta_gucu(eposta: str) -> str | None:
    """Referans adresinin güç işareti: eğitim kurumu, kurumsal ya da yok."""
    alan = eposta.rsplit("@", 1)[-1].strip().lower()
    if alan.endswith(".edu.tr") or alan.endswith(".edu"):
        return GUC_EGITIM
    if alan in UCRETSIZ_POSTA:
        return None
    return GUC_KURUMSAL


# --- Puan kuralları (docs/plans/dogrulama-iyilestirme.md § 2, § 11.2) ---------------------
# Model gerçekleri çıkarır (cikarim.py), puanı buradaki saf fonksiyonlar verir: aynı
# gerçekler her zaman aynı puanı üretir ve kural tabloyla test edilir.

# Kanıt başlığının seviye tavanı. Çapasız yüklenmiş dosya (D) 1; kamuya açık çalışma
# (C) 2; bağlı hesap ya da düzenleyen (B, A) 3. Yazılmış iddia metni kanıt değildir:
# hiç parça yoksa Kanıt "—".
KANIT_TAVANI: dict[KaynakSeviyesi, int] = {
    KaynakSeviyesi.BEYAN: 1,
    KaynakSeviyesi.KAMUYA_ACIK: 2,
    KaynakSeviyesi.PLATFORM: 3,
    KaynakSeviyesi.DUZENLEYEN: 3,
}
BAGIMSIZ_SEVIYELER = frozenset({KaynakSeviyesi.PLATFORM, KaynakSeviyesi.DUZENLEYEN})
CELISKI_TAVANI = 1


@dataclass(frozen=True)
class OkunanKanit:
    """Bir kanıt parçasının okunuşu (adım 5'te okuyucu zinciri üretir)."""

    erisim: ErisimDurumu
    seviye: KaynakSeviyesi
    metin: str
    url: str | None = None
    # Bağlı hesapta tek katkıcılı repo / tek yazarlı yazı / bağlı portfolyo (§ 2).
    bireysel: bool = False
    platform: str | None = None
    # Modelin göreceği metin (uzun metinde seçilmiş parçalar); yoksa `metin`.
    model_metni: str | None = None
    # Metnin platformun ölçtüğü kısmı (`KanitBelgesi.platform_metni`).
    platform_metni: str = ""
    # Seviyeyi neyin belirlediği (bağlı hesap yöntemi ya da yok; § 6).
    sahiplik_kaynagi: SahiplikKaynagi = SahiplikKaynagi.YOK
    # ParcaTuru: link | dosya | gorsel
    tur: str = "link"


@dataclass(frozen=True)
class BaslikPuanlari:
    kanit: int | None
    sonuc: int | None
    rol: int | None


def kanit_puani(okunan: OkunanKanit | None, *, ilgili: bool, celisiyor: bool) -> int | None:
    """Kanıt: iş var mı, bu kişinin mi? None = "—" (kanıt yok ya da okunamadı)."""
    if okunan is None or okunan.erisim.okunamadi_mi:
        return None
    if okunan.erisim in (ErisimDurumu.BULUNAMADI, ErisimDurumu.GUVENSIZ):
        return 0
    if not ilgili:
        return 0
    tavan = KANIT_TAVANI[okunan.seviye]
    return min(tavan, CELISKI_TAVANI) if celisiyor else tavan


def sonuc_puani(
    *, var: bool, sayisal: bool, olcut_acik: bool, bagimsiz_destek: bool, celisiyor: bool
) -> int:
    """Sonuç: açık yazılmış en çok 2; 3 için bağımsız destek (B/A kanıtı ya da referans)."""
    if not var:
        return 0
    puan = 1 if not sayisal else 3 if (olcut_acik and bagimsiz_destek) else 2
    return min(puan, CELISKI_TAVANI) if celisiyor else puan


def rol_puani(*, var: bool, ozgul: bool, bagimsiz_destek: bool, celisiyor: bool) -> int:
    """Rol: özgül yazılmış en çok 2; 3 için bağımsız destek (bireysel kural, B/A, referans)."""
    if not var:
        return 0
    puan = 1 if not ozgul else 3 if bagimsiz_destek else 2
    return min(puan, CELISKI_TAVANI) if celisiyor else puan


def kalem_puani(parcalar: Iterable[BaslikPuanlari]) -> BaslikPuanlari:
    """Başlık başına en güçlü parça; parçalar toplanmaz (kanıt eklemek puanı düşürmez)."""
    liste = list(parcalar)

    def en_guclu(degerler: Iterable[int | None]) -> int | None:
        dolu = [d for d in degerler if d is not None]
        return max(dolu) if dolu else None

    return BaslikPuanlari(
        kanit=en_guclu(p.kanit for p in liste),
        sonuc=en_guclu(p.sonuc for p in liste),
        rol=en_guclu(p.rol for p in liste),
    )
