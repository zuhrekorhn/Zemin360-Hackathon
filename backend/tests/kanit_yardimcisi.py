"""Testlerde kanıt parçası kurmanın tek yolu (uygulamadaki tek kapının aynası)."""

from app.core.kanit_okuma.adres import normal_url
from app.core.kanit_okuma.belge import ParcaTuru
from app.models.kanit_parcasi import KanitParcasi


def link_parcasi(url: str) -> KanitParcasi:
    return KanitParcasi(tur=ParcaTuru.LINK.value, url=url, normal_url=normal_url(url))
