"""Adresteki hesap ve sahiplik kuralı (docs/dogrulama.md § 2, § 6): bağlı hesap → B, bireysel
kural."""

import pytest

from app.agents.dogrulama.hesap_sahipligi import (
    SAHIPSIZ,
    BagliHesapBilgisi,
    sahiplik_belirle,
)
from app.core.kanit_okuma.belge import (
    ErisimDurumu,
    HesapIzi,
    KanitBelgesi,
    KaynakSeviyesi,
    SahiplikKaynagi,
)
from app.core.kanit_okuma.hesap_izi import adresteki_hesap


@pytest.mark.parametrize(
    ("adres", "beklenen"),
    [
        ("https://github.com/karpathy/micrograd", ("github", "karpathy")),
        ("github.com/orgs/python", None),
        ("https://gitlab.com/ayse/proje/-/tree/main", ("gitlab", "ayse")),
        ("https://www.youtube.com/@RickAstleyYT", ("youtube", "RickAstleyYT")),
        ("https://www.youtube.com/channel/UC123", ("youtube", "UC123")),
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", None),
        ("https://youtu.be/dQw4w9WgXcQ", None),
        ("https://medium.com/@ev/welcome-to-medium-9e53ca408c48", ("medium", "ev")),
        ("https://ayse.medium.com/bir-yazi-123", ("medium", "ayse")),
        ("https://medium.com/tag/python", None),
        ("https://www.kaggle.com/code/alexisbcook/titanic-tutorial", ("kaggle", "alexisbcook")),
        ("https://www.kaggle.com/alexisbcook", ("kaggle", "alexisbcook")),
        ("https://www.kaggle.com/competitions/titanic", None),
        ("https://www.behance.net/ayseyilmaz", ("behance", "ayseyilmaz")),
        ("https://www.behance.net/gallery/123/Proje", None),
        ("https://dribbble.com/shots/23166201-Mobile", None),
        ("https://dribbble.com/sueda-turgut", ("dribbble", "sueda-turgut")),
        ("https://vimeo.com/76979871", None),
        ("https://vimeo.com/ayse", ("vimeo", "ayse")),
        ("https://soundcloud.com/ayse/parca", ("soundcloud", "ayse")),
        ("https://orcid.org/0000-0002-1825-0097", ("orcid", "0000-0002-1825-0097")),
        ("https://jvns.ca/blog/so-you-want-to-be-a-wizard/", ("kisisel_site", "jvns.ca")),
        ("https://www.brittanychiang.com", ("kisisel_site", "brittanychiang.com")),
        ("https://docs.google.com/document/d/abc", None),
        ("https://www.linkedin.com/in/ayse", None),
        ("", None),
    ],
)
def test_adresteki_hesap(adres, beklenen):
    iz = adresteki_hesap(adres)
    assert ((iz.saglayici, iz.kullanici_adi) if iz else None) == beklenen


def _belge(url: str, *hesaplar: HesapIzi) -> KanitBelgesi:
    return KanitBelgesi(url=url, erisim=ErisimDurumu.ACIK, hesaplar=hesaplar)


GITHUB_AYSE = BagliHesapBilgisi("github", "ayse", "oauth", dis_kimlik="1234")
REPO = "https://github.com/ayse/proje"


def test_bagli_hesap_yoksa_kamuya_acik():
    assert sahiplik_belirle(_belge(REPO, HesapIzi("github", "ayse", 1.0)), ()) == SAHIPSIZ


def test_tek_katkicili_repo_bireysel_b():
    s = sahiplik_belirle(_belge(REPO, HesapIzi("github", "Ayse", 0.95)), [GITHUB_AYSE])
    assert (s.seviye, s.kaynak, s.bireysel) == (
        KaynakSeviyesi.PLATFORM,
        SahiplikKaynagi.OAUTH,
        True,
    )


def test_katki_orani_dusukse_b_ama_bireysel_degil():
    s = sahiplik_belirle(_belge(REPO, HesapIzi("github", "ayse", 0.78)), [GITHUB_AYSE])
    assert (s.seviye, s.bireysel) == (KaynakSeviyesi.PLATFORM, False)


def test_katki_verisi_yoksa_adresten_b_bireysel_degil():
    s = sahiplik_belirle(_belge(REPO), [GITHUB_AYSE])
    assert (s.seviye, s.bireysel) == (KaynakSeviyesi.PLATFORM, False)


def test_baskasinin_reposu_bagli_hesapla_b_olmaz():
    belge = _belge("https://github.com/tiangolo/fastapi", HesapIzi("github", "tiangolo", 0.9))
    assert sahiplik_belirle(belge, [GITHUB_AYSE]) == SAHIPSIZ


def test_dis_kimlikle_eslesir_kullanici_adi_degisse_de():
    assert sahiplik_belirle(_belge("https://x.dev", HesapIzi("github", "1234")), [GITHUB_AYSE])


def test_baska_platformdaki_ayni_ad_eslesmez():
    belge = _belge("https://gitlab.com/ayse/proje", HesapIzi("gitlab", "ayse", 1.0))
    assert sahiplik_belirle(belge, [GITHUB_AYSE]) == SAHIPSIZ


def test_oembed_yazar_adresiyle_kanal_b_video_bireysel_degil():
    belge = _belge("https://www.youtube.com/watch?v=x", HesapIzi("youtube", "RickAstleyYT"))
    s = sahiplik_belirle(belge, [BagliHesapBilgisi("youtube", "rickastleyyt", "profil_kodu")])
    assert (s.seviye, s.kaynak, s.bireysel) == (
        KaynakSeviyesi.PLATFORM,
        SahiplikKaynagi.PROFIL_KODU,
        False,
    )


@pytest.mark.parametrize(
    ("url", "hesap"),
    [
        ("https://medium.com/@ev/yazi-1", BagliHesapBilgisi("medium", "ev", "profil_kodu")),
        ("https://blog.ayse.dev/yazi", BagliHesapBilgisi("kisisel_site", "ayse.dev", "elle")),
        ("https://ayse.dev", BagliHesapBilgisi("kisisel_site", "ayse.dev", "profil_kodu")),
    ],
)
def test_bagli_yazi_ve_portfolyo_bireysel(url, hesap):
    s = sahiplik_belirle(_belge(url), [hesap])
    assert (s.seviye, s.kaynak, s.bireysel) == (
        KaynakSeviyesi.PLATFORM,
        SahiplikKaynagi.PROFIL_KODU,
        True,
    )


def test_benzer_alan_adi_kisisel_site_sayilmaz():
    hesap = BagliHesapBilgisi("kisisel_site", "ayse.dev", "profil_kodu")
    assert sahiplik_belirle(_belge("https://notayse.dev/yazi"), [hesap]) == SAHIPSIZ
