"""GitLab projesi: REST API'den ad alanı, açıklama, yıldız, katkıcılar ve README.

GitHub okuyucusunun eşi. Fark: GitLab'in katkıcı listesi kullanıcı adı değil ad
ve e-posta döner, katkıcıyı bağlı hesapla eşleştiremeyiz. Bu yüzden hesap izi
proje sahibidir (kullanıcı ad alanı); tek katkıcılı projede sahibin payı %100
sayılır (bireysel kural), çok katkıcılıda pay bilinmez. API okuyamazsa `None`:
zincir genel okuyucuya geçer.
"""

from __future__ import annotations

from urllib.parse import quote

import httpx

from app.core.kanit_okuma.belge import ErisimDurumu, KanitBelgesi
from app.core.kanit_okuma.istek import getir
from app.core.kanit_okuma.okuyucu import OkumaBaglami, hesap_izleri, metni_kur

API = "https://gitlab.com/api/v4"
README_EN_COK = 30_000
_PROJE_OLMAYAN = frozenset({"explore", "users", "help", "dashboard", "search", "groups"})


def _proje_yolu(url: httpx.URL) -> str | None:
    """`gitlab.com/grup/alt-grup/proje/-/tree/main` → `grup/alt-grup/proje`."""
    parcalar = [p for p in url.path.split("/") if p]
    if "-" in parcalar:
        parcalar = parcalar[: parcalar.index("-")]
    if len(parcalar) < 2 or parcalar[0] in _PROJE_OLMAYAN:
        return None
    parcalar[-1] = parcalar[-1].removesuffix(".git")
    return "/".join(parcalar)


def _readme_yolu(readme_url: str | None) -> tuple[str, str] | None:
    """`…/-/blob/main/docs/README.md` → (`main`, `docs/README.md`)."""
    if not readme_url or "/-/blob/" not in readme_url:
        return None
    dal, _, yol = readme_url.split("/-/blob/", 1)[1].partition("/")
    return (dal, yol) if dal and yol else None


class GitlabOkuyucu:
    ad = "gitlab"

    def uygun_mu(self, url: httpx.URL) -> bool:
        return url.host.removeprefix("www.") == "gitlab.com" and _proje_yolu(url) is not None

    async def oku(self, url: httpx.URL, baglam: OkumaBaglami) -> KanitBelgesi | None:
        yol = _proje_yolu(url)
        if yol is None:
            return None
        kok = f"{API}/projects/{quote(yol, safe='')}"
        try:
            bilgi = await getir(kok, transport=baglam.transport)
            if bilgi.durum == 404:
                return KanitBelgesi(url=str(url), erisim=ErisimDurumu.BULUNAMADI, platform="gitlab")
            if bilgi.durum != 200:
                return None
            veri = bilgi.json()
            katki = await getir(
                f"{kok}/repository/contributors?per_page=10", transport=baglam.transport
            )
            readme_metni = await self._readme(kok, veri.get("readme_url"), baglam)
        except (httpx.HTTPError, ValueError):
            return None

        katkicilar = (
            {k["name"]: k["commits"] for k in katki.json() if "name" in k}
            if katki.durum == 200
            else {}
        )
        ad_alani = veri.get("namespace") or {}
        # Grup projesinin sahibi bir kişi değil: hesap izi yalnızca kullanıcı ad alanından.
        sahip = ad_alani.get("path") if ad_alani.get("kind") == "user" else None
        oranlar = {sahip: 1.0} if sahip and len(katkicilar) == 1 else {}
        olcumler = (
            ("Yıldız", str(veri.get("star_count"))),
            ("Katkıcılar (commit)", ", ".join(f"{k} ({s})" for k, s in katkicilar.items())),
        )
        return KanitBelgesi(
            url=str(url),
            erisim=ErisimDurumu.ACIK,
            platform="gitlab",
            baslik=veri.get("path_with_namespace"),
            metin=metni_kur(
                ("Proje", veri.get("path_with_namespace")),
                ("Sahip", ad_alani.get("full_path")),
                ("Açıklama", veri.get("description")),
                *olcumler,
                govde=f"README:\n{readme_metni}" if readme_metni else "",
            ),
            hesaplar=hesap_izleri("gitlab", sahip, oranlar),
            veri={"sahip": sahip, "yildiz": veri.get("star_count"), "katkicilar": katkicilar},
            platform_metni=metni_kur(*olcumler),
        )

    async def _readme(self, kok: str, readme_url: str | None, baglam: OkumaBaglami) -> str:
        bulunan = _readme_yolu(readme_url)
        if bulunan is None:
            return ""
        dal, yol = bulunan
        yanit = await getir(
            f"{kok}/repository/files/{quote(yol, safe='')}/raw?ref={quote(dal, safe='')}",
            transport=baglam.transport,
        )
        return yanit.metin[:README_EN_COK] if yanit.durum == 200 else ""
