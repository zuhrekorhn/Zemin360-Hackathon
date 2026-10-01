# Karne: mevcut_sistem (2026-10-01)

- Etiket kaynağı: **TASLAK ETİKET (öneriler; Zühre'nin etiketi değil)**
- Vaka: 45 toplam, 45 ölçülen
- Kabul eşikleri: **geçmiyor**
- Sahte vakada yanlış 3: **0** (hedef 0)
- Bütün vakalarda yanlış 3: 0
- Notta dil ihlali olan vaka: 0 (hedef 0)
- Sonuç üretemeyen vaka: 0

## Başlık başına uyum

| Başlık | Birebir (hedef %80) | ±1 (hedef %95) | Vaka |
|---|---|---|---|
| kanit | %56 | %73 | 45 |
| sonuc | %82 | %100 | 45 |
| rol | %69 | %100 | 45 |
| referans | %100 | %100 | 45 |

## Alan kırılımı

| Alan | Kanıt "—" oranı | Dürüst vakada ort. Kanıt |
|---|---|---|
| akademik | %0 | 2.00 |
| gonulluluk | %50 | 0.00 |
| kamuya_kapali | %100 | — |
| medya | %67 | 0.00 |
| muhendislik | %100 | — |
| pazarlama | %100 | — |
| sertifika | %50 | 0.00 |
| staj_is | %75 | 2.00 |
| tasarim | %60 | 2.00 |
| veri | %33 | 2.00 |
| yarisma | %50 | 0.00 |
| yazi | %40 | 2.00 |
| yazilim | %11 | 1.00 |

## Vakalar

Hücre: sistem / beklenen. ✗ uyuşmayan başlık.

| Vaka | Alan | Kanıt | Sonuç | Rol | Referans |
|---|---|---|---|---|---|
| akademik-arxiv-yazar-eslesiyor | akademik | 2 / 2 | 0 / 0 | 1 / 1/2 | — / — |
| akademik-arxiv-yazar-eslesmiyor ⚠ | akademik | 2 / 0/1 ✗ | 0 / 0 | 2 / 0/1 ✗ | — / — |
| akademik-dergipark-ikinci-yazar | akademik | 2 / 2 | 0 / 0 | 1 / 2 ✗ | — / — |
| gonulluluk-kurulus-ana-sayfasi-referansli | gonulluluk | 0 / 0/1 | 2 / 3 ✗ | 2 / 3 ✗ | 3 / 3 |
| gonulluluk-kanitsiz | gonulluluk | — / — | 1 / 1 | 1 / 1 | — / — |
| kapali-satis-referans | kamuya_kapali | — / — | 2 / 3 ✗ | 2 / 3 ✗ | 3 / 3 |
| kapali-finans-beyan | kamuya_kapali | — / — | 2 / 2 | 1 / 1 | — / — |
| kapali-ik-iki-referans | kamuya_kapali | — / — | 2 / 2/3 | 2 / 2/3 | 2 / 2 |
| medya-youtube-bagli | medya | — / 3 ✗ | 2 / 3 ✗ | 2 / 2/3 | — / — |
| medya-youtube-kanal-sayfasi | medya | — / 2 ✗ | 2 / 2 | 2 / 2 | — / — |
| medya-instagram-profil | medya | 0 / 2/— ✗ | 0 / 0 | 1 / 1 | — / — |
| muhendislik-grabcad-bot-engeli | muhendislik | — / 2 ✗ | 0 / 0 | 2 / 2 | — / — |
| muhendislik-pdf-capasiz | muhendislik | — / 1 ✗ | 2 / 2 | 2 / 2 | — / — |
| pazarlama-musteri-referansi | pazarlama | — / — | 2 / 3 ✗ | 2 / 3 ✗ | 3 / 3 |
| pazarlama-ilgisiz-ansiklopedi | pazarlama | — / 0 ✗ | 2 / 2 | 2 / 2 | — / — |
| sertifika-genel-rozet-sayfasi | sertifika | 0 / 1/2 ✗ | 0 / 0 | 0 / 0 | — / — |
| sertifika-pdf-capasiz | sertifika | — / 1 ✗ | 0 / 0 | 0 / 0 | — / — |
| staj-linkedin-profil | staj_is | 2 / 2/— | 0 / 0 | 1 / 2 ✗ | — / — |
| staj-kurumsal-referans | staj_is | — / — | 2 / 3 ✗ | 2 / 3 ✗ | 3 / 3 |
| staj-referans-olumsuz | staj_is | — / — | 2 / 2 | 2 / 2 | 1 / 1 |
| staj-referans-yanitsiz | staj_is | — / — | 2 / 2 | 2 / 2 | — / — |
| tasarim-behance-bot-engeli | tasarim | — / 2 ✗ | 0 / 0 | 2 / 2 | — / — |
| tasarim-dribbble-bagli | tasarim | — / 3 ✗ | 0 / 0 | 2 / 3 ✗ | — / — |
| tasarim-dribbble-bagsiz | tasarim | — / 2 ✗ | 0 / 0 | 2 / 2 | — / — |
| tasarim-portfolyo-bagli | tasarim | 2 / 3 ✗ | 0 / 0 | 2 / 3 ✗ | — / — |
| tasarim-portfolyo-bagsiz | tasarim | 2 / 2 | 0 / 0 | 2 / 2 | — / — |
| veri-kaggle-bagsiz | veri | 2 / 2 | 0 / 0 | 2 / 2 | — / — |
| veri-kaggle-bagli | veri | 2 / 3 ✗ | 0 / 0 | 2 / 2/3 | — / — |
| veri-kanitsiz-referansli | veri | — / — | 2 / 3 ✗ | 2 / 3 ✗ | 3 / 3 |
| yarisma-genel-ana-sayfa | yarisma | 0 / 0/1 | 2 / 2 | 2 / 2 | — / — |
| yarisma-danisman-referansi | yarisma | — / — | 2 / 3 ✗ | 2 / 2 | 2 / 2 |
| yazi-medium-bagli | yazi | — / 3 ✗ | 0 / 0 | 2 / 3 ✗ | — / — |
| yazi-medium-bagsiz | yazi | — / 2 ✗ | 0 / 0 | 2 / 2 | — / — |
| yazi-kisisel-blog-bagli | yazi | 2 / 3 ✗ | 0 / 0 | 2 / 3 ✗ | — / — |
| yazi-kisisel-blog-bagsiz | yazi | 2 / 2 | 0 / 0 | 2 / 2 | — / — |
| yazi-teknik-blog-bagli | yazi | 2 / 3 ✗ | 2 / 2 | 2 / 3 ✗ | — / — |
| yazilim-bireysel-repo-bagli | yazilim | 2 / 3 ✗ | 2 / 3 ✗ | 2 / 3 ✗ | — / — |
| yazilim-bireysel-repo-bagsiz | yazilim | 2 / 2 | 2 / 2 | 2 / 2 | — / — |
| yazilim-katki-yuzde-78-bagli | yazilim | 2 / 3 ✗ | 2 / 2 | 2 / 2 | — / — |
| yazilim-baskasinin-reposu ⚠ | yazilim | 2 / 2 | 2 / 2 | 2 / 2 | — / — |
| yazilim-baskasinin-reposu-bagli-hesap ⚠ | yazilim | 2 / 2 | 2 / 2 | 2 / 2 | — / — |
| yazilim-link-404 | yazilim | 0 / 0 | 2 / 2 | 2 / 2 | — / — |
| yazilim-alan-adi-yok | yazilim | 0 / 0 | 2 / 2 | 2 / 2 | — / — |
| yazilim-kanitsiz-belirsiz | yazilim | — / — | 1 / 1 | 1 / 1 | — / — |
| yazilim-ilgisiz-link | yazilim | 0 / 0 | 2 / 2 | 2 / 2 | — / — |
