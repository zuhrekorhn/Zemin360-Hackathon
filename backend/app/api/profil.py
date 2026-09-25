"""Kart onayıyla gelen profil güncellemesi (docs/faz-b-kimlik-ve-dongu.md § 4).

Faz B'den önce onay, e-postayla profili bulup oluşturuyordu (upsert). Artık
profil token'daki hesabın profili; onay yalnızca eşleştirmeyi etkileyen
alanları günceller.

Kural (Faz A'dan): boş gelen alan kayıtlı değeri SİLMEZ. İkinci kartını
onaylayan genç şehrini ya da müsaitliğini yeniden yazmak zorunda değil.
"""

from __future__ import annotations

from app.core import calisma_modeli
from app.core.sehir import sehir_kanonik
from app.models.kullanici import Kullanici
from app.models.kurum import Kurum
from app.schemas.kesif import GencProfili
from app.schemas.tanimlama import KurumProfili


def gencin_profilini_guncelle(kullanici: Kullanici, profil: GencProfili) -> None:
    sehir = sehir_kanonik(profil.sehir)
    if sehir:
        kullanici.sehir = sehir
    modeller = calisma_modeli.temizle(profil.calisma_modelleri)
    if modeller:
        kullanici.calisma_modelleri = modeller
    if profil.musaitlik:
        kullanici.musaitlik = profil.musaitlik


def kurumun_profilini_guncelle(kurum: Kurum, profil: KurumProfili) -> None:
    sektor = (profil.sektor or "").strip()
    if sektor:
        kurum.sektor = sektor
    sehir = sehir_kanonik(profil.sehir)
    if sehir:
        kurum.sehir = sehir
