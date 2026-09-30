"""Keşif Ajanı'nın karar mantığı — LLM çağrısı olmadan.

Buradaki sınırlar docs/agent-specs.md § 1'den geliyor; LLM'in ne cevap
verdiğinden bağımsız olarak tutmaları gerekiyor.
"""

import asyncio
from types import SimpleNamespace

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents import sohbet_motoru as motor
from app.agents.kesif import (
    FALLBACK_SORULARI,
    KESIF,
    MAKS_EK_TURU,
    MAKS_TAKIP_TURU,
    SomutCiktiTaslak,
    TaslakCikarimi,
    _birlestir,
    _karar,
    bos_taslak,
)
from app.core.is_kalemi import is_kalemi_metni


def karar(durum: dict) -> dict:
    return asyncio.run(_karar(durum))


def dolu_taslak(**degisiklikler) -> dict:
    taslak = {
        "rol_alani": "backend geliştirici",
        "deneyim_seviyesi": "orta",
        "sektor_ilgi_alani": ["eğitim"],
        "araclar_teknolojiler": ["Python"],
        "sertifikalar": [],
        "diller": [],
        "somut_ciktilar": [
            {"kimlik": "c1", "baslik": "Kütüphane sistemi", "aciklama": None, "kanit_linki": None}
        ],
    }
    taslak.update(degisiklikler)
    return taslak


def test_bos_cikarim_mevcut_taslagi_silmez():
    """LLM bir turda alanı boş döndürürse önceki cevap kaybolmamalı."""
    onceki = dolu_taslak()
    sonraki = _birlestir(onceki, TaslakCikarimi())
    assert sonraki == onceki


def test_yeni_degerler_listeye_eklenir_tekrarlanmaz():
    taslak = _birlestir(
        dolu_taslak(),
        TaslakCikarimi(
            araclar_teknolojiler=["Python", "Docker"], sektor_ilgi_alani=["sivil toplum"]
        ),
    )
    assert taslak["araclar_teknolojiler"] == ["Python", "Docker"]
    assert taslak["sektor_ilgi_alani"] == ["eğitim", "sivil toplum"]


def test_ayni_cikti_iki_kez_eklenmez():
    taslak = _birlestir(
        dolu_taslak(),
        TaslakCikarimi(somut_ciktilar=[SomutCiktiTaslak(baslik="kütüphane sistemi")]),
    )
    assert len(taslak["somut_ciktilar"]) == 1


def test_eksik_alan_takip_sorusu_getirir():
    sonuc = karar({"taslak": dolu_taslak(rol_alani=None), "takip_turu": 0, "fallback_indeksi": 0})
    assert sonuc["sonraki_soru"]
    assert sonuc["taslak_hazir"] is False


def test_zorunlu_alan_icin_iki_turdan_sonra_da_sorulur():
    """Eksik zorunlu alanla kart kapatmak sohbeti uzatmaktan kötü.

    Gerçek turda "sektör ilgisi" boş kalmıştı: tur hakkı bitmiş, kart eksik
    kaydedilmişti. Boş alan eşleştirmede doğrudan skora yansıyor.
    """
    sonuc = karar(
        {
            "taslak": dolu_taslak(rol_alani=None),
            "takip_turu": MAKS_TAKIP_TURU,
            "fallback_indeksi": 0,
        }
    )
    assert sonuc["taslak_hazir"] is False
    assert sonuc["sonraki_soru"]


def test_zorunlu_tavaninda_kart_yine_de_kapanir():
    """Sonsuz döngü olmasın: tavanda alanlar yer tutucuyla dolup kart çıkar.

    Çıktının ölçüt ve rol bilgisi tam: ek sorular kendi sayacıyla ayrıca
    soruluyor (bkz. test_zorunlu_alanlar_uzun_surse_de_ek_soru_sorulur),
    burada yalnızca zorunlu alan tavanı sınanıyor.
    """
    tam_cikti = [
        {
            "baslik": "Kütüphane sistemi",
            "olculebilir_sonuc": "400 kitap",
            "kendi_rolu": "hepsini ben yazdım",
            "kanit_linki": "https://github.com/elif/kutuphane",
        }
    ]
    sonuc = karar(
        {
            "taslak": dolu_taslak(rol_alani=None, somut_ciktilar=tam_cikti),
            "takip_turu": motor.MAKS_ZORUNLU_TURU,
            "fallback_indeksi": 0,
        }
    )
    assert sonuc["taslak_hazir"] is True
    assert sonuc["taslak"]["rol_alani"] == "belirtilmedi"


def test_cikti_olcutu_eksikse_sorulur():
    """Rubrik "ölçülebilir sonuç" puanlıyor; Keşif bunu sormalı."""
    sonuc = karar(
        {
            "taslak": dolu_taslak(
                somut_ciktilar=[{"baslik": "Kütüphane sistemi", "kendi_rolu": "hepsini ben yaptım"}]
            ),
            "takip_turu": 0,
            "fallback_indeksi": 0,
        }
    )
    assert sonuc["taslak_hazir"] is False
    assert "sayıyla" in sonuc["sonraki_soru"]


def test_cikti_rolu_eksikse_sorulur():
    sonuc = karar(
        {
            "taslak": dolu_taslak(
                somut_ciktilar=[{"baslik": "Kütüphane sistemi", "olculebilir_sonuc": "400 kitap"}]
            ),
            "takip_turu": 0,
            "fallback_indeksi": 0,
        }
    )
    assert sonuc["taslak_hazir"] is False
    assert "hangi kısmı sen yaptın" in sonuc["sonraki_soru"]


def test_cikti_detaylari_tamsa_kart_kapanir():
    sonuc = karar(
        {
            "taslak": dolu_taslak(
                somut_ciktilar=[
                    {
                        "baslik": "Kütüphane sistemi",
                        "aciklama": "Ödünç takibi",
                        "olculebilir_sonuc": "400 kitap, 120 üye",
                        "kendi_rolu": "backend'i ben yazdım",
                        "kanit_linki": "https://github.com/elif/kutuphane",
                    }
                ]
            ),
            "takip_turu": 0,
            "fallback_indeksi": 0,
        }
    )
    assert sonuc["taslak_hazir"] is True


# --- Ek sorular: ayrı sayaç, tekrar yok --------------------------------------
# Eskiden ek sorular zorunlu alanlarla aynı sayacı paylaşıyordu (zorunlu alanlar
# 2 tur sürünce hiç sorulmuyorlardı) ve hep listedeki ilk soru seçiliyordu
# ("bilmiyorum" diyene aynı soru kelimesi kelimesine tekrar geliyordu).

OLCUTSUZ_ROLSUZ = [{"baslik": "Kütüphane sistemi", "aciklama": None, "kanit_linki": None}]


def test_zorunlu_alanlar_uzun_surse_de_ek_soru_sorulur():
    sonuc = karar(
        {
            "taslak": dolu_taslak(somut_ciktilar=OLCUTSUZ_ROLSUZ),
            "takip_turu": motor.MAKS_TAKIP_TURU + 1,  # zorunlu alanlar 3 tur sürdü
            "fallback_indeksi": 0,
        }
    )
    assert sonuc["taslak_hazir"] is False
    assert "sayıyla" in sonuc["sonraki_soru"]
    assert sonuc["ek_takip_turu"] == 1
    # Ek soru zorunlu alan sayacına dokunmuyor
    assert "takip_turu" not in sonuc


def test_bilmiyorum_denen_ek_soru_tekrarlanmaz():
    """Ölçüt sorulmuş, kullanıcı bilmiyor: alan boş kaldı ama soru bir daha gelmez."""
    sonuc = karar(
        {
            "taslak": dolu_taslak(somut_ciktilar=OLCUTSUZ_ROLSUZ),
            "takip_turu": 0,
            "ek_takip_turu": 1,
            "sorulan_ekler": ["olcut:Kütüphane sistemi"],
            "fallback_indeksi": 0,
        }
    )
    assert "sayıyla" not in sonuc["sonraki_soru"]
    assert "hangi kısmı sen yaptın" in sonuc["sonraki_soru"]
    assert sonuc["sorulan_ekler"] == ["olcut:Kütüphane sistemi", "rol:Kütüphane sistemi"]


def test_hepsi_sorulduysa_kart_kapanir_ve_israr_edilmez():
    sonuc = karar(
        {
            "taslak": dolu_taslak(somut_ciktilar=OLCUTSUZ_ROLSUZ),
            "takip_turu": 0,
            "ek_takip_turu": 3,
            "sorulan_ekler": [
                "olcut:Kütüphane sistemi",
                "rol:Kütüphane sistemi",
                "kanit:Kütüphane sistemi",
            ],
            "fallback_indeksi": 0,
        }
    )
    assert sonuc["taslak_hazir"] is True


def test_ek_soru_tavani():
    """İki çıktı → altı eksik; yine de en fazla dört ek soru sorulur."""
    iki_cikti = [
        {"baslik": "Kütüphane sistemi", "aciklama": None, "kanit_linki": None},
        {"baslik": "Kulüp sitesi", "aciklama": None, "kanit_linki": None},
    ]
    sonuc = karar(
        {
            "taslak": dolu_taslak(somut_ciktilar=iki_cikti),
            "takip_turu": 0,
            "ek_takip_turu": MAKS_EK_TURU,
            "sorulan_ekler": [
                "olcut:Kütüphane sistemi",
                "rol:Kütüphane sistemi",
                "kanit:Kütüphane sistemi",
                "olcut:Kulüp sitesi",
            ],
            "fallback_indeksi": 0,
        }
    )
    assert sonuc["taslak_hazir"] is True


def test_olcut_ve_rol_ayri_kalir_rubrik_birlesik_okur():
    """Sonuç ve rol düzenlenebilsin diye ayrı alanlarda kalır; Doğrulama
    Ajanı, embedding ve gerekçe işi birleşik metin olarak okur (is_kalemi_metni)."""
    sonuc = karar(
        {
            "taslak": dolu_taslak(
                somut_ciktilar=[
                    {
                        "baslik": "Kütüphane sistemi",
                        "aciklama": "Ödünç takip sistemi yazdım.",
                        "olculebilir_sonuc": "400 kitap ve 120 üye takip ediliyor.",
                        "kendi_rolu": "Backend'i ben yazdım.",
                        "kanit_linki": "https://github.com/elif/kutuphane",
                    }
                ]
            ),
            "takip_turu": 0,
            "fallback_indeksi": 0,
        }
    )
    cikti = sonuc["taslak"]["somut_ciktilar"][0]
    assert cikti["aciklama"] == "Ödünç takip sistemi yazdım."
    assert cikti["olculebilir_sonuc"] == "400 kitap ve 120 üye takip ediliyor."
    metin = is_kalemi_metni(SimpleNamespace(**cikti))
    assert "400 kitap" in metin
    assert "Backend'i ben yazdım" in metin


def test_cikti_yoksa_once_fallback_sorulur():
    sonuc = karar(
        {"taslak": dolu_taslak(somut_ciktilar=[]), "takip_turu": 0, "fallback_indeksi": 0}
    )
    assert sonuc["sonraki_soru"] == FALLBACK_SORULARI[0]
    assert sonuc["fallback_indeksi"] == 1


def test_fallback_bitince_kart_potansiyel_olur():
    """agent-specs.md § 1.4 — çıktısı olmayan kart yine de oluşur."""
    sonuc = karar(
        {
            "taslak": dolu_taslak(somut_ciktilar=[]),
            "takip_turu": 0,
            "fallback_indeksi": len(FALLBACK_SORULARI),
        }
    )
    assert sonuc["taslak_hazir"] is True
    assert sonuc["taslak"]["deneyim_seviyesi"] == "potansiyel"
    assert sonuc["sonraki_soru"] is None


def test_bos_taslak_tum_zorunlu_alanlari_icerir():
    assert set(bos_taslak()) >= {
        "rol_alani",
        "deneyim_seviyesi",
        "sektor_ilgi_alani",
        "araclar_teknolojiler",
        "somut_ciktilar",
    }


# --- Aynı işi anlatan çıktılar --------------------------------------------


def test_ayni_is_farkli_yazimla_iki_kayit_acmaz():
    """Gerçek turda görülen vaka: "Team To Do" ve "Team ToDo" iki satır olmuştu."""
    taslak = dolu_taslak(
        somut_ciktilar=[
            {"baslik": "Team To Do Web Uygulaması", "aciklama": None, "kanit_linki": None}
        ]
    )
    sonuc = _birlestir(
        taslak,
        TaslakCikarimi(
            somut_ciktilar=[
                SomutCiktiTaslak(
                    baslik="Team ToDo Web Uygulaması",
                    kanit_linki="github.com/ornek/teamtodo",
                )
            ]
        ),
    )
    assert len(sonuc["somut_ciktilar"]) == 1


def test_ikinci_anlatimdaki_link_bos_alani_doldurur():
    taslak = dolu_taslak(
        somut_ciktilar=[
            {"baslik": "Team To Do", "aciklama": "Ekip için görev takibi", "kanit_linki": None}
        ]
    )
    sonuc = _birlestir(
        taslak,
        TaslakCikarimi(
            somut_ciktilar=[SomutCiktiTaslak(baslik="team todo", kanit_linki="github.com/ornek/x")]
        ),
    )
    cikti = sonuc["somut_ciktilar"][0]
    assert cikti["kanit_linki"] == "github.com/ornek/x"
    # İlk anlatılan açıklama korunur, üzerine yazılmaz
    assert cikti["aciklama"] == "Ekip için görev takibi"


def test_gercekten_farkli_isler_ayri_kalir():
    taslak = dolu_taslak(
        somut_ciktilar=[{"baslik": "Team To Do", "aciklama": None, "kanit_linki": None}]
    )
    sonuc = _birlestir(
        taslak, TaslakCikarimi(somut_ciktilar=[SomutCiktiTaslak(baslik="Kütüphane takip sistemi")])
    )
    assert len(sonuc["somut_ciktilar"]) == 2


# --- Kalıcı kimlik: başlık değişse de aynı çalışma --------------------------
# Sahada görüldü: model her turda konuşmanın tamamını baştan okuyup çalışmaya
# başka bir ad veriyordu; başlıkla eşleştirme kartta aynı işi iki satır yapıyordu.


def test_yeni_calisma_kimlik_alir():
    sonuc = _birlestir(
        bos_taslak(),
        TaslakCikarimi(
            somut_ciktilar=[
                SomutCiktiTaslak(baslik="Kütüphane sistemi"),
                SomutCiktiTaslak(baslik="Kulüp sitesi"),
            ]
        ),
    )
    assert [c["kimlik"] for c in sonuc["somut_ciktilar"]] == ["c1", "c2"]


def test_kimlikle_gelen_farkli_baslik_ayni_calismayi_gunceller():
    taslak = dolu_taslak(
        somut_ciktilar=[{"kimlik": "c1", "baslik": "Kütüphane sistemi", "kanit_linki": None}]
    )
    sonuc = _birlestir(
        taslak,
        TaslakCikarimi(
            somut_ciktilar=[
                SomutCiktiTaslak(
                    kimlik="c1",
                    baslik="Mahalle kütüphanesi ödünç takip uygulaması",
                    kanit_linki="https://github.com/elif/kutuphane",
                )
            ]
        ),
    )
    assert len(sonuc["somut_ciktilar"]) == 1
    cikti = sonuc["somut_ciktilar"][0]
    assert cikti["baslik"] == "Kütüphane sistemi"  # ilk anlatılan korunur
    assert cikti["kanit_linki"] == "https://github.com/elif/kutuphane"


def test_bilinmeyen_kimlik_yeni_calisma_acar_cakisma_olmaz():
    taslak = dolu_taslak(somut_ciktilar=[{"kimlik": "c1", "baslik": "Kütüphane sistemi"}])
    sonuc = _birlestir(
        taslak,
        TaslakCikarimi(somut_ciktilar=[SomutCiktiTaslak(kimlik="c9", baslik="Kulüp sitesi")]),
    )
    assert [c["kimlik"] for c in sonuc["somut_ciktilar"]] == ["c1", "c2"]


def test_kimliksiz_eski_taslak_kimlik_alir():
    """Bu özellikten önce açılmış sohbetin taslağı checkpoint'te kimliksiz duruyor."""
    taslak = dolu_taslak(
        somut_ciktilar=[{"baslik": "Kütüphane sistemi"}, {"baslik": "Kulüp sitesi"}]
    )
    sonuc = _birlestir(taslak, TaslakCikarimi())
    assert [c["kimlik"] for c in sonuc["somut_ciktilar"]] == ["c1", "c2"]


def test_birlestirme_onceki_taslagi_degistirmez():
    """Checkpoint'teki eski durum yerinde değiştirilmemeli."""
    onceki_cikti = {"kimlik": "c1", "baslik": "Kütüphane sistemi", "kanit_linki": None}
    taslak = dolu_taslak(somut_ciktilar=[onceki_cikti])
    _birlestir(
        taslak,
        TaslakCikarimi(
            somut_ciktilar=[SomutCiktiTaslak(kimlik="c1", baslik="x", kanit_linki="github.com/x")]
        ),
    )
    assert onceki_cikti["kanit_linki"] is None


def test_baslik_degisince_ek_soru_tekrar_sorulmaz():
    """Sorulan ek soru kimliğe bağlı; başlığa bağlıyken yeni ad yeni soru demekti."""
    sonuc = karar(
        {
            "taslak": dolu_taslak(
                somut_ciktilar=[{"kimlik": "c1", "baslik": "Mahalle kütüphanesi uygulaması"}]
            ),
            "takip_turu": 0,
            "ek_takip_turu": 1,
            "sorulan_ekler": ["olcut:c1"],
            "fallback_indeksi": 0,
        }
    )
    assert "sayıyla" not in sonuc["sonraki_soru"]
    assert sonuc["sorulan_ekler"] == ["olcut:c1", "rol:c1"]


def test_dolu_taslak_modele_ayri_sistem_mesaji_olarak_gider():
    durum = {
        "mesajlar": [HumanMessage(content="Kütüphane sistemi yaptım.")],
        "taslak": dolu_taslak(somut_ciktilar=[{"kimlik": "c1", "baslik": "Kütüphane sistemi"}]),
        "profil_baglami": "KULLANICININ PROFİLİ: Şehir: İzmir",
    }
    mesajlar = motor.istem_mesajlari(KESIF, durum)
    sistem = [m.content for m in mesajlar if isinstance(m, SystemMessage)]
    assert sistem[0] == KESIF.sistem_talimati
    assert sistem[1] == durum["profil_baglami"]
    assert sistem[2].startswith(motor.TASLAK_BASLIGI)
    assert '"kimlik": "c1"' in sistem[2]


def test_bos_taslak_modele_gitmez():
    durum = {"mesajlar": [HumanMessage(content="Merhaba")], "taslak": bos_taslak()}
    assert len(motor.istem_mesajlari(KESIF, durum)) == 2  # talimat + kullanıcı mesajı


def test_potansiyel_kurali_ciktisiz_karti_etiketler():
    """Sohbet kapanışı ve onay aynı kuralı kullanıyor (app/api/kesif.py)."""
    from app.agents.kesif import POTANSIYEL, potansiyel_kurali

    assert potansiyel_kurali("orta", 0) == POTANSIYEL
    assert potansiyel_kurali(None, 0) == POTANSIYEL
    assert potansiyel_kurali("orta", 1) == "orta"


# --- Zorunlu fazda modelin sorusu yalnızca zorunlu konudaysa -------------------
# Gerçek sohbette: sektör eksikken model "projede rolün neydi" diye sordu; bu
# soru hiçbir deftere girmediği için bir sonraki turda sistemin ek sorusu aynı
# konuyu tekrar sordu. Kullanıcı aynı soruyu iki kez gördü.

ROL_SORUSU_LLM = "Bu çalışmayı tek başına mı geliştirdin? Senin rolün neydi?"


def test_zorunlu_fazda_ek_konulu_llm_sorusu_kullanilmaz():
    from app.agents.kesif import YEDEK_SORULAR

    sonuc = karar(
        {
            "taslak": dolu_taslak(sektor_ilgi_alani=[]),
            "takip_turu": 0,
            "son_takip_sorusu": ROL_SORUSU_LLM,
            "son_takip_konusu": "kendi_rolu",
            "fallback_indeksi": 0,
        }
    )
    assert sonuc["sonraki_soru"] == YEDEK_SORULAR["sektor_ilgi_alani"]


def test_zorunlu_konulu_llm_sorusu_kullanilir():
    """Doğal ifade sabit yedek sorudan iyi; konu doğruysa modelin sorusu sorulur."""
    llm_sorusu = "Hangi alanlarda çalışmak seni heyecanlandırır?"
    sonuc = karar(
        {
            "taslak": dolu_taslak(sektor_ilgi_alani=[]),
            "takip_turu": 0,
            "son_takip_sorusu": llm_sorusu,
            "son_takip_konusu": "sektor_ilgi_alani",
            "fallback_indeksi": 0,
        }
    )
    assert sonuc["sonraki_soru"] == llm_sorusu


def test_konusu_belirtilmemis_llm_sorusu_kullanilmaz():
    from app.agents.kesif import YEDEK_SORULAR

    sonuc = karar(
        {
            "taslak": dolu_taslak(rol_alani=None),
            "takip_turu": 0,
            "son_takip_sorusu": "Başka ne yaptın?",
            "son_takip_konusu": None,
            "fallback_indeksi": 0,
        }
    )
    assert sonuc["sonraki_soru"] == YEDEK_SORULAR["rol_alani"]


def test_gozlenen_sohbette_rol_konusu_bir_kez_sorulur():
    """Gerçek sohbetin dizisi: 1. turda sektör eksik + model rol sordu,
    2. turda zorunlular tamam. Rol/pay konusu toplamda yalnızca bir kez gelir."""
    cikti = [{"baslik": "Kütüphane sistemi", "olculebilir_sonuc": "400 kitap"}]
    durum = {
        "taslak": dolu_taslak(sektor_ilgi_alani=[], somut_ciktilar=cikti),
        "takip_turu": 0,
        "son_takip_sorusu": ROL_SORUSU_LLM,
        "son_takip_konusu": "kendi_rolu",
        "fallback_indeksi": 0,
    }
    sorular = []
    for tur_taslagi in (
        durum["taslak"],
        dolu_taslak(somut_ciktilar=cikti),  # kullanıcı sektörünü söyledi
        dolu_taslak(somut_ciktilar=cikti),  # rolünü söylemedi
    ):
        durum = {**durum, "taslak": tur_taslagi}
        sonuc = karar(durum)
        if sonuc.get("taslak_hazir"):
            break
        sorular.append(sonuc["sonraki_soru"])
        durum = {**durum, **{k: v for k, v in sonuc.items() if k != "mesajlar"}}

    rol_sorulari = [s for s in sorular if "hangi kısmı sen yaptın" in s]
    assert len(rol_sorulari) == 1, sorular


def test_teknik_rol_adlari_turkcelestirilmiyor():
    """Sahada görüldü: model "arka yüz geliştirici, tam yığın geliştirici" diye sordu.
    Kurum ve genç bu rolleri "backend", "full-stack" diye arıyor; eşleştirme
    metni de aynı adla daha iyi çalışır."""
    from app.agents.kesif import SISTEM_TALIMATI

    talimat = " ".join(SISTEM_TALIMATI.split())  # satır kırılmasından bağımsız
    assert "TÜRKÇELEŞTİRME" in talimat
    assert '"backend geliştirici"' in talimat
    assert '"arka yüz geliştirici"' in talimat
    assert "sorduğun sorulardaki örnekler için de" in talimat
