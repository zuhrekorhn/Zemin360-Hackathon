# Karne: mevcut_sistem (2026-10-01)

- Etiket kaynağı: **TASLAK ETİKET (öneriler; Zühre'nin etiketi değil)**
- Vaka: 45 toplam, 45 ölçülen
- Kabul eşikleri: **geçmiyor**
- Sahte vakada yanlış 3: **4** (hedef 0)
- Bütün vakalarda yanlış 3: 31
- Notta dil ihlali olan vaka: 18 (hedef 0)
- Sonuç üretemeyen vaka: 0

## Başlık başına uyum

| Başlık | Birebir (hedef %80) | ±1 (hedef %95) | Vaka |
|---|---|---|---|
| kanit | %56 | %87 | 45 |
| sonuc | %44 | %71 | 45 |
| rol | %27 | %69 | 45 |
| referans | %100 | %100 | 45 |

## Alan kırılımı

| Alan | Kanıt "—" oranı | Dürüst vakada ort. Kanıt |
|---|---|---|
| akademik | %0 | 3.00 |
| gonulluluk | %50 | 2.00 |
| kamuya_kapali | %100 | — |
| medya | %0 | 2.00 |
| muhendislik | %50 | 0.00 |
| pazarlama | %50 | 0.00 |
| sertifika | %50 | 2.00 |
| staj_is | %75 | 2.00 |
| tasarim | %0 | 1.60 |
| veri | %33 | 2.00 |
| yarisma | %50 | 2.00 |
| yazi | %0 | 1.20 |
| yazilim | %11 | 1.17 |

## Yanlış 3

- akademik-arxiv-yazar-eslesiyor:kanit
- akademik-dergipark-ikinci-yazar:kanit
- medya-youtube-kanal-sayfasi:sonuc
- medya-youtube-kanal-sayfasi:rol
- muhendislik-grabcad-bot-engeli:rol
- pazarlama-ilgisiz-ansiklopedi:sonuc
- pazarlama-ilgisiz-ansiklopedi:rol
- sertifika-genel-rozet-sayfasi:rol
- tasarim-behance-bot-engeli:rol
- tasarim-dribbble-bagsiz:rol
- tasarim-portfolyo-bagsiz:rol
- veri-kaggle-bagsiz:rol
- yarisma-genel-ana-sayfa:sonuc
- yarisma-genel-ana-sayfa:rol
- yazi-medium-bagsiz:rol
- yazi-kisisel-blog-bagsiz:rol
- yazi-teknik-blog-bagli:sonuc
- yazilim-bireysel-repo-bagsiz:sonuc
- yazilim-bireysel-repo-bagsiz:rol
- yazilim-katki-yuzde-78-bagli:sonuc
- yazilim-katki-yuzde-78-bagli:rol
- yazilim-baskasinin-reposu:sonuc (kötü niyetli)
- yazilim-baskasinin-reposu:rol (kötü niyetli)
- yazilim-baskasinin-reposu-bagli-hesap:sonuc (kötü niyetli)
- yazilim-baskasinin-reposu-bagli-hesap:rol (kötü niyetli)
- yazilim-link-404:sonuc
- yazilim-link-404:rol
- yazilim-alan-adi-yok:sonuc
- yazilim-alan-adi-yok:rol
- yazilim-ilgisiz-link:sonuc
- yazilim-ilgisiz-link:rol

## Notta dil ihlalleri

- akademik-arxiv-yazar-eslesmiyor: hitap: payınız
- medya-youtube-bagli: hitap: size
- medya-youtube-kanal-sayfasi: hitap: size
- medya-instagram-profil: hitap: payınız, size
- sertifika-genel-rozet-sayfasi: hitap: geçtiğiniz, size
- tasarim-behance-bot-engeli: hitap: rolünüzün, tasarladığınızı
- tasarim-portfolyo-bagli: hitap: başınıza, etmişsiniz, rolünüzü, size, yürüttüğünüzü
- tasarim-portfolyo-bagsiz: hitap: başınıza, etmişsiniz, rolünüzü, size, yürüttüğünüzü
- veri-kaggle-bagsiz: hitap: başınıza, belirtmişsiniz, hazırladığınızı
- veri-kaggle-bagli: hitap: başınıza, belirtmişsiniz, hazırladığınızı
- yarisma-genel-ana-sayfa: hitap: sizinle
- yazi-medium-bagli: hitap: aldığınız, üstlendiğiniz
- yazi-medium-bagsiz: hitap: aldığınız, üstlendiğiniz
- yazilim-bireysel-repo-bagli: hitap: size
- yazilim-bireysel-repo-bagsiz: hitap: size
- yazilim-katki-yuzde-78-bagli: hitap: başınıza, rolünüzü, size, üstlendiğinizi
- yazilim-baskasinin-reposu: hitap: size
- yazilim-baskasinin-reposu-bagli-hesap: hitap: başınıza, size, yazdığınızı, üstlendiğiniz

## Vakalar

Hücre: sistem / beklenen. ✗ uyuşmayan başlık.

| Vaka | Alan | Kanıt | Sonuç | Rol | Referans |
|---|---|---|---|---|---|
| akademik-arxiv-yazar-eslesiyor | akademik | 3 / 2 ✗ | 0 / 0 | 2 / 1/2 | — / — |
| akademik-arxiv-yazar-eslesmiyor ⚠ | akademik | 2 / 0/1 ✗ | 0 / 0 | 2 / 0/1 ✗ | — / — |
| akademik-dergipark-ikinci-yazar | akademik | 3 / 2 ✗ | 0 / 0 | 2 / 2 | — / — |
| gonulluluk-kurulus-ana-sayfasi-referansli | gonulluluk | 2 / 0/1 ✗ | 3 / 3 | 3 / 3 | 3 / 3 |
| gonulluluk-kanitsiz | gonulluluk | — / — | — / 1 ✗ | — / 1 ✗ | — / — |
| kapali-satis-referans | kamuya_kapali | — / — | — / 3 ✗ | — / 3 ✗ | 3 / 3 |
| kapali-finans-beyan | kamuya_kapali | — / — | — / 2 ✗ | — / 1 ✗ | — / — |
| kapali-ik-iki-referans | kamuya_kapali | — / — | — / 2/3 ✗ | — / 2/3 ✗ | 2 / 2 |
| medya-youtube-bagli | medya | 2 / 3 ✗ | 3 / 3 | 3 / 2/3 | — / — |
| medya-youtube-kanal-sayfasi | medya | 2 / 2 | 3 / 2 ✗ | 3 / 2 ✗ | — / — |
| medya-instagram-profil | medya | 2 / 2/— | 0 / 0 | 2 / 1 ✗ | — / — |
| muhendislik-grabcad-bot-engeli | muhendislik | 0 / 2 ✗ | 0 / 0 | 3 / 2 ✗ | — / — |
| muhendislik-pdf-capasiz | muhendislik | — / 1 ✗ | — / 2 ✗ | — / 2 ✗ | — / — |
| pazarlama-musteri-referansi | pazarlama | — / — | — / 3 ✗ | — / 3 ✗ | 3 / 3 |
| pazarlama-ilgisiz-ansiklopedi | pazarlama | 0 / 0 | 3 / 2 ✗ | 3 / 2 ✗ | — / — |
| sertifika-genel-rozet-sayfasi | sertifika | 2 / 1/2 | 1 / 0 ✗ | 3 / 0 ✗ | — / — |
| sertifika-pdf-capasiz | sertifika | — / 1 ✗ | — / 0 ✗ | — / 0 ✗ | — / — |
| staj-linkedin-profil | staj_is | 2 / 2/— | 0 / 0 | 2 / 2 | — / — |
| staj-kurumsal-referans | staj_is | — / — | — / 3 ✗ | — / 3 ✗ | 3 / 3 |
| staj-referans-olumsuz | staj_is | — / — | — / 2 ✗ | — / 2 ✗ | 1 / 1 |
| staj-referans-yanitsiz | staj_is | — / — | — / 2 ✗ | — / 2 ✗ | — / — |
| tasarim-behance-bot-engeli | tasarim | 0 / 2 ✗ | 0 / 0 | 3 / 2 ✗ | — / — |
| tasarim-dribbble-bagli | tasarim | 2 / 3 ✗ | 0 / 0 | 3 / 3 | — / — |
| tasarim-dribbble-bagsiz | tasarim | 2 / 2 | 0 / 0 | 3 / 2 ✗ | — / — |
| tasarim-portfolyo-bagli | tasarim | 2 / 3 ✗ | 0 / 0 | 3 / 3 | — / — |
| tasarim-portfolyo-bagsiz | tasarim | 2 / 2 | 0 / 0 | 3 / 2 ✗ | — / — |
| veri-kaggle-bagsiz | veri | 2 / 2 | 0 / 0 | 3 / 2 ✗ | — / — |
| veri-kaggle-bagli | veri | 2 / 3 ✗ | 0 / 0 | 3 / 2/3 | — / — |
| veri-kanitsiz-referansli | veri | — / — | — / 3 ✗ | — / 3 ✗ | 3 / 3 |
| yarisma-genel-ana-sayfa | yarisma | 2 / 0/1 ✗ | 3 / 2 ✗ | 3 / 2 ✗ | — / — |
| yarisma-danisman-referansi | yarisma | — / — | — / 3 ✗ | — / 2 ✗ | 2 / 2 |
| yazi-medium-bagli | yazi | 0 / 3 ✗ | 0 / 0 | 3 / 3 | — / — |
| yazi-medium-bagsiz | yazi | 0 / 2 ✗ | 0 / 0 | 3 / 2 ✗ | — / — |
| yazi-kisisel-blog-bagli | yazi | 2 / 3 ✗ | 0 / 0 | 3 / 3 | — / — |
| yazi-kisisel-blog-bagsiz | yazi | 2 / 2 | 0 / 0 | 3 / 2 ✗ | — / — |
| yazi-teknik-blog-bagli | yazi | 2 / 3 ✗ | 3 / 2 ✗ | 3 / 3 | — / — |
| yazilim-bireysel-repo-bagli | yazilim | 2 / 3 ✗ | 3 / 3 | 3 / 3 | — / — |
| yazilim-bireysel-repo-bagsiz | yazilim | 2 / 2 | 3 / 2 ✗ | 3 / 2 ✗ | — / — |
| yazilim-katki-yuzde-78-bagli | yazilim | 2 / 3 ✗ | 3 / 2 ✗ | 3 / 2 ✗ | — / — |
| yazilim-baskasinin-reposu ⚠ | yazilim | 2 / 2 | 3 / 2 ✗ | 3 / 2 ✗ | — / — |
| yazilim-baskasinin-reposu-bagli-hesap ⚠ | yazilim | 2 / 2 | 3 / 2 ✗ | 3 / 2 ✗ | — / — |
| yazilim-link-404 | yazilim | 0 / 0 | 3 / 2 ✗ | 3 / 2 ✗ | — / — |
| yazilim-alan-adi-yok | yazilim | 0 / 0 | 3 / 2 ✗ | 3 / 2 ✗ | — / — |
| yazilim-kanitsiz-belirsiz | yazilim | — / — | — / 1 ✗ | — / 1 ✗ | — / — |
| yazilim-ilgisiz-link | yazilim | 1 / 0 ✗ | 3 / 2 ✗ | 3 / 2 ✗ | — / — |
