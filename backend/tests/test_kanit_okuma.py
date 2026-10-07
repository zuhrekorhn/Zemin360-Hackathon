"""Kanıt okuma: erişim tespiti, HTML özeti, okuyucu zinciri, parça seçimi (ağ yok).

docs/dogrulama.md § 5. Okuyucular kayıtlı yanıtlarla (MockTransport)
sınanır; DNS çözümleyici sahtedir.
"""

import asyncio
import ipaddress
import json
import time

import httpx
import pytest

from app.core import guvenli_istek
from app.core.kanit_okuma import kaniti_oku
from app.core.kanit_okuma.belge import ErisimDurumu as E
from app.core.kanit_okuma.erisim import erisim_durumu
from app.core.kanit_okuma.html_ozeti import html_ozeti
from app.core.kanit_okuma.istek import adresi_hazirla
from app.core.kanit_okuma.parca_secimi import KISA_METIN, bol, sec

GOVDE = "Ödünç takibi yapan bir sistem. " * 20


@pytest.fixture(autouse=True)
def genel_ip(monkeypatch):
    async def coz(host, port):
        if host == "olmayan.example":
            raise OSError("çözülemedi")
        return [ipaddress.ip_address("93.184.216.34")]

    monkeypatch.setattr(guvenli_istek, "cozumleyici", coz)


def oku(adres: str, yanitlar: dict[str, httpx.Response]):
    """İstek anahtarı: Host + yol + sorgu. Bulunmayan istek 404."""

    def isleyici(istek: httpx.Request) -> httpx.Response:
        anahtar = istek.headers["host"] + istek.url.raw_path.decode()
        for desen, yanit in yanitlar.items():
            if anahtar.startswith(desen):
                return yanit
        return httpx.Response(404)

    return asyncio.run(kaniti_oku(adres, transport=httpx.MockTransport(isleyici)))


def html(govde: str, durum: int = 200, **basliklar) -> httpx.Response:
    return httpx.Response(durum, headers={"content-type": "text/html", **basliklar}, text=govde)


# --- Erişim durumu -----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("durum", "son_url", "baslik", "uzunluk", "beklenen"),
    [
        (200, "https://x.org/p", "Proje", 500, E.ACIK),
        (404, "https://x.org/p", None, 0, E.BULUNAMADI),
        (410, "https://x.org/p", None, 0, E.BULUNAMADI),
        (200, "https://www.linkedin.com/authwall?trk=x", "LinkedIn", 500, E.GIRIS_GEREKLI),
        (200, "https://accounts.google.com/ServiceLogin", "Google", 500, E.GIRIS_GEREKLI),
        (200, "https://x.org/p", "Log in • Instagram", 500, E.GIRIS_GEREKLI),
        (401, "https://x.org/p", None, 0, E.GIRIS_GEREKLI),
        (403, "https://x.org/p", None, 0, E.ENGELLENDI),
        (999, "https://x.org/p", None, 0, E.ENGELLENDI),
        (200, "https://x.org/p", "Just a moment...", 500, E.ENGELLENDI),
        (503, "https://x.org/p", None, 0, E.HATA),
        (202, "https://dribbble.com/shots/1", None, 0, E.ICERIK_YOK),
    ],
)
def test_erisim_durumu(durum, son_url, baslik, uzunluk, beklenen):
    assert (
        erisim_durumu(durum=durum, son_url=son_url, baslik=baslik, metin_uzunlugu=uzunluk)
        is beklenen
    )


# --- HTML özeti --------------------------------------------------------------------------


def test_baslik_aciklama_ve_ana_metin_iskelet_atlanir():
    ozet = html_ozeti(
        "<html><head><title> Kütüphane  Takip </title>"
        '<meta name="description" content="400 kitap"></head><body>'
        "<nav>Menü</nav><script>var x=1</script><main>Ödünç takibi</main><footer>©</footer>"
        "</body></html>"
    )
    assert (ozet.baslik, ozet.aciklama, ozet.metin) == (
        "Kütüphane Takip",
        "400 kitap",
        "Ödünç takibi",
    )


def test_og_etiketleri_ve_karakter_kodlari():
    ozet = html_ozeti(
        '<head><meta content="NASA (&#064;nasa)" property="og:title">'
        '<meta property="og:description" content="T&#252;rkiye &amp; d&#252;nya"></head>'
    )
    assert (ozet.gorunen_baslik, ozet.aciklama) == ("NASA (@nasa)", "Türkiye & dünya")


def test_yazarlar_meta_citation_ve_json_ld_den():
    ozet = html_ozeti(
        '<head><meta name="citation_author" content="Çifçi, Mehmet Akif">'
        '<meta name="citation_author" content="Elçi, Atilla">'
        '<script type="application/ld+json">{"author": [{"name": "Julia Evans"}]}</script></head>'
    )
    assert ozet.yazarlar == ["Çifçi, Mehmet Akif", "Elçi, Atilla", "Julia Evans"]


def test_buyuk_sayfada_dogrusal_surer():
    """Eski regex bu girdide felaket geri izlemeye düşüyordu."""
    girdi = '<html><head><title>Kanal</title><meta content="' + '"a ' * 20_000
    baslangic = time.perf_counter()
    assert html_ozeti(girdi).baslik == "Kanal"
    assert time.perf_counter() - baslangic < 2


def test_semasiz_adrese_https_eklenir():
    assert adresi_hazirla("  //github.com/x  ") == "https://github.com/x"
    assert adresi_hazirla("http://ornek.org") == "http://ornek.org"


# --- Okuyucular --------------------------------------------------------------------------


def test_genel_okuyucu_acik_sayfa_ve_yazar():
    belge = oku(
        "ornek.org/proje",
        {
            "ornek.org/proje": html(
                '<head><title>Proje</title><meta name="author" content="Elif"></head>'
                f"<body>{GOVDE}</body>"
            )
        },
    )
    assert (belge.erisim, belge.platform, belge.yazarlar) == (E.ACIK, "web", ("Elif",))
    assert "Başlık: Proje" in belge.metin and "Ödünç takibi" in belge.metin


def test_bot_engeli_ve_alan_adi_yok():
    assert (
        oku("x.org/p", {"x.org/p": html("<title>Attention Required!</title>", 403)}).erisim
        is E.ENGELLENDI
    )
    assert oku("olmayan.example/p", {}).erisim is E.BULUNAMADI  # "güvensiz" değil: alan adı yok


def test_javascript_sayfasi_meta_varsa_acik_yoksa_icerik_yok():
    meta = (
        '<head><title>Titanic Tutorial | Kaggle</title><meta name="description" content="'
        + "Notebook. " * 25
        + '"></head><body></body>'
    )
    assert oku("kaggle.com/code/x", {"kaggle.com/code/x": html(meta)}).erisim is E.ACIK
    assert oku("x.org/spa", {"x.org/spa": html("<div id=root></div>")}).erisim is E.ICERIK_YOK


def test_github_okuyucusu_api_verisini_okur():
    repo = {
        "full_name": "elif/kutuphane",
        "owner": {"login": "elif"},
        "description": "Ödünç takibi",
        "stargazers_count": 12,
    }
    katki = [{"login": "elif", "contributions": 24}, {"login": "ali", "contributions": 1}]
    belge = oku(
        "github.com/elif/kutuphane",
        {
            "api.github.com/repos/elif/kutuphane/contributors": httpx.Response(200, json=katki),
            "api.github.com/repos/elif/kutuphane/readme": httpx.Response(
                200, text="# Kütüphane\n400 kitap"
            ),
            "api.github.com/repos/elif/kutuphane": httpx.Response(200, json=repo),
        },
    )
    assert (belge.platform, belge.erisim) == ("github", E.ACIK)
    assert [(h.kullanici_adi, h.katki_orani) for h in belge.hesaplar] == [
        ("elif", pytest.approx(24 / 25)),
        ("ali", pytest.approx(1 / 25)),
    ]
    assert "Yıldız: 12" in belge.metin and "400 kitap" in belge.metin
    assert belge.veri["katki_oranlari"]["elif"] == pytest.approx(24 / 25)


GITLAB_KOK = "gitlab.com/api/v4/projects/elif%2Fkutuphane"


def _gitlab_proje(tur="user"):
    return {
        "path_with_namespace": "elif/kutuphane",
        "description": "Mahalle kütüphanesi",
        "star_count": 7,
        "namespace": {"path": "elif", "full_path": "elif", "kind": tur},
        "readme_url": "https://gitlab.com/elif/kutuphane/-/blob/main/README.md",
    }


def test_gitlab_proje_tek_katkici_sahibin_payi_tam():
    belge = oku(
        "https://gitlab.com/elif/kutuphane/-/tree/main",
        {
            f"{GITLAB_KOK}/repository/contributors": httpx.Response(
                200, json=[{"name": "Elif Y", "email": "e@x", "commits": 30}]
            ),
            f"{GITLAB_KOK}/repository/files/README.md/raw": httpx.Response(200, text="400 kitap"),
            GITLAB_KOK: httpx.Response(200, json=_gitlab_proje()),
        },
    )
    assert (belge.platform, belge.erisim) == ("gitlab", E.ACIK)
    assert [(h.saglayici, h.kullanici_adi, h.katki_orani) for h in belge.hesaplar] == [
        ("gitlab", "elif", 1.0)
    ]
    assert "Yıldız: 7" in belge.platform_metni and "400 kitap" in belge.metin


def test_gitlab_cok_katkicida_pay_bilinmez_grupta_sahip_yok():
    katkicilar = [{"name": "A", "commits": 5}, {"name": "B", "commits": 5}]
    yanitlar = {
        f"{GITLAB_KOK}/repository/contributors": httpx.Response(200, json=katkicilar),
        GITLAB_KOK: httpx.Response(200, json=_gitlab_proje()),
    }
    belge = oku("gitlab.com/elif/kutuphane", yanitlar)
    assert [(h.kullanici_adi, h.katki_orani) for h in belge.hesaplar] == [("elif", None)]
    yanitlar[GITLAB_KOK] = httpx.Response(200, json=_gitlab_proje(tur="group"))
    assert oku("gitlab.com/elif/kutuphane", yanitlar).hesaplar == ()


def test_gitlab_olmayan_proje_bulunamadi():
    belge = oku("gitlab.com/yok/yok", {"gitlab.com/api/v4/projects/yok%2Fyok": httpx.Response(404)})
    assert (belge.platform, belge.erisim) == ("gitlab", E.BULUNAMADI)


def test_github_olmayan_repo_bulunamadi():
    belge = oku("github.com/yok/yok", {"api.github.com/repos/yok/yok": httpx.Response(404)})
    assert (belge.platform, belge.erisim) == ("github", E.BULUNAMADI)


def test_oembed_youtube_yazari_verir():
    veri = {
        "title": "Klip",
        "author_name": "Rick Astley",
        "author_url": "https://youtube.com/@x",
        "provider_name": "YouTube",
    }
    belge = oku(
        "https://www.youtube.com/watch?v=abc",
        {"www.youtube.com/oembed": httpx.Response(200, json=veri)},
    )
    assert (belge.platform, belge.yazarlar, belge.erisim) == ("youtube", ("Rick Astley",), E.ACIK)


def test_medium_rss_akisinda_yaziyi_bulur():
    rss = (
        '<rss xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:content="http://purl.org/rss/1.0/modules/content/">'
        "<channel><item><title>Yazı</title><link>https://medium.com/@ev/yazi-9e53ca408c48?source=rss</link>"
        "<dc:creator>Ev Williams</dc:creator>"
        "<content:encoded><![CDATA[<p>İçerik metni</p>]]></content:encoded>"
        "</item></channel></rss>"
    )
    belge = oku(
        "https://medium.com/@ev/yazi-9e53ca408c48",
        {"medium.com/feed/@ev": httpx.Response(200, text=rss)},
    )
    assert (belge.platform, belge.yazarlar) == ("medium", ("Ev Williams",))
    assert "İçerik metni" in belge.metin


def test_google_docs_disa_aktarir_paylasimsiz_dosya_giris_ister():
    acik = oku(
        "https://docs.google.com/document/d/ABC/edit",
        {
            "docs.google.com/document/d/ABC/export?format=txt": httpx.Response(
                200, headers={"content-type": "text/plain"}, text=GOVDE
            )
        },
    )
    assert (acik.platform, acik.erisim) == ("google", E.ACIK)
    kapali = oku(
        "https://docs.google.com/document/d/GIZLI/edit",
        {
            "docs.google.com/document/d/GIZLI/export": httpx.Response(
                302, headers={"location": "https://accounts.google.com/ServiceLogin"}
            ),
            "accounts.google.com/ServiceLogin": html("<title>Google</title>" + GOVDE),
        },
    )
    assert kapali.erisim is E.GIRIS_GEREKLI


# --- Parça seçimi ------------------------------------------------------------------------


def test_kisa_metin_oldugu_gibi():
    async def gom(_m, _t):
        raise AssertionError("kısa metinde embedding çağrılmaz")

    assert asyncio.run(sec("kısa", ["x"], gom)) == "kısa"


def test_uzun_metinde_ilk_parca_ve_ilgili_parcalar_secilir():
    metin = "A" * 3000 + "kütüphane " * 300 + "B" * 9000
    parcalar = bol(metin)

    async def gom(metinler, tur):
        # Sahte uzay: "kütüphane" içeren parça sorguya yakın.
        return [
            [1.0, 0.0] if ("kütüphane" in m or tur == "query") else [0.0, 1.0] for m in metinler
        ]

    secilen = asyncio.run(sec(metin, ["kütüphane"], gom))
    assert secilen.startswith(parcalar[0])
    assert "kütüphane" in secilen
    assert len(secilen) < len(metin)


def test_embedding_hata_verirse_metnin_basi_kullanilir():
    async def gom(_m, _t):
        raise RuntimeError("429")

    assert asyncio.run(sec("x" * (KISA_METIN * 2), ["sorgu"], gom)) == "x" * KISA_METIN


def test_json_kodlu_rss_degil():  # okuyucu bozuk akışta None döner, zincir genel okuyucuya geçer
    belge = oku(
        "https://medium.com/@ev/yazi-abc",
        {
            "medium.com/feed/@ev": httpx.Response(200, text=json.dumps({"x": 1})),
            "medium.com/@ev/yazi-abc": html("<title>x</title>", 403),
        },
    )
    assert belge.erisim is E.ENGELLENDI
