"""Bilinen belge düzenleyenleri (plan § 4.2): doğrulama adresi bu alan adlarından birindeyse
belgeyi bağımsız bir kurumun doğruladığı kabul edilir. Alt alan adları da sayılır
(`www.`, `learn.` …). Liste veridir: yeni düzenleyen = yeni satır (karar, 3 Eki:
küçük bir başlangıç listesi, GİRVAK genişletir).
"""

from __future__ import annotations

import httpx

BILINEN_DUZENLEYENLER: dict[str, str] = {
    # Rozet ve sertifika platformları
    "credly.com": "Credly",
    "youracclaim.com": "Credly",
    "accredible.com": "Accredible",
    "badgr.com": "Badgr",
    "certificates.dev": "certificates.dev",
    # Eğitim platformları
    "coursera.org": "Coursera",
    "edx.org": "edX",
    "udemy.com": "Udemy",
    "datacamp.com": "DataCamp",
    "freecodecamp.org": "freeCodeCamp",
    "kaggle.com": "Kaggle",
    "hackerrank.com": "HackerRank",
    "linkedin.com": "LinkedIn Learning",
    # Kurumlar
    "btkakademi.gov.tr": "BTK Akademi",
    "turkiye.gov.tr": "e-Devlet",
    "learn.microsoft.com": "Microsoft Learn",
    "grow.google": "Google",
    "skillshop.exceedlms.com": "Google Skillshop",
    "netacad.com": "Cisco Networking Academy",
    "aws.amazon.com": "AWS",
    "oracle.com": "Oracle",
}


def duzenleyen(adres: str) -> str | None:
    """Adres bilinen bir düzenleyenin alan adındaysa adı, değilse None."""
    try:
        alan = (httpx.URL(adres).host or "").lower().rstrip(".")
    except (httpx.InvalidURL, ValueError):
        return None
    for kok, ad in BILINEN_DUZENLEYENLER.items():
        if alan == kok or alan.endswith("." + kok):
            return ad
    return None
