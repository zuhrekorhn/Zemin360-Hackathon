# Karne: mevcut_sistem (2026-10-05)

- Etiket kaynağı: **TASLAK ETİKET (öneriler; Zühre'nin etiketi değil)**
- Vaka: 45 toplam, 45 ölçülen
- Kabul eşikleri: **geçiyor**
- Sahte vakada yanlış 3: **0** (hedef 0)
- Bütün vakalarda yanlış 3: 0
- Notta dil ihlali olan vaka: 0 (hedef 0)
- Sonuç üretemeyen vaka: 0

## Başlık başına uyum

| Başlık | Birebir (hedef %80) | ±1 (hedef %95) | Vaka |
|---|---|---|---|
| kanit | %96 | %100 | 45 |
| sonuc | %84 | %100 | 45 |
| rol | %84 | %100 | 45 |
| referans | %100 | %100 | 45 |

## Alan kırılımı

| Alan | Kanıt "—" oranı | Dürüst vakada ort. Kanıt |
|---|---|---|
| akademik | %0 | 2.00 |
| gonulluluk | %50 | 0.00 |
| kamuya_kapali | %100 | — |
| medya | %33 | 2.50 |
| muhendislik | %0 | 1.00 |
| pazarlama | %50 | 0.00 |
| sertifika | %0 | 1.50 |
| staj_is | %75 | 2.00 |
| tasarim | %0 | 2.20 |
| veri | %33 | 2.50 |
| yarisma | %50 | 0.00 |
| yazi | %0 | 2.60 |
| yazilim | %11 | 1.33 |

## Adalet

Yalnızca dürüst, etiketli vakalar. Her alanda Kanıt 3'e giden en az bir yol olmalı; fark büyürse yeni yol eklenir, tavan düşürülmez. "—" ortalamaya girmez.

Genel ortalama Kanıt: **1.77**

| Alan | Vaka | Ort. Kanıt | En yüksek | Etiketin tavanı | '—' oranı | 3 yolu | Sorun |
|---|---|---|---|---|---|---|---|
| akademik | 2 | 2.00 | 2 | 2 | %0 | yok | 3'e giden yol yok; az vaka: ölçüm güvenilir değil |
| gonulluluk | 2 | 0.00 | 0 | 1 | %50 | yok | 3'e giden yol yok; az vaka: ölçüm güvenilir değil |
| kamuya_kapali | 3 | — | — | — | %100 | yok | 3'e giden yol yok |
| medya | 3 | 2.50 | 3 | 3 | %33 | medya-youtube-bagli |  |
| muhendislik | 2 | 1.00 | 1 | 2 | %0 | yok | 3'e giden yol yok; az vaka: ölçüm güvenilir değil |
| pazarlama | 2 | 0.00 | 0 | 0 | %50 | yok | 3'e giden yol yok; az vaka: ölçüm güvenilir değil |
| sertifika | 2 | 1.50 | 2 | 2 | %0 | yok | 3'e giden yol yok; az vaka: ölçüm güvenilir değil |
| staj_is | 4 | 2.00 | 2 | 2 | %75 | yok | 3'e giden yol yok |
| tasarim | 5 | 2.20 | 3 | 3 | %0 | tasarim-portfolyo-bagli |  |
| veri | 3 | 2.50 | 3 | 3 | %33 | veri-kaggle-bagli |  |
| yarisma | 2 | 0.00 | 0 | 1 | %50 | yok | 3'e giden yol yok; az vaka: ölçüm güvenilir değil |
| yazi | 5 | 2.60 | 3 | 3 | %0 | yazi-medium-bagli, yazi-kisisel-blog-bagli, yazi-teknik-blog-bagli |  |
| yazilim | 7 | 1.33 | 3 | 3 | %14 | yazilim-bireysel-repo-bagli, yazilim-katki-yuzde-78-bagli |  |

Dikkat: akademik, gonulluluk, kamuya_kapali, muhendislik, pazarlama, sertifika, staj_is, yarisma.

## Vakalar

Hücre: sistem / beklenen. ✗ uyuşmayan başlık.

| Vaka | Alan | Kanıt | Sonuç | Rol | Referans |
|---|---|---|---|---|---|
| akademik-arxiv-yazar-eslesiyor | akademik | 2 / 2 | 0 / 0 | 1 / 1/2 | — / — |
| akademik-arxiv-yazar-eslesmiyor ⚠ | akademik | 1 / 0/1 | 0 / 0 | 1 / 0/1 | — / — |
| akademik-dergipark-ikinci-yazar | akademik | 2 / 2 | 0 / 0 | 2 / 2 | — / — |
| gonulluluk-kurulus-ana-sayfasi-referansli | gonulluluk | 0 / 0/1 | 2 / 3 ✗ | 2 / 3 ✗ | 3 / 3 |
| gonulluluk-kanitsiz | gonulluluk | — / — | 1 / 1 | 1 / 1 | — / — |
| kapali-satis-referans | kamuya_kapali | — / — | 2 / 3 ✗ | 2 / 3 ✗ | 3 / 3 |
| kapali-finans-beyan | kamuya_kapali | — / — | 2 / 2 | 1 / 1 | — / — |
| kapali-ik-iki-referans | kamuya_kapali | — / — | 2 / 2/3 | 2 / 2/3 | 2 / 2 |
| medya-youtube-bagli | medya | 3 / 3 | 2 / 3 ✗ | 2 / 2/3 | — / — |
| medya-youtube-kanal-sayfasi | medya | 2 / 2 | 2 / 2 | 2 / 2 | — / — |
| medya-instagram-profil | medya | — / 2/— | 0 / 0 | 1 / 1 | — / — |
| muhendislik-grabcad-bot-engeli | muhendislik | 1 / 2 ✗ | 0 / 0 | 2 / 2 | — / — |
| muhendislik-pdf-capasiz | muhendislik | 1 / 1 | 2 / 2 | 2 / 2 | — / — |
| pazarlama-musteri-referansi | pazarlama | — / — | 2 / 3 ✗ | 2 / 3 ✗ | 3 / 3 |
| pazarlama-ilgisiz-ansiklopedi | pazarlama | 0 / 0 | 2 / 2 | 2 / 2 | — / — |
| sertifika-genel-rozet-sayfasi | sertifika | 2 / 1/2 | 0 / 0 | 0 / 0 | — / — |
| sertifika-pdf-capasiz | sertifika | 1 / 1 | 0 / 0 | 0 / 0 | — / — |
| staj-linkedin-profil | staj_is | 2 / 2/— | 0 / 0 | 2 / 2 | — / — |
| staj-kurumsal-referans | staj_is | — / — | 2 / 3 ✗ | 2 / 3 ✗ | 3 / 3 |
| staj-referans-olumsuz | staj_is | — / — | 2 / 2 | 2 / 2 | 1 / 1 |
| staj-referans-yanitsiz | staj_is | — / — | 2 / 2 | 2 / 2 | — / — |
| tasarim-behance-bot-engeli | tasarim | 2 / 2 | 0 / 0 | 2 / 2 | — / — |
| tasarim-dribbble-bagli | tasarim | 2 / 3 ✗ | 0 / 0 | 2 / 3 ✗ | — / — |
| tasarim-dribbble-bagsiz | tasarim | 2 / 2 | 0 / 0 | 2 / 2 | — / — |
| tasarim-portfolyo-bagli | tasarim | 3 / 3 | 0 / 0 | 2 / 3 ✗ | — / — |
| tasarim-portfolyo-bagsiz | tasarim | 2 / 2 | 0 / 0 | 2 / 2 | — / — |
| veri-kaggle-bagsiz | veri | 2 / 2 | 0 / 0 | 2 / 2 | — / — |
| veri-kaggle-bagli | veri | 3 / 3 | 0 / 0 | 2 / 2/3 | — / — |
| veri-kanitsiz-referansli | veri | — / — | 2 / 3 ✗ | 2 / 3 ✗ | 3 / 3 |
| yarisma-genel-ana-sayfa | yarisma | 0 / 0/1 | 2 / 2 | 2 / 2 | — / — |
| yarisma-danisman-referansi | yarisma | — / — | 2 / 3 ✗ | 2 / 2 | 2 / 2 |
| yazi-medium-bagli | yazi | 3 / 3 | 0 / 0 | 3 / 3 | — / — |
| yazi-medium-bagsiz | yazi | 2 / 2 | 0 / 0 | 2 / 2 | — / — |
| yazi-kisisel-blog-bagli | yazi | 3 / 3 | 0 / 0 | 3 / 3 | — / — |
| yazi-kisisel-blog-bagsiz | yazi | 2 / 2 | 0 / 0 | 2 / 2 | — / — |
| yazi-teknik-blog-bagli | yazi | 3 / 3 | 2 / 2 | 3 / 3 | — / — |
| yazilim-bireysel-repo-bagli | yazilim | 3 / 3 | 3 / 3 | 3 / 3 | — / — |
| yazilim-bireysel-repo-bagsiz | yazilim | 2 / 2 | 2 / 2 | 2 / 2 | — / — |
| yazilim-katki-yuzde-78-bagli | yazilim | 3 / 3 | 2 / 2 | 2 / 2 | — / — |
| yazilim-baskasinin-reposu ⚠ | yazilim | 2 / 2 | 2 / 2 | 2 / 2 | — / — |
| yazilim-baskasinin-reposu-bagli-hesap ⚠ | yazilim | 2 / 2 | 2 / 2 | 2 / 2 | — / — |
| yazilim-link-404 | yazilim | 0 / 0 | 2 / 2 | 2 / 2 | — / — |
| yazilim-alan-adi-yok | yazilim | 0 / 0 | 2 / 2 | 2 / 2 | — / — |
| yazilim-kanitsiz-belirsiz | yazilim | — / — | 1 / 1 | 1 / 1 | — / — |
| yazilim-ilgisiz-link | yazilim | 0 / 0 | 2 / 2 | 2 / 2 | — / — |
