"""GitHub reposu: REST API'den sahip, açıklama, yıldız, katkıcılar ve README.

Sayfanın HTML'i yerine API: veriler yapılandırılmış ve platformun ölçtüğü
(yıldız, commit sayıları; seviye B için bağımsız destek adayı, adım 8). API
okuyamazsa (hız sınırı, ağ) `None`: zincir genel okuyucuya geçer.
"""

from __future__ import annotations

import httpx

from app.core.kanit_okuma.belge import ErisimDurumu, KanitBelgesi
from app.core.kanit_okuma.istek import getir
from app.core.kanit_okuma.okuyucu import OkumaBaglami, hesap_izleri, metni_kur

API = "https://api.github.com"
README_EN_COK = 30_000
_REPO_OLMAYAN = frozenset(
    {
        "orgs",
        "settings",
        "topics",
        "search",
        "marketplace",
        "features",
        "sponsors",
        "about",
        "login",
    }
)


class GithubOkuyucu:
    ad = "github"

    def uygun_mu(self, url: httpx.URL) -> bool:
        parcalar = [p for p in url.path.split("/") if p]
        return (
            url.host.removeprefix("www.") == "github.com"
            and len(parcalar) >= 2
            and parcalar[0] not in _REPO_OLMAYAN
        )

    async def oku(self, url: httpx.URL, baglam: OkumaBaglami) -> KanitBelgesi | None:
        sahip, repo = [p for p in url.path.split("/") if p][:2]
        repo = repo.removesuffix(".git")
        kok = f"{API}/repos/{sahip}/{repo}"
        basliklar = {"Accept": "application/vnd.github+json"}
        if baglam.github_token:
            basliklar["Authorization"] = f"Bearer {baglam.github_token}"
        try:
            bilgi = await getir(kok, transport=baglam.transport, basliklar=basliklar)
            if bilgi.durum == 404:
                return KanitBelgesi(url=str(url), erisim=ErisimDurumu.BULUNAMADI, platform="github")
            if bilgi.durum != 200:
                return None
            veri = bilgi.json()
            katki = await getir(
                f"{kok}/contributors?per_page=10", transport=baglam.transport, basliklar=basliklar
            )
            readme = await getir(
                f"{kok}/readme",
                transport=baglam.transport,
                basliklar={**basliklar, "Accept": "application/vnd.github.raw"},
            )
        except (httpx.HTTPError, ValueError):
            return None

        katkicilar = (
            {k["login"]: k["contributions"] for k in katki.json() if "login" in k}
            if katki.durum == 200
            else {}
        )
        toplam = sum(katkicilar.values()) or 1
        oranlar = {k: s / toplam for k, s in katkicilar.items()}
        sahip_adi = (veri.get("owner") or {}).get("login")
        readme_metni = readme.metin[:README_EN_COK] if readme.durum == 200 else ""
        olcumler = (
            ("Yıldız", str(veri.get("stargazers_count"))),
            ("Katkıcılar (commit)", ", ".join(f"{k} ({s})" for k, s in katkicilar.items())),
        )
        return KanitBelgesi(
            url=str(url),
            erisim=ErisimDurumu.ACIK,
            platform="github",
            baslik=veri.get("full_name"),
            metin=metni_kur(
                ("Repo", veri.get("full_name")),
                ("Sahip", sahip_adi),
                ("Açıklama", veri.get("description")),
                *olcumler,
                govde=f"README:\n{readme_metni}" if readme_metni else "",
            ),
            yazarlar=(sahip_adi,) if sahip_adi else (),
            hesaplar=hesap_izleri("github", sahip_adi, oranlar),
            veri={
                "sahip": sahip_adi,
                "yildiz": veri.get("stargazers_count"),
                "katki_oranlari": oranlar,
            },
            platform_metni=metni_kur(*olcumler),
        )
