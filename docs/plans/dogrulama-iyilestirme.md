# Doğrulama İyileştirme Planı (sürüm 3)

> **Durum:** Onaylandı (1 Eki 2026). Karar 1–13 kapandı (§ 17). Uygulama § 15'teki sırayla yürür. Her adımın sonunda testler çalışır, değerlendirme seti karnesi çıkarılır ve onay beklenir.
> **Sürüm 3'te değişenler:** kaynak katmanları "Seviye A–D" adını aldı. Seviye D daraltıldı ve bireysel proje kuralları eklendi (§ 2). Uzun içerik seçimi eklendi (§ 5.4), ekran görüntüsü yolu eklendi (§ 5.5), Google Drive ve Docs okuyucusu eklendi (§ 5.6). İlgisiz kanıt artık 0. Yetenek bazlı kanıt eklendi (§ 11). Ad ve kimlik bütünlüğü eklendi (§ 6.3). Hesap bağlama gerçekçi hâline getirildi (§ 6). Link çürümesi sayacı düzeltildi (§ 10.4). Etiketleme süreci eklendi (§ 10.1). Dış servisler bayrak ve zarif düşüşle tanımlandı (§ 14.4). Yeni bulgular 45–49. Adım adım uygulama planı eklendi (§ 15).
> **Uygulama notu (Adım 1):** değerlendirme seti çalışırken bulgu 50 (ReDoS) bulundu; üretimdeki etkisi yüzünden Adım 2'nin ilk commit'i olarak düzeltildi. Bulgu 7 (karakter kodları) ve 52 de aynı değişiklikle kapandı.
> **Değiştirdiği belgelenmiş kararlar** (her biri ilgili adımın commit'inde güncellenir): `agent-specs.md` § 4 (karar 13: yalnızca başlık okunur; referans formu), karar 7 (linksiz kalem), "SMTP yok" MVP kararı, `matching-algorithm.md` § 4 (boş başlık bonusa girmez), `sequence-diagrams.md` Akış 2, `api-contracts.md` § Doğrulama, `data-schema.md`.

---

## 0. Özet

Bugünkü Doğrulama, linkin yalnızca `<head>` kısmını okuyor ve puanı modelin takdirine bırakıyor. Gerçek denemelerde sonuç şöyle oldu:
- Başkasına ait bir repo 12 üzerinden 8 aldı.
- Behance ve Medium linkleri "açılmıyor" sayılıp 0 aldı.
- Kanıtsız iddia Sonuç ve Rol'den tam puan aldı.

Yeni tasarımda dört şey değişiyor:
1. **Kanıtın kaynağı seviyelendirilir** (A–D, § 2).
2. **Puanı kural verir.** Model yalnızca alıntıyla gerçek çıkarır.
3. **Okunamayan link için alternatif yollar sunulur:** PDF, görsel, referans, hesap bağlama.
4. **Sistem kendini ölçer:** etiketli set, adalet ölçümü, gözlem.

---

## 1. İlkeler

| # | İlke | Sonuç |
|---|---|---|
| İ1 | **Ajan sinyal toplar, hüküm vermez** | Şüphe puanı kendiliğinden düşürmez; GİRVAK inceleme kuyruğuna gider (§ 9) |
| İ2 | **Beyan kanıt değildir** | Yazılmış iddia, çapasız yüklenmiş dosya ve doğrulanmamış kullanıcı adı tek başına üst puan getirmez |
| İ3 | **Kanıtın gücü kaynağın bağımsızlığıdır** | Seviyeler puan tavanını belirler (§ 2) |
| İ4 | **Değerlendirilmeyen, değerlendirilmiş gibi görünmez** | Okunamayan, istenmeyen ya da yanıtlanmayan başlık "—" (NULL) olur, asla 0 olmaz |
| İ5 | **Her meslek için eşit güçte bir yol** | Kamuya açık çıktısı olmayan meslekler referans, belge ve hesap bağlamayla aynı tavana ulaşır. Bireysel projeler kurum işiyle aynı tavana ulaşır. Adalet ölçülür |
| İ6 | **Model gerçek çıkarır, kural puanlar, şablon anlatır** | Puan test edilebilir; not sayılarla çelişmez |
| İ7 | **Tek kural, tek yer** | Kanıt değişimi, referans durumu ve puan kuralları tek fonksiyondadır; arayüz kuralı tekrar etmez, bayrağı okur |
| İ8 | **Ölçmeden değiştirme** | Her puan değişikliği etiketli sette önce ve sonra çalıştırılır |
| İ9 | **Hiçbir dış servis hatası değerlendirmeyi düşürmez** | Servis kapalıysa ya da hata verirse ilgili sinyal "—" olur ve akış devam eder (§ 14.4) |

---

## 2. Kaynak seviyeleri (çekirdek model)

Koddaki karşılığı `KaynakSeviyesi` enum'u: `DUZENLEYEN` (A), `PLATFORM` (B), `KAMUYA_ACIK` (C), `BEYAN` (D).

| Seviye | Enum | Örnekler | Neden bu güçte |
|---|---|---|---|
| **A** | `DUZENLEYEN` | İmzalı Open Badges / Credly rozeti; geçerli e-imzalı PDF; QR / doğrulama adresi düzenleyenin sitesine gidip **kimlik koşulunu** (§ 6.3) sağlayan belge; GİRVAK'ın doğruladığı e-Devlet barkodlu belge; organizatörün sonuç sayfasında / PDF'inde ad (kimlik koşuluyla); e-postası doğrulanmış referansın "evet" yanıtı | Belgeyi bağımsız bir kurum üretmiş ve kimlik bağı var |
| **B** | `PLATFORM` | OAuth ya da profil koduyla **bağlı hesaba** ait çalışma: repo, yayımlanmış yazı, portfolyo işi, video, Kaggle notebook'u; platform verisi (commit oranı, yıldız, indirme, mağaza sayıları) | Hesabın gence ait olduğu kanıtlanmış; sayılar platformdan geliyor |
| **C** | `KAMUYA_ACIK` | Herkese açık yayımlanmış çalışmanın kendisi: repodaki kod, blog / Medium / Substack yazısı, portfolyo sitesindeki iş, video, herkese açık Drive dosyası, yedek okuyucunun ekran görüntüsü; sayfada adın geçmesi (kimlik koşulu yoksa) | Çalışma gerçek ve görülebilir, ama kimin olduğu kanıtlanmamış |
| **D** | `BEYAN` | **Yalnızca:** gencin sohbette ya da formda yazdığı iddia metni; çapası olmayan yüklenmiş dosya veya görsel; doğrulanmamış kullanıcı adı | Genç üretmiş ya da kolayca üretebilir |

**Çalışmanın içindeki iddialar** (README'deki kullanıcı sayısı, portfolyodaki "satışı %40 artırdı", "backend'i ben yazdım" cümlesi) çalışma hangi seviyede olursa olsun **iddia** olarak kalır. Tek başına Sonuç ve Rol'ü en çok 2'ye çıkarır. 3 için platform verisi (B), A seviyesinde bir belge ya da referans gerekir.

**Puan tavanları:**

| Başlık | D | C | B | A |
|---|---|---|---|---|
| Kanıt (iş var mı, bu kişinin mi) | — (iddia metni) / 1 (çapasız dosya) | 2 | 3 | 3 |
| Sonuç | 2 (açık yazılmışsa) | 2 | 3 (platform verisi sonucu gösteriyorsa) | 3 |
| Rol | 2 (açık yazılmışsa) | 2 | 3 (katkı oranı ya da bireysel proje kuralı) | 3 (belge rolü adlandırıyorsa ya da referans "pay doğru: evet") |

**Bireysel proje kuralları** (kurum ya da referans bağı şart değil; bu işler kurum işiyle aynı tavana ulaşır):

| Durum | Kanıt | Rol |
|---|---|---|
| Bağlı hesaba ait, tek katkıcılı repo (commit'lerin en az %90'ı gencin) | 3 | 3 |
| Bağlı hesapta tek yazarlı (byline) yayımlanmış yazı | 3 | 3 |
| Bağlı portfolyo sitesindeki iş | 3 | Sayfada ekip / ajans / müşteri ortaklığı belirtilmemişse 3, belirtilmişse 2 |
| Aynı işler, hesap bağlı değil | 2 | 2 |

**Birden çok parça:** bir kalemin birden çok kanıt parçası olabilir (link + PDF + referans). Her başlık için **en güçlü parça** kullanılır; parçalar toplanmaz. Kanıt eklemek böylece puanı hiçbir zaman düşürmez.

---

## 3. Kanıt türleri ve akışları

| Tür | Ne zaman | Akış |
|---|---|---|
| **Link** | İş kamuya açık bir yerdeyse | Okuyucu zinciri → erişim durumu → içerik (gerekirse parça seçimi) → seviye (§ 5) |
| **Dosya (PDF)** | Link okunamadı, iş kamuya açık değil; rapor, sertifika, portfolyo, sonuç listesi | Güvenli yükleme → içerik çıkarma → çapa arama → seviye (§ 4) |
| **Görsel** | Tasarım, fotoğraf, ekran görüntüsü, fiziksel iş | Güvenli yükleme → görsel analiz → kaynak araması → C2PA → seviye (§ 4) |
| **Referans** | Her meslekte; kamuya açık çıktısı olmayan işlerde birincil yol | E-postayla doğrudan referansa giden 4 soruluk form (§ 7) |
| **Hesap bağlama** | GitHub, GitLab, ORCID (OAuth); YouTube ve diğerleri (profil kodu) | Bağlı hesaptaki çalışmalar seviye B (§ 6) |

**Okunamayan link için seçenek kutusu:**

| Erişim durumu | Gence gösterilen | Seçenekler |
|---|---|---|
| `GIRIS_GEREKLI` (LinkedIn, Instagram) | "Bu link yalnızca giriş yapanlara açık; içeriğini göremedik." | Herkese açık link ver · PDF olarak yükle · Ekran görüntüsü ekle · Referans ekle |
| `GIRIS_GEREKLI` (Google Drive / Docs) | "Paylaşım ayarını 'Bağlantıya sahip olan herkes' yaparsan içeriğini okuyabiliriz." | Paylaşımı aç, yeniden dene · PDF olarak yükle · Referans ekle |
| `ENGELLENDI` | "Bu siteye otomatik olarak ulaşamadık; senin hatan değil." | Hesabını bağla · PDF olarak yükle · Görsel ekle · Referans ekle |
| `ICERIK_YOK` | "Sayfa açıldı ama içeriği okunamadı." | Kaynak kod linki ekle · Ekran görüntüsü ekle · Referans ekle |
| `BULUNAMADI` | "Bu adreste bir sayfa yok." | Linki düzelt · PDF yükle · Referans ekle |

Seçenekler meslek alanına göre sıralanır (§ 8).

**İlgisiz kanıt:** link açılır ama çalışmayla ilgisizse Kanıt 0 olur ve kaleme `alakasiz_kanit` işareti düşer. Gence şablon cümlesi gösterilir: "Eklediğin link bu çalışmayla ilgili görünmüyor." Bu bir kötüye kullanım işareti değildir, GİRVAK kuyruğuna girmez.

---

## 4. Dosya ve görsel kanıtı

### 4.1 İlke

**Dosyanın kendisi kanıt değildir; içindeki doğrulanabilir çapa kanıttır.** Çapasız yüklenmiş dosya seviye D'dir; çapası doğrulanan dosya seviye A'ya çıkar. Sahte bir PDF en çok D alır, bu yüzden sahtecilik tespitinde kusursuz olmak gerekmez. Belge sahteciliği tespit eden firmalar (Resistant AI, Inscribe) bile yapay zekâ ile üretilmiş belgelerde zorlanıyor.

### 4.2 Doğrulanabilir çapalar

| Çapa | Bulma | Doğrulama | Sonuç |
|---|---|---|---|
| QR / doğrulama adresi | PDF sayfası görüntüye çevrilir (`pypdfium2`), QR okunur (`zxing-cpp`); metinde doğrulama adresi aranır | Adres güvenli istekle açılır. Alan adı bilinen düzenleyen listesinde mi; sayfada belge başlığı ve kimlik koşulu (§ 6.3) var mı | Koşullar sağlanırsa A, sağlanmazsa C |
| Elektronik imza (PAdES) | `pyHanko` | İmza geçerli mi, belge imzadan sonra değişmemiş mi, zincir güvenilir köke (Kamu SM ve yaygın kökler) gidiyor mu | Geçerliyse A; bozuksa işaret (§ 9) |
| Open Badges | PNG / SVG içine gömülü veri ya da rozet adresi | İmza, düzenleyen, alıcı (alıcı e-postası hesap e-postasıyla eşleşirse en güçlü sinyal) | A |
| e-Devlet barkodu | Barkod numarası, e-Devlet ibaresi | GİRVAK turkiye.gov.tr/belge-dogrulama'da elle doğrular (kuyruk). T.C. kimlik no saklanmaz | GİRVAK onayı → A |
| Organizatör belgesi | Sonuç listesi | Link olarak verilirse alan adı organizatörün mü ve adda kimlik koşulu var mı | Link + koşul → A; yalnızca yükleme → D |

Normalleştirilmiş doğrulama adresi tekildir. Aynı adres ikinci bir hesapta kullanılırsa reddedilmez; `ayni_belge_iki_hesapta` işaretiyle GİRVAK kuyruğuna düşer.

### 4.3 İçerik analizi

- **PDF:** metin katmanı olan PDF'te önce `pypdf` ile çıkarım yapılır. Taranmış PDF ya da görsel ağırlıklı PDF Gemini'nin belge anlama özelliğiyle okunur (50 MB / 1000 sayfa sınırı).
- **Görsel:** iki adımdır.
  - (a) Model görseldeki metni (`gorsel_metni`) ve görülen içeriğin betimini çıkarır.
  - (b) İddia karşılaştırması bunun üzerinden yapılır; alıntı denetimi `gorsel_metni`'ne karşı çalışır.
- **Kaynak araması:** Cloud Vision Web Detection (bayrakla, § 14.4). Görselin internette başkasında, daha eski tarihte bulunması bir işarettir.
- **C2PA:** `c2pa-python` ile içerik kimlik bilgisi okunur. Varsa üretim aracı ve düzenleme geçmişi notta yer alır; yoksa hiçbir sonuç çıkarılmaz.
- **EXIF:** zayıf sinyal olarak okunur, sonra silinir.
- **Yapay zekâ tespiti yapılmaz.** Bu sınıflandırıcılar güvenilir değil; seviye sistemi riski zaten sınırlıyor.

### 4.4 Güvenli yükleme

| Konu | Karar |
|---|---|
| Saklama | Cloudflare R2, özel kova; anahtar rastgele, dosya adı kullanıcıdan alınmaz |
| Türler | PDF, PNG, JPEG, WebP, HEIC; tür ilk baytlardan belirlenir (`filetype`) |
| Boyut | PDF 20 MB, görsel 10 MB; kalem başına en çok 5 dosya; kullanıcı başına günlük sınır |
| Zararlı içerik | ClamAV (ayrı konteyner); PDF'teki JavaScript ve gömülü dosyalar `pikepdf` ile temizlenir |
| Görsel temizliği | Pillow ile yeniden kodlama; EXIF ve konum silinir; çok biçimli (polyglot) dosyalar etkisizleşir |
| Sunum | Kısa ömürlü imzalı adres, `Content-Disposition: attachment`, ayrı alan adı |
| Görünürlük | Varsayılan olarak yalnızca genç ve GİRVAK görür; firma sonucu görür. Genç kalem başına "firmalar görebilir" seçebilir |
| Kişisel veri | Çıkarılan metinde T.C. kimlik no, telefon ve adres maskelenir. Kalem silinince dosya da silinir. KVKK aydınlatma metnine eklenir |
| Tekrar | Aynı dosya özeti (SHA-256) başka hesapta varsa işaret |

---

## 5. Link okuma

### 5.1 Okuyucu zinciri (Strategy + Chain of Responsibility)

```
app/core/kanit_okuma/
  __init__.py            kaniti_oku(kaynak, baglam) → KanitBelgesi
  belge.py               KanitBelgesi, ErisimDurumu, KaynakSeviyesi, MetinParcasi (değer nesneleri)
  okuyucu.py             Okuyucu Protocol: uygun_mu(url) / oku(url, baglam) → KanitBelgesi | None
  kayit.py               okuyucu listesi (sıralı); yeni platform = yeni sınıf + bir satır
  istek.py               guvenli_get sarmalayıcısı: tarayıcı başlıkları, akışlı 2 MB, unescape
  erisim.py              giriş duvarı / bot engeli / içerik yok tespiti (saf)
  parca_secimi.py        uzun içerik: bölme, embedding, iddia başına seçim (§ 5.4)
  onbellek.py            URL özeti → belge (24 saat)
  okuyucular/
    github.py  gitlab.py  oembed.py  youtube.py  medium.py  google.py
    akademik.py  sertifika.py  magaza.py  devpost.py  html_genel.py
  dosya/
    hat.py               yükleme hattı: tür → boyut → virüs → temizlik → analiz
    pdf.py  gorsel.py  qr.py  imza.py  rozet.py  c2pa.py
```

Zincir sırası:
1. Platform okuyucusu (resmî API / oEmbed / RSS / dışa aktarma adresi).
2. Genel okuyucu (trafilatura + JSON-LD + meta).
3. Yedek okuyucu (Playwright; gerekirse ekran görüntüsü).
4. Jina (bayrak açıksa).
5. Erişim durumu.

### 5.2 Erişim durumları

| Durum | Kanıt | Tespit |
|---|---|---|
| `ACIK` | Kurallarla | İçerik okundu |
| `GIRIS_GEREKLI` | — | Son adreste `login`, `signin`, `authwall`, `ServiceLogin`; giriş başlığı; platform kuralı |
| `ENGELLENDI` | — | 403, 429, 999, Cloudflare sayfası; yedek okuyucu da açamadı |
| `ICERIK_YOK` | — | Metin 200 karakterden az ve ekran görüntüsü de alınamadı |
| `BULUNAMADI` | 0 | 404, 410, alan adı yok (`AdresBulunamadi`) |
| `GUVENSIZ` | 0 | SSRF kuralı |
| `HATA` | — | Zaman aşımı, ağ hatası; sonra yeniden denenir |

### 5.3 İstek

- **Başlıklar:** gerçekçi `User-Agent`, `Accept`, `Accept-Language: tr-TR,tr;q=0.9,en;q=0.8`.
- **Okuma:** gövde 2 MB'a kadar akışla okunur; karakter kodları `html.unescape` ile çözülür.
- **Tek kapı:** sabit API uç noktaları da `guvenli_istek.py`'den geçer.
- **API sınırları:** GitHub uygulama tokenı (5.000 istek/saat); aynı URL için 24 saatlik önbellek.

### 5.4 Uzun içerik: kesme yok, seçme var

- **Kısa metin:** 8.000 karakteri aşmıyorsa olduğu gibi kullanılır.
- **Uzun metin:**
  - Yaklaşık 1.500 karakterlik parçalara bölünür, parçalar arasında 200 karakter örtüşme olur.
  - Parçalar mevcut embedding modeliyle (Voyage, 1024 boyut) vektörleştirilir.
  - Her iddia (iş, sonuç, pay) için pgvector ile en ilgili 4 parça seçilir. Belgenin ilk parçası (başlık, README girişi) her zaman eklenir. Model yalnızca bu parçaları görür.
- **Alıntı denetimi** seçilen parçalara değil, **tam metne** karşı yapılır.
- **Saklama:** parçalar `kanit_metin_parcasi` tablosunda `kanit_parcasi` ile ilişkili tutulur. İtiraz ve yeniden değerlendirmede tekrar hesaplanmaz.
- **Arayüz:** seçim `ParcaSecici` arayüzünün arkasındadır. Üretim sürümü pgvector'dür; testlerde bellek içi sürüm kullanılır (testler veritabanına bağlanmıyor).

### 5.5 Görsel siteler için ekran görüntüsü yolu

- **Ne döner:** yedek okuyucu (kendi Playwright servisimiz) metinle birlikte ekran görüntüsü de döndürür: tam sayfa, 1280 px genişlik, en çok 3 parça.
- **Ne zaman alınır:**
  - platform görsel ağırlıklıysa (Behance, Dribbble, ArtStation, kişisel portfolyo alan adı),
  - metin 200 karakterin altındaysa,
  - durum `ICERIK_YOK` ise.
- **Analiz:** görsel analizinin iki adımı uygulanır (§ 4.3); alıntı denetimi `gorsel_metni`'ne karşıdır.
- **Seviye:** kaynak herkese açık bir link olduğu için C'dir (yüklenmiş görsel gibi D değil). Hesap bağlıysa B'dir.

### 5.6 Google Drive ve Docs okuyucusu (`okuyucular/google.py`)

| Giriş | Dönüşüm |
|---|---|
| `drive.google.com/file/d/{id}/...` | `drive.usercontent.google.com/download?id={id}&export=download&confirm=t` |
| `docs.google.com/document/d/{id}` | `…/export?format=txt` |
| `docs.google.com/spreadsheets/d/{id}` | `…/export?format=csv` |
| `docs.google.com/presentation/d/{id}` | `…/export/pdf` |

- İndirilen dosya dosya analiz hattına girer (tür, boyut, `pikepdf`). Seviye C'dir.
- `ServiceLogin`'e yönlenirse durum `GIRIS_GEREKLI` olur ve gence paylaşım ayarı cümlesi gösterilir (§ 3).

---

## 6. Hesap bağlama ve kimlik

### 6.1 Hesap bağlama

| Yöntem | Platform | Kapsam / araç | Seviye |
|---|---|---|---|
| OAuth | GitHub | `read:user` | B |
| OAuth | GitLab | `read_user` | B |
| OAuth | ORCID | `/authenticate` | B |
| Profil kodu + YouTube Data API (uygulama API anahtarı) | YouTube | Kanal açıklamasında kod | B |
| Profil kodu | Kaggle, Behance, Dribbble, Medium, Vimeo, SoundCloud, kişisel site | Profil açıklamasında / sitede kod | B |

- **Google OAuth kullanılmaz.** YouTube ve Drive kapsamları Google'ın uygulama doğrulamasını gerektiriyor.
- **Kişisel API anahtarı hiçbir platform için istenmez.**
- `bagli_hesap` tablosunda (`saglayici`, `dis_kimlik`) tekildir: bir hesap iki gence bağlanamaz.
- **OAuth token'ı saklanmaz.** Bağlama anında kullanıcı adı ve dış kimlik okunur, token atılır.

### 6.2 Profil kodu

- **Biçim:** `z360-` + 8 rastgele karakter.
- **Geçerlilik:** 48 saat; kullanıcı ve platform başına tek kod.
- **Bağlantı:** kod doğrulandıktan sonra profilden kaldırılabilir; bağlantı kalıcıdır.
- **Profil okunamazsa** (bot engeli): önce yedek okuyucu denenir; o da açamazsa GİRVAK elle doğrular (kuyruk). Ekran görüntüsüyle doğrulama kabul edilmez.
- **Yaklaşım:** her platform bir `ProfilKoduPlatformu` stratejisidir (profil adresi, kodun aranacağı alan).

### 6.3 Ad ve kimlik bütünlüğü

- **Doğrulama:** kayıtta e-posta doğrulanır (bağlantılı e-posta, Resend).
- **Ad kilidi:** e-posta doğrulandıktan sonra `kimlik_adi` (bugünkü `kullanici.ad`) kilitlenir. Kilit ayrıca saklanmaz, e-posta doğrulama tarihinden türetilir.
- **Ad değişikliği:** talep GİRVAK kuyruğuna gider. Onaylanırsa `sahiplik_kaynagi = "ad"` olan bütün kanıt parçaları yeniden değerlendirilir.
- **Ada dayalı seviye A için üç koşul birlikte gerekir:** ad eşleşmesi, doğrulanmış e-posta, kilitli ad. Biri eksikse en çok seviye C.
- **E-posta eşleşmesi daha güçlüdür:** doğrulama sayfası ya da rozet bir e-posta gösteriyorsa (Credly vb.), bu e-postanın hesap e-postasıyla eşleşmesi ada göre öncelikli ve daha güçlü bir sinyaldir.
- **Ad eşleşmesi kuralı:** Türkçe karakterden bağımsızdır (`turkce_kucult` + aksan temizleme); bütün ad parçaları sırası fark etmeksizin geçmelidir.

---

## 7. Referans

- **Gönderim:** e-posta doğrudan referansa gider (Resend; SPF ve DKIM ayarlı). Genç yanıt linkini görmez; hiçbir API yanıtında token yoktur.
- **Hatırlatma:** 3. günde bir kez; 7. günde "yanıt yok" (nötr). İkisi de Canlılık taramasıyla.
- **Form:**
  1. "Bu kişiyi nereden tanıyorsunuz?" Yönetici · takım arkadaşı · öğretmen / danışman · müşteri · diğer.
  2. "Çalışma anlatıldığı gibi mi?"
  3. "Payı (ayrı satırda gösterilir) doğru mu?"
  4. "Sonuç (ayrı satırda gösterilir) doğru mu?"

  (2)-(4) için yanıtlar: evet / kısmen / hayır / bilmiyorum. Ardından isteğe bağlı yorum.
- **Puan:**
  - Referans başlığı: evet = 3, kısmen = 1, hayır = 0. "Bilmiyorum" ortalamaya girmez. Güncel yanıtların ortalaması alınır (0.5 yukarı yuvarlama). Yanıt yoksa "—".
  - (3) "evet" → Rol için A desteği; (4) "evet" → Sonuç için A desteği.
  - Eski 1-5 yanıtlar `REFERANS_PUAN_ESLEMESI` ile okunmaya devam eder.
- **Güç işaretleri** (puan değil, satırda görünür): kurumsal e-posta (alan adı kuruluşun web sitesiyle aynı), `.edu.tr`, ilişki türü.
- **Engeller:**
  - gencin kendi e-postası (422),
  - aynı kalemde aynı kişiden ikinci bekleyen istek (409).
- **Durum makinesi:** `referans_gecisi(durum, olay)`: `bekliyor → yanitlandi | yanit_yok | geri_cekildi`. Geçersiz geçiş 409; geçiş bildirimi aynı işlemde yazılır.
- **Eşzamanlılık:** yanıt koşullu güncellemeyle kaydedilir: `UPDATE … WHERE token = :t AND durum = 'bekliyor' RETURNING id`.

---

## 8. Meslek dallarına göre kanıt

| Alan | Link okuyucu | Dosya / görsel | Hesap bağlama | A'ya giden yol |
|---|---|---|---|---|
| Yazılım | GitHub / GitLab API, mağaza, genel + yedek okuyucu | Diyagram, ekran görüntüsü (D) | GitHub, GitLab (OAuth) | Bireysel repo kuralı (B ile 3/3), organizatör sayfası, referans |
| Tasarım | Figma oEmbed, yedek okuyucu + **ekran görüntüsü** (Behance, Dribbble, ArtStation) | Görsel + kaynak araması, portfolyo PDF'i | Behance, Dribbble, kişisel site (profil kodu) | Bağlı portfolyo kuralı, ödül sayfası, müşteri referansı |
| Yazı, içerik, gazetecilik | Medium RSS, JSON-LD `author`, imza (byline) | Yazı PDF'i (D) | Medium, kişisel site (profil kodu) | Bağlı tek yazarlı yazı kuralı, editör referansı |
| Video, medya, müzik, fotoğraf | oEmbed, YouTube Data API | Görsel + C2PA + kaynak araması | YouTube, Vimeo, SoundCloud (profil kodu) | Bağlı kanal, festival / yarışma sayfası, referans |
| Veri, analitik | Kaggle, Drive (CSV), genel okuyucu | Rapor PDF'i | Kaggle (profil kodu), GitHub | Yarışma sıralaması (B), referans |
| Akademik | Crossref, ORCID, `citation_author`, Drive (PDF) | Bildiri / poster PDF'i | ORCID (OAuth) | Yazar listesi + ORCID (B), danışman referansı |
| Mühendislik, mimarlık | Genel okuyucu, Drive | PDF rapor, maket fotoğrafı | — | QR'lı / imzalı belge, danışman referansı |
| Yarışma | Devpost (ekip), organizatör sayfası | Derece belgesi (QR) | GitHub | Organizatör sayfası + kimlik koşulu |
| Sertifika, eğitim | Sertifika okuyucu | Sertifika PDF'i (QR / imza / rozet) | — | Düzenleyenin doğrulama sayfası (rozet e-postası eşleşmesi en güçlü) |
| Staj, iş | LinkedIn (giriş duvarı) | e-Devlet barkodlu belge, staj belgesi | — | GİRVAK barkod doğrulaması, kurumsal e-postalı referans |
| Gönüllülük | Genel okuyucu | Belge, etkinlik fotoğrafı | — | Kuruluş sayfası + kimlik koşulu, kuruluş referansı |
| Pazarlama, sosyal medya | Genel okuyucu, Drive (sunum) | Kampanya raporu, ekran görüntüleri | YouTube, kişisel site (profil kodu) | Müşteri / yönetici referansı |
| Satış, operasyon, İK, finans, hukuk, sağlık | — | İş / staj belgesi | — | **Referans + belge** (bu meslekler için birincil yol) |

---

## 9. Kötüye kullanım ve GİRVAK incelemesi

İşaretler puanı kendiliğinden düşürmez (İ1). Hepsi `inceleme_isareti` tablosuna ve GİRVAK kuyruğuna düşer. GİRVAK bir işareti "sorun yok" diye kapatabilir ya da kalemi "doğrulanamadı" olarak etiketleyebilir; genç bu kararı görür ve itiraz edebilir.

| İşaret | Tespit |
|---|---|
| `ayni_iddia_cok_hesapta` | Aynı normalleştirilmiş URL, dosya özeti ya da benzer görsel (pHash) başka bir hesapta. OAuth katkıcı listesi ikisini de doğruluyorsa kapanır (takım projesi) |
| `ayni_belge_iki_hesapta` | Aynı normalleştirilmiş doğrulama adresi (QR / sertifika) ikinci bir hesapta |
| `gorsel_baskasinda` | Kaynak araması: birebir eş, başka bir portfolyoda, daha eski tarihte |
| `referans_supheli` | IP ya da tarayıcı özeti gencin girişleriyle aynı, birkaç saniyede yanıt, aynı referansın çok sayıda gence yanıt vermesi. IP'nin tuzlu özeti saklanır, 90 gün |
| `belge_tutarsiz` | Bozuk imza; QR sayfasında ad yok ya da farklı |
| `kanit_celisiyor` | Model "çelişiyor" dedi ve alıntı denetimden geçti |
| `itiraz_siniri` | Bir içerik sürümünde 3 itiraz |
| `ad_degisikligi` | Kilitli ad için değişiklik talebi |
| `profil_kodu_elle` | Profil okunamadı, elle doğrulama bekliyor |
| `edevlet_barkodu` | e-Devlet barkodlu belge doğrulama bekliyor (adım 9'da `eposta_barkodu` yazım hatası düzeltildi) |

`alakasiz_kanit` kalem işaretidir; kuyruğa girmez (§ 3).

---

## 10. Ölçüm

### 10.1 Değerlendirme seti

- **Hedef:** `backend/tests/degerlendirme_seti/` altında 120 vaka. § 8'deki 13 alanın her birinden dürüst vakalar; kötü niyetli vakalar (başkasının reposu, şişirilmiş sayı, sahte ad, düzenlenmiş ekran görüntüsü, QR'ı başka sayfaya giden belge, giriş duvarı, bot engeli, kanıtsız ama doğru iddia); en az 10 **bireysel proje** vakası (tek katkıcılı repo, kişisel blog, kişisel portfolyo; hesap bağlı ve bağlı değil).
- **Bireysel vakalarda beklenen:** hesap bağlıysa Kanıt 3 ve Rol 3; bağlı değilse Kanıt 2.
- **Etiketleme:**
  - Önce `degerlendirme_seti/ETIKETLEME_REHBERI.md` yazılır: her başlık ve seviye için örnekli kural.
  - Etiketleri Zühre koyar. Her vakada `etiketleyen` ve `gozden_geciren` alanları bulunur.
  - GİRVAK sonradan vakaların en az %20'sini gözden geçirir; anlaşmazlıklar `ANLASMAZLIKLAR.md`'ye yazılır.
  - Kötü niyetli vakaları Zühre üretir.
  - Etiketlenmemiş vaka karneye girmez. Etiketleri bekleyen ilk karne "taslak etiketle" diye ayrı raporlanır.
- **Çevrimdışı çalışma:** ağ ve model yanıtları kayıtlıdır (kaset deseni). Set her commit'te CI'da çalışır; canlı sürüm ayrı bir betikle çalışır.
- **Ölçütler ve kabul eşikleri:**
  - **Sahte vakada yanlış 3 = 0** (en kritik ölçüt),
  - başlık başına birebir uyum ≥ %80, ±1 uyum ≥ %95,
  - alan bazında "—" oranı,
  - notta yasak kelime ya da hitap hatası = 0.

### 10.2 Adalet

Dürüst vakalarda alan başına ortalama Kanıt ve ulaşılabilir en yüksek puan ölçülür. Her alanda en az bir yolla 3'e ulaşılabilmelidir. Fark büyürse yeni bir yol eklenir; tavanlar düşürülmez. "—" bonusa girmez.

**Uygulama (adım 12):** `degerlendirme/adalet.py` (saf) karnenin "Adalet" bölümünü üretir. Yalnızca dürüst, etiketli vakalar; alan başına ortalama Kanıt ("—" ortalamaya girmez, ayrı oran), sistemin en yüksek Kanıt'ı, etiketlerin ulaşılabilir saydığı tavan ve Kanıt 3'e ulaşan vakalar ("3 yolu"). Sorun işaretleri: alanda 3'e giden yol yok; ortalama genel ortalamadan `FARK_ESIGI` (0,5 puan; plan sayı vermiyordu, varsayım) fazla geride; üçten az dürüst vaka (ölçüm güvenilir değil). Bunlar kabul kapısı değil, iştir: işaretli alana yeni yol (vaka ya da kanıt türü) eklenir, tavan düşürülmez; bu yüzden `esikleri_geciyor_mu`'ya girmez.

### 10.3 Gözlem

Her değerlendirme için şunlar kaydedilir:
- girdi özeti,
- okuyucu,
- erişim durumu,
- seviye,
- süre,
- token kullanımı,
- dış servis çağrıları ve sonuçları.

GİRVAK panelinde iki görünüm yer alır: platform bazında erişim dağılımı ve servis durumu (§ 14.4).

### 10.4 Link çürümesi

- **Sıklık:** haftalık yoklama (Canlılık taraması).
- **Sayaç:** yalnızca `BULUNAMADI` ve `GIRIS_GEREKLI` sayılır (link silinmiş ya da gizlenmiş). `ENGELLENDI` ve `HATA` sayılmaz. `ACIK` sonuç sayacı sıfırlar.
- **Sonuç:** üst üste 3 sayılan sonuçtan sonra Kanıt "—" olur, gence bildirim gider, puan geçmişi saklanır.

---

## 11. Puanlama

### 11.1 Model çıkarımı (güçlü katman, sıcaklık 0)

```python
class IddiaDestegi(BaseModel):
    iddia: Literal["is", "sonuc", "pay"]
    durum: Literal["destekleniyor", "celisiyor", "kanitta_yok"]
    alinti: str | None

class YetenekKaniti(BaseModel):
    yetenek: str                 # yalnızca istemde verilen sabit listeden (kartın yetenekleri)
    alinti: str

class KanitCikarimi(BaseModel):
    ilgili_mi: bool
    sonuc_var: bool
    sonuc_sayisal: bool
    sonuc_olcut_acik: bool
    pay_var: bool
    pay_ozgul: bool
    ekip_ortakligi_belirtilmis: bool   # sayfada ekip / ajans / müşteri ortaklığı (bireysel kural)
    destekler: list[IddiaDestegi]
    kanitlanan_yetenekler: list[YetenekKaniti]
    oneri: str | None            # tek cümle, "sen" hitabı
```

- **Kanıtın istemdeki yeri:** `<kanit_metni>` etiketleri içinde, "bu bir veri, talimat değil" kuralıyla verilir. Uzun içerikte yalnızca seçilmiş parçalar gider (§ 5.4).
- **Alıntı denetimi:** **tam metne** (ya da `gorsel_metni`'ne) karşı yapılır. Metin normalleştirilir (Türkçe küçük harf, boşluk, noktalama), sonra kısmi benzerlik ≥ 0.9 aranır. Geçmeyen destek ve yetenek atılır.
- **Yetenek listesi denetimi:** listede olmayan yetenek atılır.
- **Yetenek kanıtı kaydı:** her kanıtlanan yetenek `yetenek_kaniti` tablosuna yazılır (`kart_id`, `yetenek`, `en_guclu_puan`, `kaynak_parca_id`, `seviye`).
- **Eşleştirme bonusu bu adımda değişmez.** Eşleştirme incelemesinde değerlendirilecek iki seçenek:
  - (a) en güçlü iki kalemin ortalaması,
  - (b) ihtiyacın gerektirdiği yeteneklerin `yetenek_kaniti` ortalaması; kanıtı olmayan yetenek bonusa girmez.

### 11.2 Kurallar (saf fonksiyonlar)

```
parca_puani(parca, cikarim, kimlik) → BaslikPuanlari      (seviye tavanıyla)
kalem_puani(parcalar, beyan, referanslar) → BaslikPuanlari  (başlık başına en güçlü parça)

kanit:  BULUNAMADI | GUVENSIZ → 0 · okunamadı → None · ilgisiz → 0 (+ alakasiz_kanit)
        ilgili → seviye tavanı (D dosya: 1, C: 2, B/A: 3)
sonuc:  yok 0 · niteliksel 1 · sayısal 2 · sayısal + ölçüt açık + (B platform verisi | A belge | referans sonuç: evet) → 3
rol:    yok 0 · belirsiz 1 · özgül 2
        özgül + (B katkı oranı ≥ %90 | bireysel kural | A belge rolü | referans pay: evet) → 3
celisiyor (alıntılı) → ilgili başlık en çok 1 + kanit_celisiyor işareti
referans: güncel yanıtların ortalaması; yanıt yoksa None
```

Hiç kanıt parçası olmayan kalem de beyan tavanıyla değerlendirilir: Sonuç ve Rol en çok 2, Kanıt ve Referans "—" (Karar 10).

### 11.3 Not

- **Yapı:** başlık başına bir şablon cümlesi; cümleyi puan, seviye ve erişim durumu belirler. Ardından modelin `oneri` cümlesi gelir.
- **Hitap ve terimler:** şablonlar "sen" diye yazılır ve rehber sözlüğünü kullanır. `oneri` cümlesi yasak kelime ve hitap denetiminden geçemezse atılır.
- **Ortak dil kuralı:** `kullanici_dili(hitap="sen" | "siz")` bütün istemlerde kullanılır.

### 11.4 İtiraz

- **Önbellek:** `girdi_ozeti = hash(iddia + parça özetleri + itiraz notu + kural sürümü)`. Aynı özet varsa önceki sonuç döner.
- **Değişiklik zorunlu:** itiraz bir not ya da yeni bir parça ister.
- **Sınır:** içerik sürümü başına 3 itiraz; sonrası `itiraz_siniri` işaretiyle kuyruğa gider.

---

## 12. Bulgular: kök neden ve çözüm

| # | Bulgu | Çözüm | Bölüm | Adım |
|---|---|---|---|---|
| 1 | Sayfa içeriği okunmuyor | Okuyucu zinciri + alıntılı çıkarım | § 5, § 11 | 5 |
| 2 | Sahiplik kontrolü yok | Seviyeler; sahiplik yalnızca OAuth / profil kodu / düzenleyen | § 2, § 6 | 8 |
| 3 | Bot engeli → 0 | Başlıklar → resmî yol → yedek okuyucu → `ENGELLENDI` "—" + seçenekler | § 3, § 5 | 5, 10 |
| 4 | Büyük sayfada başlık kaçıyor | oEmbed, akışlı 2 MB okuma | § 5.3 | 5 |
| 5 | Giriş sayfası "açılıyor" | `GIRIS_GEREKLI` | § 5.2 | 5 |
| 6 | DNS hatası "güvensiz" | `AdresBulunamadi` | § 5.2 | 5 |
| 7 | HTML karakter kodları | HTML ayrıştırıcısı çözer (bulgu 50 ile) | § 5.3 | 2 |
| 8 | JavaScript siteleri boş | Yedek okuyucu + ekran görüntüsü | § 5.5 | 10 |
| 9 | İstem enjeksiyonu | Veri etiketi + kural puanı + alıntı denetimi | § 11 | 4 |
| 10 | Beyan tam puan | Seviye tavanları | § 2 | 4 |
| 11 | Hitap "siz" | Şablon not, `kullanici_dili(hitap)` | § 11.3 | 4 |
| 12 | Not ile sayılar çelişiyor | Şablon not | § 11.3 | 4 |
| 13 | Tek başlığa "güven göstergesi" | Şablon sözlüğü | § 11.3 | 4 |
| 14 | "Ajan'sın" | İstem yeniden yazılır | § 11.1 | 4 |
| 15 | İtiraz sınırsız | Önbellek, değişiklik zorunlu, sınır | § 11.4 | 4 |
| 16 | Referans eklemek yeniden puanlıyor | Parça ekleme ve değerlendirme ayrı | § 14 | 3 |
| 17 | Linksiz kalemde sahte 0 | NULL başlıklar, dolu başlıklardan bonus | § 13 | 3 |
| 18 | Referans pay ve sonucu görmüyor | Form alanları ayrı ayrı gösterir | § 7 | 7 |
| 19 | "Referans yok" ile "olumsuz" aynı | NULL ile 0 ayrımı | § 1 İ4 | 3 |
| 20 | Ölçek ve tek soru | 4 soruluk form | § 7 | 7 |
| 21 | Kendi kendine referans | Doğrudan e-posta, engeller, işaret | § 7, § 9 | 7, 11 |
| 22 | Yanlış e-posta | `geri_cekildi` | § 7 | 7 |
| 23 | Zaman aşımında bildirim yok | Geçiş bildirimi + tarama | § 7 | 7 |
| 24 | Aynı anda iki yanıt | Koşullu güncelleme | § 7 | 7 |
| 25 | Link iki yoldan değişiyor | Tek kanıt servisi | § 14 | 3 |
| 26 | Eşleşmeler tazelenmiyor | `gosterge_degisti` kancası | § 14 | 3 |
| 27 | Zayıf kanıt bonusu düşürüyor | Dolu başlık + en güçlü parça (3); kart formülü Eşleştirme incelemesinde (§ 11.1) | § 11.1 | 3, 13 |
| 28 | Rozet tazelenmiyor | Yanıt `kart_kanit_bekleyen` taşır | § 14 | 3 |
| 29 | "Kanıt türü" kullanılmıyor | Platformdan otomatik | § 13 | 3 |
| 30 | "Yeniden iste" 409 | Backend bayrağı | § 1 İ7 | 3 |
| 31 | GİRVAK token görüyor | Token hiçbir yanıtta yok | § 7 | 7 |
| 32 | Uç dosyası şişkin | Katmanlama | § 14 | 2 |
| 33 | Zaman aşımı iki kez | Tek fonksiyon | § 14 | 2 |
| 34 | Referans kuralları yanlış modülde | Taşınır | § 14 | 2 |
| 35 | Test açıkları | Birim + uç + set + canlı | § 10, § 16 | Her adım |
| 36 | Beyan edilen kullanıcı adı sahiplik sayılıyordu | Yalnızca OAuth / profil kodu | § 6 | 8 |
| 37 | Hesap e-postası doğrulanmıyor | Kayıtta doğrulama | § 6.3 | 6 |
| 38 | Kanıtın bağımsızlığı ayrılmıyordu | Seviye modeli | § 2 | 4 |
| 39 | Ölçüm yok | Etiketli set | § 10 | 1 |
| 40 | Platformlar arası adaletsizlik | Her alana yol, adalet ölçümü | § 8, § 10.2 | 12 |
| 41 | Birebir alıntı katı | Normalleştirme + kısmi benzerlik | § 11.1 | 4 |
| 42 | Link çürümesi | Haftalık yoklama, doğru sayaç | § 10.4 | 12 |
| 43 | Aynı iddia birden çok hesapta | Özet ve pHash ile işaret | § 9 | 11 |
| 44 | Okunamayan link için yol yok | Seçenek kutusu | § 3 | 9 |
| 45 | Uzun içerik kesiliyordu | Bölme + embedding + iddia başına seçim; alıntı tam metne | § 5.4 | 5 |
| 46 | Görsel sitelerde metin yok | Ekran görüntüsü yolu, seviye C | § 5.5 | 10 |
| 47 | Drive / Docs linkleri okunmuyor | Dışa aktarma adresleri, paylaşım cümlesi | § 5.6 | 5 |
| 48 | Ad değiştirilerek sahiplik taklidi | Ad kilidi, üç koşul, e-posta eşleşmesi öncelikli, belge tekilliği | § 6.3, § 4.2 | 6, 9 |
| 49 | Dış servis hatası değerlendirmeyi düşürebilir | Arayüz + bayrak + zarif düşüş + sağlık | § 14.4 | Her servisin adımı |
| 50 | **Başlık ayrıştırmasında ReDoS (kritik):** `_meta_icerigi` regex'i (`(.*?)` + `re.S`) `>` içermeyen tırnaklı bölgede felaket geri izlemeye düşüyor (24 KB 6 sn, 60 KB ~40 sn, YouTube'un 300 KB'ı saatler); Python regex'i GIL'i bırakmadığı için bütün sunucu donuyor | Standart kütüphanenin HTML ayrıştırıcısı, `</head>`'de durur, doğrusal | § 5.3 | 2 (acil, ilk commit) |
| 51 | Wikipedia ve benzerleri tarayıcı kimliği olmayan isteği 403 ile reddediyor | Gerçekçi başlıklar | § 5.3 | 5 |
| 52 | Bozuk öznitelikten özete ham HTML sızıyor (Instagram) | HTML ayrıştırıcısı (bulgu 50 ile aynı commit'te çözüldü) | § 5.3 | 2 |
| 53 | Dribbble 202 ve boş gövde döndürüyor (bot sorgulaması); bugün "açılıyor" sayılıyor | `ICERIK_YOK` → yedek okuyucu | § 5.2, § 5.5 | 5, 10 |

---

## 13. Veri modeli

| Tablo | Değişiklik |
|---|---|
| `kanit_parcasi` (yeni) | `somut_cikti_id`, `tur` (link / dosya / gorsel / referans_disi), `url`, `normal_url`, `dosya_anahtari`, `dosya_ozeti`, `phash`, `platform`, `erisim`, `seviye`, `sahiplik_kaynagi` (oauth / profil_kodu / ad / eposta / yok), `belge` JSONB (yazarlar, çapalar, alıntılar, platform verisi), `tam_metin` (maskelenmiş), `gorsel_metni`, `okuma_tarihi`, `curume_sayaci`, `gorunur_firmaya`, `isaretler` (ör. `alakasiz_kanit`) |
| `kanit_metin_parcasi` (yeni) | `kanit_parcasi_id`, `sira`, `metin`, `embedding vector(1024)` |
| `somut_cikti` | `kanit_linki` → ilk `kanit_parcasi`na taşınır, sonra kalkar; `kanit_turu` kalkar |
| `guven_skoru` | Dört başlık nullable; `girdi_ozeti`, `kural_surumu`, `kanit_ozeti` JSONB (başlık başına parça ve seviye), `degerlendirme_tarihi`, `itiraz_sayisi` |
| `yetenek_kaniti` (yeni) | `kart_id`, `yetenek`, `en_guclu_puan`, `kaynak_parca_id`, `seviye`; (`kart_id`, `yetenek`) tekil |
| `referans_istegi` | `iliski`, `iddia_dogru`, `pay_dogru`, `sonuc_dogru`, `gonderim_tarihi`, `hatirlatma_tarihi`, `kurumsal_eposta`, `yanit_isareti` JSONB; `durum` += `geri_cekildi`; `puan` eski satırlar için korunur |
| `bagli_hesap` (yeni) | `kullanici_id`, `saglayici`, `kullanici_adi`, `dis_kimlik`, `yontem` (oauth / profil_kodu / elle), `baglanma_tarihi`; (`saglayici`, `dis_kimlik`) tekil |
| `profil_kodu` (yeni) | `kullanici_id`, `platform`, `kod`, `profil_adresi`, `son_gecerlilik`; (`kullanici_id`, `platform`) tekil |
| `inceleme_isareti` (yeni) | `tur`, `somut_cikti_id`, `kullanici_id`, `ayrinti` JSONB, `durum` (acik / kapandi / dogrulanamadi), `girvak_notu`, `kapanma_tarihi` |
| `kanit_onbellek` (yeni) | `anahtar_ozeti`, `belge` JSONB, `tarih` |
| `hesap` | `eposta_dogrulandi_tarihi` |
| `eposta_dogrulama` (yeni) | `hesap_id`, `token_ozeti`, `son_gecerlilik` |

**Migration:**
- Eski satırlardaki "referanssız 0" → NULL.
- Linksiz satırların sahte 0'ları → NULL.
- `kanit_linki` → `kanit_parcasi` (`seviye = NULL`: ilk değerlendirmede hesaplanır).
- Geri alma (downgrade) tanımlıdır; veri silmez.

---

## 14. Mimari

### 14.1 Katmanlar (CLAUDE.md: uçlar ince, orkestrasyon `servisler/`'de)

| Katman | Dosya | Sorumluluk |
|---|---|---|
| Saf kurallar | `agents/dogrulama/kurallar.py` | Seviye tavanları, `parca_puani`, `kalem_puani`, bireysel kurallar, referans çevrimi, zaman aşımı |
| Saf kurallar | `agents/dogrulama/alinti.py` | Normalleştirme, kısmi benzerlik |
| Saf kurallar | `agents/dogrulama/not_sablonu.py` | Şablon not |
| Saf kurallar | `agents/dogrulama/kimlik.py` | Ad eşleşmesi, seviye A koşulu |
| Durum makinesi | `agents/dogrulama/referans_durumu.py` | `referans_gecisi` |
| Model çıkarımı | `agents/dogrulama/cikarim.py` | İstem, şema, `cikar(...)` |
| Okuma | `core/kanit_okuma/` | § 5.1 |
| Dış servis arayüzleri | `core/dis_servisler/` | § 14.4 |
| Orkestrasyon | `servisler/dogrulama/kanit.py` | Parça ekle / sil / değerlendir; `gosterge_degisti` |
| Orkestrasyon | `servisler/dogrulama/referans.py` | İste, geri çek, yanıtla, zaman aşımı, hatırlatma |
| Orkestrasyon | `servisler/dogrulama/itiraz.py` | İtiraz |
| Orkestrasyon | `servisler/hesap_baglama.py` | OAuth, profil kodu |
| Orkestrasyon | `servisler/inceleme.py` | İşaret aç / kapat |
| Orkestrasyon | `servisler/kimlik_dogrulama.py` | E-posta doğrulama, ad değişikliği |
| Uçlar | `api/dogrulama.py`, `api/hesap_baglama.py`, `api/girvak_inceleme.py`, `api/eposta_dogrulama.py` | Şema, sahiplik, hata çevirisi |

`agents/dogrulama.py` tek dosyadan pakete döner. Dışarıya açılan adlar `__init__.py`'de tutulur, böylece mevcut içe aktarmalar kırılmaz.

### 14.2 SOLID karşılıkları

| İlke | Uygulama |
|---|---|
| Tek sorumluluk | Okuyucu başına bir sınıf; kurallar saf modüllerde; servis yalnızca orkestrasyon; uç yalnızca HTTP |
| Açık / kapalı | Yeni platform = yeni `Okuyucu` + kayıt satırı. Yeni profil kodu platformu = yeni `ProfilKoduPlatformu`. Yeni OAuth = yeni `OAuthSaglayici`. Yeni çapa = yeni `CapaDogrulayici`. Mevcut kod değişmez |
| Liskov | Her okuyucu aynı sözleşmeyi döndürür (`KanitBelgesi`). Kayıttaki bütün okuyucular **ortak sözleşme testinden** geçer |
| Arayüz ayrımı | Küçük arayüzler: `EpostaGonderici.gonder`, `Depo.koy / imzali_adres / sil`, `VirusTarayici.tara`, `ParcaSecici.sec`, `GorselArayici.ara`, `YedekOkuyucu.ac`, `Gomucu.gom` |
| Bağımlılığın tersine çevrilmesi | Servisler arayüzlere bağlıdır. Somut sınıflar tek bir **kurulum noktasında** (`core/dis_servisler/kurulum.py`) bayraklara göre seçilir. Testler sahte sınıf verir |

### 14.3 Desenler

| Desen | Nerede | Neden |
|---|---|---|
| Strategy | Okuyucular, OAuth sağlayıcıları, profil kodu platformları, çapa doğrulayıcıları | Platforma özel davranış, ortak yüz |
| Chain of Responsibility | Okuyucu zinciri (platform → genel → yedek → Jina) | İlk başaran okuyucu kazanır; düşüş sırası tek yerde |
| Adapter | Resend, R2, ClamAV, Playwright, Jina, Cloud Vision, YouTube Data API, Voyage | Dış API'ler bizim arayüzümüze uyar |
| Null Object | Bayrağı kapalı servis (`KapaliGorselArayici` → `None`) | Zarif düşüş; `if servis_var` dalları kod içine dağılmaz |
| Decorator | `zaman_asimli`, `gozlemli` sarmalayıcıları | Zaman aşımı, ölçüm ve log her servise aynı biçimde |
| State Machine | `referans_gecisi` | Eşleşme ve takip durum makineleriyle aynı desen |
| Kural tablosu | Seviye tavanları, puan kuralları, not şablonu | Kural veri gibi okunur, tabloyla test edilir |
| Value Object | `KanitBelgesi`, `BaslikPuanlari`, `MetinParcasi` (frozen dataclass) | Değişmez, karşılaştırılabilir |
| Pipeline | Dosya yükleme hattı (tür → boyut → virüs → temizlik → analiz) | Her adım tek iş yapar, sırası tek yerde |

### 14.4 Dış servisler: arayüz, bayrak, zarif düşüş

- **Arayüz ve bayrak:** her servis bir arayüzün arkasındadır ve bir özellik bayrağı (`.env`) vardır.
- **Zarif düşüş:** servis yoksa ya da hata verirse ilgili sinyal "—" olur, akış devam eder. Hata gözlem kaydına yazılır.
- **Zaman aşımı:** her çağrıda zaman aşımı vardır (`zaman_asimli` decorator'ı).
- **Sağlık kontrolü:** `GET /saglik/servisler` yalnızca GİRVAK içindir; durum gözlem panelinde görünür. Sağlık kaydı süreç içinde tutulur, ayrıca `servis_gunlugu` tablosuna günlük sayaç olarak yazılır (adım 12): panel süreç yeniden başlasa da geçmişi gösterir.

| Servis | Varsayılan | Not |
|---|---|---|
| E-posta: Resend | açık | SPF ve DKIM ayarlı |
| Depo: Cloudflare R2 | açık | Özel kova |
| Playwright yedek okuyucu (Railway'de ayrı servis) | açık | Kendi servisimiz |
| ClamAV (ayrı konteyner) | açık | Yerel |
| pyHanko, c2pa-python, zxing-cpp | açık | Yerel kütüphaneler |
| YouTube Data API | açık | Uygulama API anahtarı |
| Jina Reader | kapalı | Yalnızca Playwright başarısız olursa ve bayrak açıksa |
| Cloud Vision | kapalı | Açıkken yalnızca tasarım / fotoğraf alanındaki görsellerde; aylık tavan ortam değişkeninden |

Yurt dışına veri aktaran her servis (Resend, R2, Jina, Cloud Vision) KVKK aydınlatma metninde ayrı ayrı listelenir.

---

## 15. Uygulama sırası

Sıra bağımlılığa ve riske göredir. Her adımın üç ortak kuralı var:
- **Ön koşul:** önceki adım onaylanmış olmalı.
- **Bitiş ölçütü:** backend testleri + ruff + frontend eslint / tsc / testleri yeşil; değerlendirme seti karnesi gerilemiyor (puan değiştiren adımlarda iyileşiyor).
- **Commit:** bulgu ya da iş birimi başına ayrı commit; ilgili belge aynı commit'te güncellenir; kısa rapor verilir ve onay beklenir.

Sürüm 2 sırasından iki bilinçli sapma var, ikisinin de nedeni bağımlılık:
- (a) **Tek kanıt servisi ve `gosterge_degisti` adım 3'e alındı.** Sürüm 2'de adım 9'du. Sonraki her adım (okuyucular, dosyalar, referans) kanıt parçasını bu servisten ekliyor.
- (b) **E-posta altyapısı, kayıt doğrulaması ve inceleme kuyruğunun çekirdeği referanstan önce ayrı bir adım (6) oldu.** Referans e-postası, ad kilidi, profil kodunun elle doğrulanması ve dosya işaretleri bunlara dayanıyor.

### Adım 1: Ölçüm altyapısı ve bugünkü sistemin karnesi

> **Durum: tamamlandı** (`0ed787f`…`9dbfaa9`). 45 taslak vaka; etiketler Zühre'de. İlk karne: `backend/tests/degerlendirme_seti/karneler/2026-10-01-mevcut_sistem-taslak.md`. Projede CI olmadığı için çevrimdışı karne pytest'in parçası (`test_degerlendirme_seti`).

- **Neden önce:** her sonraki adımın gerilemediğini ve iyileştiğini kanıtlamak için (İ8).
- **İş birimleri:**
  1. `degerlendirme_seti/ETIKETLEME_REHBERI.md`: başlıklar, seviyeler, bireysel kurallar, örnekler.
  2. Vaka şeması: `Vaka` (pydantic) ve vaka dosyaları (YAML). Yükleyici ve şema doğrulama testi.
  3. Kaset altyapısı:
     - ağ için kayıtlı yanıt dönen bir httpx transport'u,
     - model için girdi özetine göre kayıtlı çıktı dönen sahte model,
     - kayıt kipi (ortam değişkeniyle).
  4. `Degerlendirici` arayüzü ve `MevcutSistemDegerlendirici` adaptörü (bugünkü rubrik). Ölçüt hesapları saf fonksiyonlardır; Markdown karne raporu üretilir.
  5. Taslak vakalar: 13 alan, kötü niyetli vakalar, en az 10 bireysel vaka. Önerilen etiketler `etiketleyen: null` olarak gelir; Zühre etiketler. Kayıtlı sayfalar ve API yanıtları da vakalarla birlikte gelir.
  6. `scripts/karne.py` + CI'da çevrimdışı çalışma. İlk karne "taslak etiket" diye ayrı raporlanır.
- **Desenler:** Adapter (değerlendirici), Strategy (ileride yeni sistem aynı arayüze bağlanır).
- **Belge:** `degerlendirme_seti/README.md`.

### Adım 2: Katmanlama (davranış değişmez)

> **Durum: tamamlandı** (`058241b`, `41c7b6d`, `b13bbca`). İlk commit, Adım 1'de bulunan ReDoS'un (bulgu 50) acil düzeltmesi; katmanlama commit'lerinde karne birebir aynı. Uç dosyasında şema eşlemesi (`_durum_yaniti`) sunum işi olarak kaldı. Testlerde yalnızca içe aktarma yolları ve iki sahte nesnenin eksik alanları değişti.

- **Bulgular:** 32, 33, 34.
- **İş birimleri:**
  1. `agents/dogrulama.py` → `agents/dogrulama/` paketi (dışarıya açılan adlar korunur).
  2. Referans geçerlilik kuralları `kart_duzenleme`'den taşınır; `getattr` kalkar.
  3. `referans_gecisi` durum makinesi (mevcut üç durum) ve tek `zaman_asimlarini_isle`.
  4. Uçtaki iş mantığı `servisler/dogrulama/`'ya taşınır; uçlar incelir.
- **Bitiş:** mevcut testler değişmeden yeşil; karne birebir aynı.

### Adım 3: Veri modeli, "—" ve tek kanıt servisi

> **Durum: tamamlandı** (`906fa4c` genişlet, `2745ab7` "—", `2c63259` tek kanıt kapısı, `e180e1a` daralt, kart arayüz düzeltmesi). Uygulamada netleşen kararlar: (1) link iddia düzenleme formundan çıktı, kanıt bölümünün tek kapısından eklenir ve kaldırılır; (2) kanıt değişikliği göstergeyi yeniden değerlendirir ama referans yanıtlarını geçmişe atmaz, karar 8'deki "ya da linki" kalktı (§ 2: kanıt eklemek puanı düşürmez); (3) "değerlendirildi mi" `degerlendirme_tarihi`'ne bakar, yalnızca referansla açılan gösterge sayılmaz; (4) kalem içinde "en güçlü parça" seçimi adım 4-5'te (bugün değerlendirme birincil linki okur). Gerçek sunucuda uçtan uca denendi.

- **Bulgular:** 16, 17, 19, 25, 26, 27 (kısmen), 28, 29, 30.
- **İş birimleri:**
  1. Alan türleri: `KaynakSeviyesi`, `ErisimDurumu`, `ParcaTuru` (değer nesneleri).
  2. Migration: `kanit_parcasi`, `kanit_metin_parcasi`, `yetenek_kaniti`, nullable başlıklar ve yeni sütunlar, veri taşıma. Diğer tablolar ilgili adımlarında eklenir.
  3. `servisler/dogrulama/kanit.py`: `parca_ekle / sil`, `degerlendir`. Kart düzenleme formu da link değişikliğini bu servisten yapar (sıfırlama ve `icerik_tarihi` burada).
  4. `gosterge_degisti` kancası → kart hazırlama (arka plan; `conftest` sahtesi).
  5. Yeni uçlar ve şemalar (§ 14.1): `kanit-ekle` kalkar; yanıtlarda `kart_kanit_bekleyen` ve `yeniden_istenebilir` bulunur.
  6. Eşleştirme: bonus yalnızca dolu başlıklardan; kalem içinde en güçlü parça; `dogrulama_ozeti` NULL'u "değerlendirilmedi" diye anlatır.
  7. Frontend: `GuvenGostergesi` "—", kanıt bölümü parça listesi, "Kanıt türü" alanı kalkar.
- **Belgeler:** data-schema, api-contracts, matching-algorithm § 4.

### Adım 4: Puan çekirdeği

> **Durum: tamamlandı.** `cekirdek.py` tek giriş noktası (model çağrısı enjekte; uygulama ve karne aynı çekirdeği kullanır). Alıntı denetimi yeni bağımlılık yerine `difflib` ile. Notta Referans cümlesi yok (referans sonradan yanıt verince eskirdi). İtiraz sınırı önbellek kontrolünden sonra (aynı not hak harcamaz). Referansın yapılandırılmış yanıtı çekirdekte destekli, uygulama adım 7'de bağlar. Diğer ajanların istemlerine `kullanici_dili(hitap)` kendi incelemelerinde geçirilecek. Karne: sahte vakada yanlış 3 4 → 0, notta dil ihlali 18 → 0, Sonuç birebir %44 → %82; kalan Kanıt farkları okuyucu (5, 10), hesap bağlama (8) ve dosya (9) adımlarına bağlı.

- **Bulgular:** 9–15, 38, 41; ilgisiz → 0.
- **İş birimleri:**
  1. `kurallar.py`: seviye tavanları, `parca_puani`, `kalem_puani`, bireysel kurallar, referans çevrimi (eski + yeni). Tablo testleri.
  2. `alinti.py` (bağımlılık `rapidfuzz`) ve `kimlik.py`.
  3. `cikarim.py`: `KanitCikarimi`, `kanitlanan_yetenekler`, istem (veri etiketi, "Ajan'sın" yok), `kullanici_dili(hitap)`.
  4. `not_sablonu.py`: başlık başına şablon ve `oneri` denetimi.
  5. `yetenek_kaniti` yazımı.
  6. İtiraz: `girdi_ozeti` önbelleği, değişiklik zorunlu, sınır (işaret tablosu adım 6'da gelir; o zamana kadar 429).
  7. Geçiş: bugünkü link okuması `KanitBelgesi`'ne uyarlanır (adaptör; seviye C ya da erişim durumu), böylece sistem adım 5'ten önce de çalışır.
- **Bitiş:** karnede sahte vakada yanlış 3 düşer; hitap ve yasak kelime sıfır.
- **Belge:** agent-specs § 4 (kural ve şablon).

### Adım 5: Link okuma

- **Bulgular:** 1, 3 (başlıklar ve resmî yol), 4, 5, 6, 7, 45, 47.
- **İş birimleri:**
  1. `istek.py` (başlıklar, akışlı 2 MB, `unescape`) + `AdresBulunamadi`.
  2. `erisim.py`: giriş duvarı, bot engeli, içerik yok (saf, kalıp tablosu).
  3. `Okuyucu` arayüzü, kayıt, zincir, ortak sözleşme testi, önbellek.
  4. Okuyucular, her biri ayrı commit: `html_genel` (trafilatura), `github`, `gitlab`, `oembed`, `youtube`, `medium`, `google`, `akademik`, `sertifika`, `magaza`, `devpost`.
  5. `parca_secimi.py`: bölme, `Gomucu` (Voyage), `ParcaSecici` (pgvector + bellek içi), iddia başına 4 parça + ilk parça.
  6. Adım 4'teki geçiş adaptörü kalkar.
- **Belge:** agent-specs § 4.1 (karar 13 değişir).

> **Durum: tamamlandı (kapsam notlarıyla).** `app/core/kanit_okuma/`: `istek.py` (tarayıcı başlıkları, 2 MB sınır, `guvenli_get` üzerinden), `erisim.py` (saf tablo), `html_ozeti.py`, `okuyucu.py` (Strategy arayüzü) ve zincir `kaniti_oku` (Chain of Responsibility: platform okuyucusu `None` dönerse genel okuyucu). Okuyucular: `github` (API: repo, katkıcılar, README; isteğe bağlı `GITHUB_TOKEN`), `oembed` (YouTube, Vimeo, SoundCloud, Spotify, Figma), `medium` (RSS), `google` (Drive/Docs/Sheets/Slides dışa aktarma), `genel`. `parca_secimi.py`: 8000 karakterden uzun metinde ilk parça + iddia yüzü başına 4 parça (bellek içi kosinüs); embedding hatasında metnin başı. Adım 4 adaptörü (`link_kontrolu.py`) kalktı; karne uygulamanın yolunu (`okuma.kanit_oku`) kullanıyor, embedding de kasette.
> **Plandan sapmalar (bilinçli):** trafilatura yerine standart `HTMLParser` (yeni bağımlılık yok, doğrusal; ReDoS dersi). Sayfa metninin meta ile birlikte sayılması: JS ile çizilen ama açıklaması olan sayfa (Kaggle) "açık". Model istemine iddia sahibinin adı eklendi ve "ad geçmiyor" çelişki sayılmıyor (zengin metinle yanlış çelişki çıkıyordu).
> **Ertelenenler:** `gitlab`, `akademik` (DOI/Crossref), `sertifika`, `magaza`, `devpost` okuyucuları ve okuma önbelleği; pgvector'lu parça seçimi (bellek içi yeterli, kalıcı parça gerekince). Zincire yeni okuyucu eklemek tek sınıf + `PLATFORM_OKUYUCULARI`'na bir satır.
> **Dış bağımlılık:** Voyage hesabında ödeme yöntemi yok (3 istek/dk); parça seçimi bu yüzden çoğunlukla metnin başına düşüyor. Ödeme yöntemi eklenince karne `--ag tamamla --model tamamla` ile yeniden alınmalı.
> **Karne (`karneler/2026-10-01-mevcut_sistem-taslak-adim5.md`):** Kanıt birebir %56 → %62 (±1 %76), Rol %76 (±1 %100), Sonuç %82, Referans %100; sahte vakada yanlış 3: 0, dil ihlali: 0. Kalan Kanıt farkları: bot engelli/JS siteler (Behance, Dribbble, GrabCAD) → adım 10; bağlı hesap → 8; PDF → 9.

### Adım 6: Kimlik, e-posta ve inceleme kuyruğu çekirdeği

> **Durum: tamamlandı** (`88dd3fc` dış servisler, `106afd7` e-posta doğrulaması, `fc784ba` inceleme kuyruğu, `15305de` ad kilidi, `92ded83` itiraz sınırı). Uygulamada netleşen kararlar (Zühre, 2 Eki): (1) doğrulanmamış hesap her şeyi kullanır, panelde engellemeyen bant ve "yeniden gönder" var; demo ve GİRVAK hesapları doğrulanmış açılır; (2) varsayılan `EPOSTA_SAGLAYICI=log` (bağlantı log'da), Resend anahtarı ve doğrulanmış alan adı gelince `.env`'den `resend`; anahtar eksikse açılış log kipine düşer; (3) hak dolduktan sonraki itiraz kendiliğinden kuyruğa gider (202, `inceleme_bekliyor`). Ek kararlar: doğrulama bağlantısı 24 saat, yenisi eskisini geçersiz kılar, ikinci açılış yan etkisiz; kapanmış işarete farklı karar 409 (kararın etkisi geri alınmaz); `inceleme_isareti` CHECK'i § 9'daki on türün hepsini baştan içerir; ad değişikliğinde yalnızca boşluk/harf büyüklüğü farkı değişiklik sayılmaz. Ad değişikliği onayı, adla sahipliği kurulmuş parçaların kalemlerini "değerlendirilmedi"ye çevirir ve kartı arka planda hazırlar (bugün böyle parça yok; seviye A üreten okuyucular adım 9'da `kimlik.ada_dayali_seviye`'yi kullanacak). Karne değişmedi (puan kuralına dokunulmadı).
> **Ertelenen / borç:** "Doğrulanamadı" kararı bugün yalnızca bildirimle görünüyor; kalemin üzerinde etiket olarak gösterilmesi adım 11'de (kalem işaretleriyle birlikte). `/saglik/servisler` sonuçları süreç içi bellekte; kalıcı gözlem adım 12. `girvak/page.tsx` 400 satır: yeni bölümler ayrı bileşen olarak eklendi, sayfanın kendisinin bölünmesi ayrı bir refactor. Referans yanıt linkinin gence dönmesi adım 7'de kalkıyor.

- **Bulgular:** 37, 48 (ad kilidi).
- **İş birimleri:**
  1. `core/dis_servisler/`: `EpostaGonderici` (Resend + log + kapalı), `kurulum.py`, `zaman_asimli` / `gozlemli` decorator'ları, servis sağlığı.
  2. Kayıt e-posta doğrulaması (`eposta_dogrulama`, uçlar, frontend sayfası).
  3. Ad kilidi ve değişiklik talebi.
  4. `inceleme_isareti` + `servisler/inceleme.py` + GİRVAK kuyruk uçları ve sayfası.
  5. Adım 4'teki geçici 429 itiraz sınırı → `itiraz_siniri` işareti.
- **Belgeler:** faz-b kimlik notu, api-contracts.

### Adım 7: Referans

> **Durum: tamamlandı** (tek commit: API sözleşmesi, form ve satır birlikte değiştiği için bölünmedi). Migration `e4a9c7b2d5f1`: ilişki ve üç soru sütunları (CHECK'li), `gonderim_tarihi`, `hatirlatma_tarihi`, `yanit_isareti`, durum CHECK'i `geri_cekildi` ile. E-posta referansa doğrudan gider (`servisler/dogrulama/referans_epostasi.py`, yanıttan sonra arka planda, `EpostaGonderici` üzerinden); token ve yanıt linki hiçbir API yanıtında yok (GİRVAK dahil). Keşif onayındaki referans da aynı kapıdan açılır (`yeni_istek_ac`) ve e-postası gider; gencin kendi adresi orada sessizce atılır. Yanıt `UPDATE … WHERE durum = 'bekliyor' RETURNING id`. Geri çekme `POST /dogrulama/referans/{id}/geri-cek` (sayfa içi onayla; tekrarı yan etkisiz; geri çekilen istek `kanit_bekliyor`'da sayılmaz). Zaman aşımı geçişini yapan kod gence `referans_yanit_yok` bildirimini aynı işlemde yazar (okuma anı ya da Canlılık taraması, hangisi önce). Canlılık taraması 3. gün tek hatırlatma gönderir (yalnızca `gonderim_tarihi` dolu, yani sistemin e-posta gönderdiği isteklere).
> Uygulamada netleşen kararlar: (1) Referans başlığı **kişi başına** ortalama: her referansın bilinen yanıtlarının ortalaması, sonra kişiler arası ortalama (0.5 yukarı); çok soruya yanıt veren daha ağır basmaz. Herkes "bilmiyorum" dediyse "—". (2) Rol / Sonuç desteği için güncel referanslardan **birinin** "evet"i yeter (destek kanıt gibidir, oylama değil; "hayır" zaten başlığı düşürür). (3) Destek değişince kalem **arka planda yeniden puanlanır** (`kart_hazirlama.kalemi_yeniden_puanla`): değerlendirme girdisinin özeti desteği içerdiği için model bir kez çağrılır; referans kişi beklemez, hız sınırı yanıtı düşürmez. (4) Kalemde yazılmamış pay / sonuç sorulmaz, gelen yanıt kaydedilmez. (5) `kurumsal_eposta` sütunu **saklanmadı**: güç işareti adresten okuma anında hesaplanır (`eposta_gucu`), eski satırlar da kapsanır, iki kaynak tutarsızlaşmaz. (6) Referans kişiye "siz" (firmaya giden metinlerle aynı).
> **Ertelenen / borç:** "Kurumsal" bugün "ücretsiz posta sağlayıcısı değil" demek; kuruluşun web sitesiyle alan adı karşılaştırması kalemde kuruluş sitesi tutulmadığı için yok (§ 18). Arka plandaki yeniden puanlama LLM hatasında kalemi eski puanla bırakır; bir sonraki değerlendirme (kanıt, itiraz) desteği içerir. `yanit_isareti` boş; `referans_supheli` sinyalleri adım 11. Karne değişmedi (değerlendirme setinde referans yanıtı yok).

- **Bulgular:** 18, 20, 21 (engeller ve doğrudan e-posta), 22, 23, 24, 31.
- **İş birimleri:**
  1. Migration (referans sütunları); `referans_gecisi` += `geri_cekildi`.
  2. Doğrudan e-posta ve token'ın hiçbir yanıtta olmaması.
  3. 4 soruluk form (backend + `/referans` sayfası, pay ve sonuç ayrı satırlarda).
  4. Engeller, koşullu yanıt, geri çekme.
  5. Hatırlatma ve zaman aşımı bildirimi (Canlılık taramasından).
- **Belgeler:** agent-specs § 4.2, sequence-diagrams Akış 2, api-contracts.

### Adım 8: Hesap bağlama

> **Durum: tamamlandı** (`2cda007` sahiplik çekirdeği, `e2080ce` OAuth + GitHub, `ae4f0fe` GitLab, `4882b52` ORCID, `74476ca` doğrulama kodu, `56d743b` betik, `7ded940` frontend). Sahiplik saf bir kuraldır (`agents/dogrulama/hesap_sahipligi.py`): kanıttaki hesap izleri (adresteki hesap `core/kanit_okuma/hesap_izi.py`, oEmbed yazar adresi, repo sahibi ve katkıcılar) bağlı hesapla eşleşirse seviye B. Uygulama ve karne aynı yoldan (`okuma.kanit_oku(bagli_hesaplar=…)`).
> Uygulamada netleşen kararlar (Zühre, 2 Eki: GitLab okuyucusu bu adımda; OAuth anahtarı yokken bayrakla): (1) **B'de çalışmanın içindeki iddia yine iddia:** Sonuç'u B'de yalnızca platformun ölçtüğü veri destekler (`KanitBelgesi.platform_metni`: yıldız, katkıcılar; alıntı orada olmalı), Rol'ü yalnızca katkı oranı / bireysel kural / referans; metindeki destek yalnızca A'da. Bu dal B hiç oluşmadığı için önceden uykudaydı (`KURAL_SURUMU` adim8). (2) Bireysel kural: GitHub katkı ≥ %90; GitLab katkıcı listesi kullanıcı adı vermediği için kullanıcı ad alanındaki tek katkıcılı proje %100, çok katkıcılıda pay bilinmez; bağlı Medium / kişisel site / Behance / Dribbble sayfası; video ve Kaggle notebook bireysel değil. (3) Eşleşme kullanıcı adı ya da değişmez kimlikle, harf büyüklüğünden bağımsız; kişisel sitede alt alan adları da gencin. (4) OAuth backend'de oturum tutmaz: imzalı 10 dakikalık durum (hesap + sağlayıcı), sağlayıcı frontend'e döner (`/hesap-baglama/{saglayici}`), frontend kodu Bearer ile iletir; ayarı olmayan sağlayıcı arayüzde görünmez. (5) Kullanıcıya "doğrulama kodu" (rehberde "profil" kayıt bilgisi demek); okunacak profil adresini sunucu kurar (sorgu dizesi atılır, kişisel sitede ana sayfa): kod başkasının sayfasında yankılanamaz. (6) Genç başına tek açık elle inceleme (tek karar iki hesabı birden onaylamasın); GİRVAK onayı `yontem=elle`. (7) Bağlantı değişince linkli kalemler arka planda yeniden okunur (`kart_hazirlama.kalemleri_yeniden_oku`); seviyesi değişmeyen kalemde önbellek tutar, model çağrılmaz.
> **Ertelenen / borç:** ORCID bağlanır ama puana etkisi akademik okuyucuyla (§ 8). YouTube'da Sonuç 3 için izlenme sayısı (platform verisi) Data API okuyucusu ister; bugün oEmbed. Okunamayan profil bugün doğrudan GİRVAK'a gider; yedek okuyucu adım 10'da önce denenecek. Kod kontrolünde hız sınırı yok (istek güvenli katmandan geçiyor). Tarayıcıda uçtan uca denenmedi: OAuth uygulamaları ve `YOUTUBE_API_ANAHTARI` Zühre'de (`.env.example`).
> **Karne (`karneler/2026-10-02-mevcut_sistem-taslak-adim8.md`):** Kanıt birebir %62 → %76, Rol %76 → %84, Sonuç %82 → %84; sahte vakada yanlış 3: 0, dil ihlali: 0. Bağlı vakalarda GitHub bireysel 3/3/3, %78 katkı 3/2/2, kişisel blog 3/3, başkasının reposu bağlı hesapla 2. Kalanlar: Dribbble / Kaggle bağlı (bot engeli, JS) → adım 10; Medium bağlı vakada Kanıt "—" (kasette okunamadı, ayrıca bakılmalı); YouTube Sonuç 3 izlenme verisi ister; bağlı portfolyoda Rol 2 (model ekip / müşteri ortaklığı gördü; etiket kararı Zühre'de).

- **Bulgular:** 2, 36.
- **İş birimleri:**
  1. Migration (`bagli_hesap`, `profil_kodu`).
  2. `OAuthSaglayici`: GitHub, GitLab, ORCID (her biri ayrı commit).
  3. `ProfilKoduPlatformu`: YouTube (Data API), Kaggle, Behance, Dribbble, Medium, Vimeo, SoundCloud, kişisel site.
  4. Okunamayan profil → yedek okuyucu → `profil_kodu_elle` işareti.
  5. Seviye B kuralları okuyuculara bağlanır (sahiplik kaynağı); bireysel vakalarda karne hedefi: bağlı → 3/3, bağlı değil → Kanıt 2.
  6. Frontend: "Hesaplarım" bölümü.

### Adım 9: Dosya ve görsel

> **Durum: tamamlandı** (`39ccb0e` bütün parçaların değerlendirilmesi, `ee5bdaa` depo + virüs adaptörleri, `ff16a3a` yükleme hattı ve uçlar, `798305a` PDF / görsel okuma, `b2dfd90` çapa çekirdeği + QR, `5666326` e-imza, `634baa3` Open Badges, `34128de` e-Devlet, `d7df769` belge tekilliği, `dfa4340` C2PA, `4185632` firma görünürlüğü, `3fb3fa4` frontend, `4e0a35f` karne).
> Uygulamada netleşen kararlar (Zühre, 3 Eki: öneriler onaylandı): (a) geliştirmede yerel disk deposu (`DEPO_SAGLAYICI=yerel`, indirme backend'in `/dosya/{token}` ucundan); yayında R2 gerekli (Railway diski kalıcı değil). (b) ClamAV kapalıyken ya da ulaşılamazken dosya taranmadan kabul edilir; temizlik her durumda çalışır, yalnızca "zararlı" reddeder. (c) Bilinen düzenleyenler küçük bir veri listesi (`core/capalar/duzenleyenler.py`), GİRVAK genişletir.
> Plandan sapmalar: (1) **Değerlendirme artık bir çalışmanın bütün parçalarını okur** (önceden yalnızca ilk link): her parça ayrı puanlanır, başlık başına en güçlüsü (§ 2), not Kanıt'ı veren parçadan. Dosya ve linkin aynı çalışmada durabilmesi için ön koşuldu. (2) **Çapalar seviye değil gerçek yazar;** seviye okuma anında saf kuralla ve gencin o anki kimlik durumuyla hesaplanır (`agents/dogrulama/capalar.py`): e-posta doğrulanınca ya da GİRVAK kararı gelince eski dosyalar da doğru okunur (e-posta doğrulanınca dosyası olan kart arka planda yeniden okunur). (3) İçerik yükleme anında bir kez okunur ve maskelenip saklanır; değerlendirme ve itiraz dosyayı yeniden okumaz. (4) Görselde betim modele bağlamdır, alıntı kaynağı değildir (`OkunanKanit.alinti_metni`). (5) C2PA bilgisi nota değil kanıt satırına ("Oluşturan araç") yazılır: not puanlardan kurulan şablondur. (6) Kendi imzaladığı belge (imzalayan = genç) güvenilir kök olsa da en çok C. (7) Doğrulama sayfası için genel okuyucunun "en az metin" eşiği yok (doğrulama sayfaları kısadır).
> **Ertelenen / borç:** pHash ve dosya özetinin başka hesapta tekrarı adım 11'de (`ayni_iddia_cok_hesapta`). İmzalı (JWS) Open Badges ve OB 3.0 doğrulanmıyor (D kalır). Kamu SM kökleri depoda yok: `EIMZA_KOK_KLASORU` verilmezse Kamu SM imzalı belge "geçerli ama kök tanınmıyor" (C). E-imza iptal denetimi soft-fail, ağ isteği yok. Adres maskelemesi kalıba dayanır (mahalle + numara), her adresi yakalamaz. Bozuk imza ve QR sayfasında farklı ad için `belge_tutarsiz` işareti adım 11'de. `belge->capalar` sorgusu indeksli değil (ölçek küçük). Gencin silinmesi (hesap silme) yolunda depo temizliği yok; kalem ve parça silmede var. Tarayıcıda uçtan uca denenmedi.
> **Karne (`karneler/2026-10-05-mevcut_sistem-taslak-adim9.md`):** Kanıt birebir %76 → %80, Sonuç %84, Rol %84; sahte vakada yanlış 3: 0, dil ihlali: 0. İki çapasız PDF vakası "—" → 1 (beklenen). Görsel ve çapalı (QR, imza, rozet, e-Devlet) vaka sette yok; eklenirse etiketleri Zühre koyar. Testler: backend 1727, frontend 141.

- **Bulgular:** 44, 48 (belge tekilliği).
- **İş birimleri:**
  1. `Depo` (R2), `VirusTarayici` (ClamAV) adaptörleri.
  2. Yükleme hattı: tür, boyut, virüs, `pikepdf`, Pillow; maskeleme.
  3. PDF analizi (`pypdf` → Gemini).
  4. Görsel analizi (iki adımlı, `gorsel_metni`).
  5. Çapalar, her biri ayrı commit: QR, e-imza, Open Badges, e-Devlet (GİRVAK kuyruğu); belge tekilliği → `ayni_belge_iki_hesapta`.
  6. C2PA.
  7. Frontend: yükleme, seçenek kutusu, görünürlük.
- **Belgeler:** KVKK aydınlatma, api-contracts.

### Adım 10: Yedek okuyucu

> **Durum: tamamlandı** (`87d3a3e` Playwright servisi, `bb59eaf` adaptör + zincir + ekran görüntüsü, `3d0bb15` Jina adaptörü, `0214481` kapalı platformlar ve ekran istemi, karne commit'i).
> Uygulamada netleşen kararlar: (1) **Servis backend reposunda ayrı uygulama** (`backend/yedek_okuyucu/`, kendi `Dockerfile` ve `requirements.txt`'si): SSRF kuralları tek kaynaktan, imaja yalnızca `guvenli_istek.py` kopyalanır. (2) **Tarayıcının tek ağ kapısı süreç içi süzgeçli vekil:** her bağlantı `hedefi_dogrula` ile denetlenip doğrulanan IP'ye açılır (yerel adresler de vekilden, WebRTC kapalı). `page.route` yetmedi: yakalanan isteğe verilen 3xx'i tarayıcı denetimsiz izliyor (denendi); istekleri Python'dan atmak da tarayıcının TLS kimliğini kaybettirip bot engelini geri getiriyor. (3) Tam Chromium'un yeni başsız kipi + "HeadlessChrome"suz kullanıcı aracı: Behance ve GrabCAD ancak böyle 200 döndü; durum ana çerçevenin son belgesinden (Dribbble önce 202'lik doğrulama sayfası veriyor). (4) Ne zaman ekran görüntüsü alınacağına backend karar verir (`EkranKurali`, eşik `EN_AZ_METIN`); doğrulama / giriş sayfasının görüntüsü kanıt sayılmaz. (5) Görüntüler tek model çağrısında okunur (`ekranlari_oku`), okunuş adres başına 24 saat süreç içi önbellekte (`kanit_okuma/onbellek.py`): maliyet ve betimin her seferinde değişip kalem özetini bozması. (6) Profil kodu okuması da engelde yedeğe gider (adım 8 borcu). (7) Jina'nın adı arayüzde `UzakOkuyucu` (`UZAK_OKUYUCU=jina|kapali`, varsayılan kapalı); KVKK metnine eklendi.
> Plandan sapmalar: (1) **Kapalı platformlar (Instagram, LinkedIn, Facebook) yedeğe gitmez** (§ 18): Instagram tarayıcıda açıldı ama içerik giriş penceresinin arkasındaydı; model "ilgisiz" deyip Kanıt 0 veriyordu, bu ceza olurdu. "—" kalır. (2) Görsel platform listesine GrabCAD, Sketchfab, DeviantArt, Pinterest ve portfolyo kurucuları da girdi; genel site kurucuları (Wix, Squarespace) girmedi, oradaki metinsiz sayfa "metin azsa" kuralına düşer.
> **Ertelenen / borç:** Dribbble shot sayfasında yazarın kullanıcı adı yok (yalnızca adı ve ekip bağlantısı): bağlı Dribbble'da shot B'ye çıkmıyor; bir Dribbble okuyucusu (API ya da profil sayfası) gerekir. Vekilde istek başına bant / süre sınırı yok (yalnızca sayfa zaman aşımı ve eşzamanlılık). Yedek okuyucu sonucu backend'de önbelleğe alınmıyor (yalnızca görüntü okunuşu); her değerlendirmede sayfa yeniden açılır. Windows'ta vekil kapanışında asyncio "bağlantı sıfırlandı" gürültüsü log'a düşüyor (Linux'ta yok). Railway kurulumu ve Jina anahtarı Zühre'de. Tarayıcıda uçtan uca denenmedi (servis yerelde gerçek sitelerle denendi).
> **Karne (`karneler/2026-10-05-mevcut_sistem-taslak-adim10.md`):** Kanıt birebir %80 → %96 (±1 %80 → %100), Sonuç %84, Rol %84; sahte vakada yanlış 3: 0, dil ihlali: 0. Behance, Dribbble (bağsız), Kaggle (iki vaka), Medium (iki vaka) artık okunuyor; ansiklopedi vakası "—" → 0 (beklenen). Kalan iki fark etiket sorusu: GrabCAD sayfası "Catia V5R20" diyor, iddia "SolidWorks" (çelişki, Kanıt 1; beklenen 2); bağlı Dribbble'da Kanıt 2 / Rol 2 (beklenen 3, yukarıdaki borç). Kaset: `yedek_okuyucu.json` + `yedek/` (1,5 MB). Testler: backend 1781, frontend 141.

- **Bulgular:** 3 (yedek), 8, 46.
- **İş birimleri:**
  1. Playwright servisi (ayrı uygulama, Railway): metin + ekran görüntüsü (1280 px, en çok 3 parça).
  2. `YedekOkuyucu` adaptörü, zincire bağlanması, ekran görüntüsü kuralları.
  3. Jina adaptörü (kapalı bayrak).

### Adım 11: Kötüye kullanım işaretleri

> **Durum: tamamlandı** (`746a90c` ayni_iddia_cok_hesapta, `54f881a` GorselArayici + gorsel_baskasinda, `149de0d` referans_supheli, `6193b57` belge_tutarsiz + kanit_celisiyor, `59d43a9` "Doğrulanamadı" etiketi ve karara itiraz). Migration `b9e4c2a7d1f3` (`servis_kullanimi`). Hepsi `app/servisler/dogrulama/isaretler/` altında; `kanit.uygula` (değerlendirme sonrası) ve `dosyalar.dosya_ekle` (yükleme sonrası) çağırır. İşaret puanı değiştirmez (İ1).
> Uygulamada netleşen kararlar: (1) **Sinyal tekrarı:** `inceleme.sinyal_ekle` her sinyale `anahtar` verir; aynı kalemde aynı türden herhangi bir işarette (açık ya da kararlı) görülmüş anahtar yeniden eklenmez: GİRVAK'ın "sorun yok" dediği eşleşme her değerlendirmede kuyruğa dönmez. (2) **pHash saf Python** (32×32 DCT, 64 bit; numpy bağımlılığı yok), bit farkı ≤ 6 benzer; Postgres `bit_count` ile tam tarama (ölçek küçük). Link `normal_url`, dosya SHA-256 ile aranır; **takım projesi:** iki parça da OAuth katkıcı listesiyle doğrulandıysa işaret yok. (3) **Cloud Vision kapalı bayrak** (`GORSEL_ARAYICI=kapali`): yalnızca tasarım / fotoğraf alanındaki gençlerin görsellerinde (rol alanı ya da araçlar, saf kural `gorsel_kaynagi.py`), aylık tavan kalıcı sayaçla (`servis_kullanimi`, koşullu artırma). Yalnızca birebir eşleşme, gencin bağlı hesabında / kanıt linklerinin hesabında olmayan sayfa işarettir; servis tarih vermediği için "daha eski" sorusunu GİRVAK sayfaya bakarak yanıtlar. (4) **referans_supheli izleri `referans_istegi.yanit_isareti` JSONB'sinde** (yeni tablo yok): tuzlu HMAC IP ve tarayıcı özeti, 90 gün sonra Canlılık taramasında silinir, sinyaller kalır; yerel / özel ağ IP'si özetlenmez. Sinyaller: gencin izleriyle aynı IP / tarayıcı, 20 sn'den kısa ya da hiç açılmamış form, aynı kişi ≥ 3 gence yanıt. Gencin "izi", referans istediği anlardaki istek izidir (giriş kaydı tutulmuyor). (5) **belge_tutarsiz:** bozuk imza; QR'dan ya da bilinen düzenleyenden açılan sayfada ne ad ne e-posta (tanınmayan, metinde geçen adres sayılmaz). (6) **kanit_celisiyor:** çekirdek parça başına alıntısı denetimden geçmiş çelişkileri döner; puan kuralı değişmedi. (7) **"Doğrulanamadı" etiketi:** türünün son kararı "doğrulanamadı" olan işaret etiket verir; genç "Karara itiraz et" der: model çağrılmaz, hak harcanmaz, aynı türden yeni işaret GİRVAK'a gider.
> **Ertelenen / borç:** Cloud Vision anahtarı ve açılması Zühre'de (kapalı geldi). IP özeti proxy arkasında `X-Forwarded-For`'un son girdisine güvenir: Railway dışında dağıtımda proxy yapılandırması gözden geçirilmeli. pHash taraması indekssiz (ölçek büyürse bit-ağacı ya da LSH). Çelişki sinyali yalnızca model "çelişiyor" derse; kuyrukta "kanıtın hangi kısmı" için sayfa vurgusu yok. Tarayıcıda uçtan uca denendi (5 Eki, log kipinde e-posta): şüpheli referans (19 sn form), "Doğrulanamadı" etiketi, karara itiraz (202, model çağrısı yok), "Sorun yok" ile kapanış; IP sinyali yerelde üretilmez (özel adres). Karne değişmedi: Kanıt birebir %96, Sonuç %84, Rol %84; sahte vakada yanlış 3: 0, dil ihlali 0 (`karneler/2026-10-05-mevcut_sistem-taslak-adim11.md`).

- **Bulgular:** 21 (işaretler), 43.
- **İş birimleri:**
  1. `ayni_iddia_cok_hesapta` (normal URL, SHA-256, pHash).
  2. `GorselArayici` (Cloud Vision, kapalı bayrak, aylık tavan) → `gorsel_baskasinda`.
  3. `referans_supheli` (tuzlu özetler, 90 gün saklama).
  4. `belge_tutarsiz`, `kanit_celisiyor`.

### Adım 12: Süreklilik ve ölçümün kalıcılaşması

> **Durum: tamamlandı** (`5f211fc` link çürümesi yoklaması, `81eb232` gözlem paneli ve kalıcı servis sağlığı, `b31db82` adalet raporu, `4e7ca5e` haftalık canlı karne betiği, `87613c8` zaman kaydırma düzeltmesi). Migration `c5d8f2a1b7e3` (`kanit_gozlemi`, `degerlendirme_gozlemi`, `servis_gunlugu`).
> Uygulamada netleşen kararlar: (1) **Çürüme yoklaması Canlılık taramasının bir adımı** (`servisler/dogrulama/curume.py`, kurallar saf `agents/dogrulama/curume.py`); yeni zamanlayıcı yok. Yalnızca eskiden açık okunmuş (`erisim = acik`) ya da sayacı işleyen link yoklanır: baştan giriş isteyen (LinkedIn) ya da hiç bulunamayan link zaten "—" / 0 almıştı, onun "çürümesi" gence yanlış haber olurdu. Yoklama yalnızca erişim durumunu okur (yedek okuyucu ve model yok), taramada en çok 100 link, haftada en çok bir. Sayaç `kanit_parcasi.curume_sayaci`; eşik 3'te parça `okunabilir_mi`'den çıkar (Kanıt "—", Sonuç ve Rol beyan tavanıyla), çalışma yeniden değerlendirilir, gence nötr `kanit_curudu` bildirimi gider, önceki puan `belge.curume.onceki_puanlar`'da saklanır; link geri gelirse sayaç sıfırlanır ve puan yeniden hesaplanır. Yeniden değerlendirme savepoint içinde: model arızası taramayı düşürmez, eşik işlenmemiş kaldığı için sonraki taramada beklemeden denenir. (2) **Gözlem kayıtları kişi ve adres taşımaz**, 90 gün saklanır (Canlılık taraması siler). Link okuması `hazirla` içinde (değerlendirme) ve yoklamada yazılır; dosya ve görseller yüklenirken okunduğu için yazılmaz. Model süresi ve token'ı `llm.kullanim_topla()` bağlam toplayıcısıyla; token'lar yalnızca modelin çağrıldığı değerlendirmede (önbellekten dönen yazılmaz). Servis günlüğü `SAGLIK.kalici` kancasıyla, uygulama açılışında bağlanır (testlerde bağlı değil), kendi kısa işleminde, hatayı yutar. (3) **Panel ucu ayrı:** `GET /girvak/gozlem?gun=` (`/saglik/servisler` süreç içi anlık görünüm olarak kaldı). Panelde "Gözlem" bölümü; hata türünün sınıf adı arayüzde gösterilmez (API'de var). (4) **Adalet:** `degerlendirme/adalet.py`; eşik `FARK_ESIGI = 0,5` puan ve `EN_AZ_VAKA = 3` plan sayı vermediği için **varsayım**, kapı değil iş olarak raporlanır. (5) **Canlı karne:** `python -m scripts.canli_karne`; kayıtlı (kaset) turu ile canlı turu aynı süreçte koşturup vaka başına sapmayı yazar; canlı tur geçici klasöre kaydeder ve silinir (kasetler ve kayıtlı karneler değişmez), ekran okunuşu önbelleği turlar arasında temizlenir.
> **İlk adalet tablosu (taslak etiket, `karneler/2026-10-05-mevcut_sistem-taslak-adim12.md`):** 13 alandan yalnızca beşinde (medya, tasarım, veri, yazı, yazılım) Kanıt 3'e giden vaka var; akademik, gönüllülük, kamuya kapalı, mühendislik, pazarlama, sertifika, staj / iş ve yarışmada yol yok, çoğunda üçten az dürüst vaka. Bu bir bulgu, ölçüm hatası değil: 45 taslak vakanın alan dağılımı dengesiz ve dosya / referans / hesap yolundan 3'e giden vaka az. Hedef 120 vakaya giderken bu alanlara 3'e giden vakalar (referans + belge + hesap yolu) eklenmeli. Karne puanları değişmedi: Kanıt %96, Sonuç %84, Rol %84; sahte vakada yanlış 3: 0, dil ihlali 0.
> **Ertelenen / borç:** Gözlem paneli tarayıcıda denendi (5 Eki: GitHub erişimi, servis durumu, değerlendirme süresi görünüyor). Platform dağılımı yalnızca bu adımdan sonraki okumalardan oluşur (geçmiş yok). `platform` alanı okuyucunun tanıdığı platform adıdır; tanınmayan siteler "web" altında toplanır. Yoklama yedek okuyucuyu kullanmaz: bot engelli bir sitede link silinse bile `engellendi` döner ve sayılmaz (çürüme geç fark edilir). Canlı karne henüz gerçek ağ ve modelle çalıştırılmadı (ücretli; ilk çalıştırma Zühre'de); zamanlayıcısı kurulmadı (Railway cron'u Zühre'de). Haftalık çalıştırma için çıktı klasörü (`karneler/canli/`) canlıda geçici dosya sistemindedir: cron çıktıyı yalnızca günlükte (stdout) saklar.

- **Bulgular:** 40, 42.
- **İş birimleri:**
  1. Link çürümesi yoklaması (doğru sayaç).
  2. Gözlem paneli: erişim dağılımı, servis sağlığı.
  3. Adalet raporu (karnenin alan kırılımı).
  4. Haftalık canlı karne betiği.

### Adım 13: Eşleştirme incelemesine hazırlık

> **Durum: tamamlandı.** `matching-algorithm.md` § 4.1: iki seçenek, 45 vakadan türetilen oran dağılımı (ortalama 0,54, ortanca 0,50) ve örnek kart tablosuyla. (b) için `yetenek_kaniti` verisi sette yok ve ihtiyaç kartında gereken yeteneklerin listesi yok; bu iki sınır ve karar soruları belgede. Formül ve kod değişmedi.

- **Bulgu:** 27.
- **İş:** `matching-algorithm.md`'ye iki seçenek (§ 11.1) karne verisiyle birlikte yazılır. Formül **değişmez**; karar Eşleştirme incelemesinde verilir.

### Adım 14: Son belge denetimi

> **Durum: tamamlandı.** README (Doğrulama satırı ve kapsam paragrafı: SMTP yok cümlesi eskiydi), CLAUDE.md (Doğrulama paragrafı), roadmap (Doğrulama incelemesi bölümü) güncellendi. Metinler `genc-akisi-metinler.md`'de, her adımda eklendi.

Her adım kendi belgesini güncelledi. Bu adım yalnızca çapraz denetimdir: README, içerik rehberi (yeni metinler), CLAUDE.md "Şu an neredeyiz", roadmap.

---

## 16. Test stratejisi

| Düzey | Ne |
|---|---|
| Birim (saf) | Seviye tavanları, puan kuralları, bireysel kurallar, alıntı denetimi, ad eşleşmesi ve seviye A koşulu, referans çevrimi ve durum makinesi, erişim kalıpları, not şablonu, parça bölme |
| Sözleşme | Kayıttaki her okuyucu ve her dış servis adaptörü ortak sözleşme testinden geçer (kayıtlı yanıtlarla) |
| Dosya | Örnek PDF (metinli, taranmış, imzalı, imzası bozuk, QR'lı), görsel (EXIF, C2PA, polyglot), zararlı dosya taklidi |
| Uç | Başarılı akış + 401 / 403 / 404; tekrar ve geçersiz geçiş 409 |
| Değerlendirme seti | § 10.1 ölçütleri, CI'da kasetle |
| Zarif düşüş | Her servis kapalı ve hatalı iken değerlendirme tamamlanır, ilgili sinyal "—" olur |
| Canlı | `scripts/dogrulama_e2e.py` ve haftalık canlı karne |

**Haftalık canlı karne (adım 12):** `python -m scripts.canli_karne` seti gerçek ağ ve modelle ölçer, kayıtlı (kasetli) karneyle karşılaştırıp vaka başına sapmayı yazar (`degerlendirme/canli.py`); kasetlere dokunmaz, rapor `karneler/canli/` altına gider; çıkış kodu kabul eşiklerine bağlı. Zamanlayıcı kurulmaz (CLAUDE.md): çalıştırmak platform cron'unun işi.

---

## 17. Kararlar (kapandı)

Karar 1–13 onaylandı (1 Eki 2026).

| # | Karar |
|---|---|
| Karar 1 | Link içeriği okunur (karar 13 değişir) |
| Karar 2 | Puanı kural verir |
| Karar 3 | Not şablondan yazılır |
| Karar 4 | Seviye tavanları (§ 2) |
| Karar 5 | Değerlendirilmeyen "—" (NULL) |
| Karar 6 | 4 soruluk referans formu |
| Karar 7 | Referans e-postasını sistem gönderir |
| Karar 8 | Dosya ve görsel kanıtı; varsayılan görünürlük yalnızca genç ve GİRVAK |
| Karar 9 | Hesap bağlama; yalnızca § 6.1'deki tablo |
| Karar 10 | Linksiz kalem beyan tavanıyla değerlendirilir |
| Karar 11 | GİRVAK inceleme kuyruğu |
| Karar 12 | Dış servisler § 14.4'teki gibi |
| Karar 13 | Kayıtta e-posta doğrulaması |

## 18. Bilinen sınırlar

- **Kimlik:** gencin gerçekten o kişi olduğu doğrulanmıyor. Seviye A ve B riski daraltır, ortadan kaldırmaz.
- **Sahte belge:** çapasız sahte belge tespit edilmeyebilir. Etkisi seviye D ile sınırlıdır.
- **Kapalı platformlar:** LinkedIn ve Instagram okunamaz; alternatif yol sunulur.
- **Referansın dürüstlüğü:** e-postası doğrulanmış bir arkadaş yine de abartabilir. İşaretler bunu görünür kılar.
- **Kurumsal e-posta:** ücretsiz posta sağlayıcısı dışındaki her alan adı "kurumsal" görünür; kişisel alan adı da bu sınıfa düşer. Kuruluşun sitesiyle karşılaştırma için kalemde kuruluş adresi gerekir.

## 19. Kaynaklar

- Referans sahteciliği: [Xref](https://www.xref.com/blog/avoiding-bad-hires-with-xref-fraud-detection), [Crosschq](https://www.crosschq.com/blog/interview-fraud-detection-your-complete-defense-guide-for-2025)
- Belge sahteciliği: [Resistant AI](https://resistant.ai/products/documents), [Inscribe](https://www.inscribe.ai/document-fraud-detection-software)
- Sayfa okuma: [Jina AI ve Firecrawl](https://blog.apify.com/jina-ai-vs-firecrawl/), [Firecrawl alternatifleri](https://www.tinyfish.ai/blog/firecrawl-alternatives-for-developers-in-2026)
- oEmbed: [oembedproviders.com](https://www.oembedproviders.com/), [Microlink](https://microlink.io/embed)
- Görsel kaynak araması: [Cloud Vision Web Detection](https://docs.cloud.google.com/vision/docs/internet-detection)
- İçerik kimlik bilgisi: [C2PA Python](https://opensource.contentauthenticity.org/docs/c2pa-python/)
- PDF anlama: [Gemini belge işleme](https://ai.google.dev/gemini-api/docs/document-processing)
- Dijital sertifika: [Credly Open Badge 3.0](https://info.credly.com/product/open-badge-3.0), [1EdTech Open Badges](https://www.1edtech.org/standards/open-badges)
- e-Devlet: [Belge Doğrulama](https://www.turkiye.gov.tr/belge-dogrulama)
- Yetenek ağları: [Upwork ve Toptal](https://www.upwork.com/resources/upwork-vs-toptal)
