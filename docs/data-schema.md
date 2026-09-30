# Veri Şeması

## ER Diyagramı

```mermaid
erDiagram
  KULLANICI ||--o{ YETENEK_KARTI : sahiptir
  YETENEK_KARTI ||--o{ SOMUT_CIKTI : icerir
  SOMUT_CIKTI ||--o| GUVEN_SKORU : degerlendirilir
  SOMUT_CIKTI ||--o{ REFERANS_ISTEGI : ister
  KURUM ||--o{ IHTIYAC_KARTI : olusturur
  YETENEK_KARTI ||--o{ ESLESME : aday_olur
  IHTIYAC_KARTI ||--o{ ESLESME : eslesir
  ESLESME ||--o| ISBIRLIGI : donusur
  ISBIRLIGI ||--o{ MILESTONE : icerir
  ESLESME ||--o{ CANLILIK_OLAYI : tetikler
  HESAP ||--o| KULLANICI : profil
  HESAP ||--o| KURUM : profil
  HESAP ||--o{ BILDIRIM : alir
  ESLESME |o--o{ BILDIRIM : konusu

  KULLANICI {
    uuid id PK
    string ad
    string email
    string sehir
    text[] calisma_modelleri
    text[] musaitlikler
    string kariyer_durumu
    string okul
    string bolum
    int sinif
    int mezuniyet_yili
    date musaitlik_baslangici
    string github_url
    string linkedin_url
    string portfolyo_url
  }
  YETENEK_KARTI {
    uuid id PK
    uuid kullanici_id FK
    string rol_alani
    string deneyim_seviyesi
    text[] sektor_ilgi_alani
    text[] araclar_teknolojiler
    boolean kanit_bekleyen
    int versiyon
    vector embedding
  }
  SOMUT_CIKTI {
    uuid id PK
    uuid yetenek_karti_id FK
    string baslik
    string aciklama
    string kanit_linki
    string kanit_turu
    date tarih
  }
  GUVEN_SKORU {
    uuid id PK
    uuid somut_cikti_id FK
    int kanit_orijinalligi
    int sonuc_olculebilirligi
    int rol_netligi
    int ucuncu_taraf_onayi
    string gerekce_metni
  }
  REFERANS_ISTEGI {
    uuid id PK
    uuid somut_cikti_id FK
    string referans_email
    string token
    string durum
    int puan
    string yanit_metni
    timestamp olusturma_tarihi
  }
  KURUM {
    uuid id PK
    string ad
    string sektor
    string sehir
    string iletisim_email
    string tur
    string web_sitesi
    string calisan_araligi
    int kurulus_yili
    text tanitim
    string yetkili_ad
    string yetkili_gorev
    string dogrulama_durumu
    timestamp dogrulama_tarihi
  }
  FIRMA_KARTI {
    uuid id PK
    uuid kurum_id FK
    text ne_yapiyoruz
    text[] yetkinlikler
    text onceki_isler
    text aranan_isbirligi
    text[] isbirligi_turleri
    int versiyon
    vector embedding
    uuid oturum_id
    timestamp olusturma_tarihi
  }
  IHTIYAC_KARTI {
    uuid id PK
    uuid kurum_id FK
    string problem_tanimi
    string basari_kriteri
    string kisitlar
    string sehir_tercihi
    string musaitlik_tercihi
    vector embedding
    timestamp olusturma_tarihi
    string durum
    string aranan
    text[] aranan_firma_turleri
    string isbirligi_turu
    string kapanma_nedeni
    timestamp kapanma_tarihi
  }
  ESLESME {
    uuid id PK
    uuid yetenek_karti_id FK
    uuid ihtiyac_karti_id FK
    float skor
    string gerekce_metni
    string durum
    timestamp son_aktivite_tarihi
  }
  ISBIRLIGI {
    uuid id PK
    uuid eslesme_id FK
    date baslangic_tarihi
    string durum
    timestamp genc_plan_onayi
    timestamp kurum_plan_onayi
    timestamp tamamlanma_tarihi
    text durum_ozeti
    timestamp ozet_tarihi
    bool plan_onerildi_mi
  }
  MILESTONE {
    uuid id PK
    uuid isbirligi_id FK
    string baslik
    text aciklama
    int sira
    date hedef_tarih
    string durum
    timestamp genc_isaret
    timestamp kurum_isaret
    string kanit_linki
  }
  CANLILIK_OLAYI {
    uuid id PK
    uuid eslesme_id FK
    timestamp tetiklenme_tarihi
    string tur
    string mesaj_metni
  }
```

## Tasarım Kararları

- **Genç akışı alanları (28-29 Eyl, `plans/genc-akisi.md` § 3).**
  - `HESAP.kvkk_onay_tarihi`.
  - `KULLANICI`'da kayıt formunun yapısal alanları (yukarıdaki diyagram). Fotoğraf, yaş, cinsiyet, medeni durum, TC kimlik no, adres ve ücret beklentisi bilinçli olarak yok; şema bu alanları 422 ile reddeder.
  - `YETENEK_KARTI.sertifikalar`, `diller`; `versiyon` her gerçek düzenlemede artar.
  - `SOMUT_CIKTI.is_turu`, `kendi_rolu`, `olculebilir_sonuc` (eskiden açıklamaya birleştiriliyordu; rubrik ve embedding birleşik okur, `app/core/is_kalemi.py`), `icerik_tarihi` (NULL = hiç değişmedi; değişince güven göstergesi sıfırlanır) ve `oturum_id` ("Yeni iş ekle" sohbeti için, ertelendi).
  - `REFERANS_ISTEGI.yanit_tarihi`: `icerik_tarihi`'nden önce verilmiş yanıt geçmişte kalır, puana girmez.
  - `ESLESME` ve `IHTIYAC_KARTI.durum` aşağıda.

- **`HESAP` (Faz B) — kimlik profilden ayrı.** `hesap(id, email UNIQUE, sifre_hash, rol, olusturma_tarihi)`; `rol` ∈ `genc | kurum | girvak`. Genç hesabının bir `KULLANICI` profili, kurum hesabının bir `KURUM` profili olur (`hesap_id` UNIQUE FK, 1-1); GİRVAK hesabının profili yok. Şifre argon2id ile hash'lenir, düz şifre saklanmaz. `hesap_id` nullable: Faz B öncesi profiller için hesap uydurulmadı. Gerekçe ve iki seçeneğin karşılaştırması: `faz-b-kimlik-ve-dongu.md` § 1.
- **`ISBIRLIGI` ve `MILESTONE` (Faz C) — Takip.** `ISBIRLIGI.durum`: `plan_bekliyor` → `aktif` (iki taraf da mevcut planı onaylayınca; düzenleme iki onayı da sıfırlar) → `tamamlandi` (son adım iki tarafça tamamlanınca, kural; ajanın kararı değil). `MILESTONE.durum`: `bekliyor` → `tamamlandi` (genç ve kurum ayrı ayrı işaretler). **Gecikme saklanmaz**, okuma anında hesaplanır (`hedef_tarih < bugün` ve tamamlanmadı). Onaylanan plan kilitli; `aktif`'te yalnızca `kanit_linki` değişir. `durum_ozeti` Takip Ajanı'nın kesilebilir özeti, hiçbir kural ona bakmaz. **Tamamlanmış pilot** sinyali saklanmaz, `durum = tamamlandi` kayıtlarından hesaplanır ve Eşleştirme'nin doğrulama bonusuna girer (`matching-algorithm.md` § 4). Faz B'de `aktif` açılmış planı olmayan kayıtlar migration'la `plan_bekliyor` oldu. Bkz. `faz-c-takip.md`.
- **`BILDIRIM` (Faz B) — uygulama içi bildirim.** `bildirim(id, hesap_id FK CASCADE, tur, metin, eslesme_id FK nullable SET NULL, olusturma_tarihi, okundu_tarihi nullable)`. `tur` ∈ `yeni_oneri | ilgi | kabul | red | referans_yaniti` (Faz B), `plan_onerildi | plan_duzenlendi | plan_onayi | plan_onaylandi | adim_isaretlendi | adim_tamamlandi | isbirligi_tamamlandi` (Faz C); Canlılık (Faz D) aynı tabloya kendi türleriyle yazar. `olusturma_tarihi` INSERT anında `clock_timestamp()` ile atanır: `now()` işlem başlangıcını döndüğü için aynı işlemde yazılan bildirimler eşit zamanlı kalıp sıra belirsizleşiyordu. Olayla aynı işlemde yazılır; aynı geçişin tekrarı yeni bildirim yazmaz. Metin e-posta taşımaz. Gerçek e-posta gönderilmez. Bkz. `faz-b-kimlik-ve-dongu.md` § 6.
- **`GUVEN_SKORU` ve `REFERANS_ISTEGI`, `SOMUT_CIKTI`'dan ayrı tablolar.** Bir çıktının birden fazla referans isteği olabilir; güven skoru zamanla güncellenebilir olmalı (itiraz sonrası yeniden hesaplama).
- **`ESLESME.durum` ve ilgi alanları (genç akışı, `plans/genc-akisi.md` § 4).** Değerler: `onerildi`, `genc_ilgilendi`, `ilgileniliyor`, `kabul_edildi`, `reddedildi`, `kapandi`; kural tek yerde (`app/agents/eslesme_durumu.py`). Karar `durum`'da; `baslatan` (`genc | kurum`), `genc_ilgi_tarihi`, `genc_iletisim_onayi_tarihi`, `kurum_ilgi_tarihi` yalnızca "kim, ne zaman" bilgisi. Tek alan seçildi çünkü pipeline, Canlılık, GİRVAK sayıları ve sahiplik `durum`'u okuyor. Karşılıklı ilgi `kabul_edildi`'dir. `IHTIYAC_KARTI.durum` (`acik | kapandi`): kapalı ihtiyaç eşleştirmeye girmez, bekleyen kayıtlar `kapandi` olur. `IHTIYAC_KARTI.aranan` (`genc | firma`, varsayılan `genc`): ilanın hangi kapıdan açıldığı; aynı tablo, aynı pipeline ve ilgi kuralları, fark aday kaynağında. Ortak ilanında `aranan_firma_turleri` (boş = hepsi) ve `isbirligi_turu`; çalışma modeli ve müsaitlik yalnızca genç ilanında (`plans/firma-akisi.md` § 0 kararlar 4-5). Firma kapatırken neden seçer (`kapanma_nedeni`: `platformda_bulundu | baska_yoldan_bulundu | vazgecildi`, `kapanma_tarihi`); neden yalnızca GİRVAK sayılarında görünür, kapanan ilan tekrar açılmaz (`plans/firma-akisi.md` § 7).
- **`KURUM` kayıt alanları (firma akışı, `plans/firma-akisi.md` § 2).** `tur` (`girisim | kobi | kurumsal`), `web_sitesi`, `calisan_araligi` (`1-10 | 11-50 | 51-250 | 250+`), `kurulus_yili`, `tanitim` (≤300), `yetkili_ad`, `yetkili_gorev`; hepsi nullable. Zorunluluk (tür, sektör, şehir) kayıt şemasında; eski hesaplarda boş olabilir, panel engellemeyen bir bantla ister. Vergi numarası, adres ve telefon bilinçli olarak toplanmaz. KVKK onayı gençteki gibi `hesap.kvkk_onay_tarihi`'nde. Kurallar `app/core/firma_profili.py`. **Doğrulama** (§ 6): `dogrulama_durumu` (`bekliyor | dogrulandi | simdilik_degil`, varsayılan `bekliyor`) ve GİRVAK'ın karar anı `dogrulama_tarihi`. Alan adı ipucu saklanmaz, okuma anında hesaplanır (`app/core/firma_dogrulama.py`, ağ isteği yok). Web sitesinin alan adı değişince `bekliyor`a döner. Dışarıya yalnızca `dogrulandi: bool` açılır; "şimdilik değil" firmaya "bekliyor"dan ayırt edilmez.
- **`FIRMA_KARTI` (firma akışı, `plans/firma-akisi.md` § 0 karar 10).** Firma başına bir kart (`kurum_id` UNIQUE), isteğe bağlı: yalnızca genç arayan firmanın karta ihtiyacı yok, kartı olmayan firma ortak olarak önerilmez. Yetenek kartı genişletilmedi; onun alanları gence özel. Paylaşılan kısım eşleşme, pipeline, ilgi kuralları ve iş birliği. Embedding firmanın **ne yaptığını** temsil eder (ne yapıyoruz, yetkinlikler, önceki işler, sektör); aradığı ortak ve iş birliği türü benzerlik metnine girmez. `versiyon` hazırlamanın tekrar korumasıdır; `oturum_id` UNIQUE, aynı sohbetin ikinci onayı mevcut kartı döner. Kurallar `app/core/firma_karti.py`.
- **`ESLESME` → `ISBIRLIGI` ilişkisi isteğe bağlı (0 veya 1).** Her eşleşme iş birliğine dönüşmez — kurum "ilgileniyorum" der, iş birliği ancak genç kabul edince (`kabul_edildi`) açılır (docs/faz-b-kimlik-ve-dongu.md § 5).
- **`CANLILIK_OLAYI` doğrudan `ESLESME`'ye bağlı, `ISBIRLIGI`'na değil.** Pasiflik takibi bir iş birliği resmen başlamadan da çalışabilmeli — örn. "eşleşme önerildi ama kimse tıklamadı" durumu.
- **`kanit_bekleyen` (YETENEK_KARTI) ve `durum` (REFERANS_ISTEGI, ESLESME, ISBIRLIGI) alanları state machine mantığıyla çalışıyor.** Örn. `REFERANS_ISTEGI.durum`: `bekliyor` → `yanitlandi` veya `yanit_yok` (zaman aşımı, ceza değil nötr durum). `yanitlandi`, referansın yanıt verdiğini söyler — olumlu bulduğunu değil; olumsuz bir referans da bu durumda olur, değerlendirme `GUVEN_SKORU.ucuncu_taraf_onayi` puanında taşınır.
- **`embedding` (YETENEK_KARTI, IHTIYAC_KARTI), pgvector kolonu.** Kart onaylandığında/güncellendiğinde yeniden hesaplanır. **Sağlayıcı: Voyage AI (voyage-4, 1024 boyut)** — Anthropic'in Claude ile kullanım için resmi önerisi; ilk 200M token ücretsiz. `EMBEDDING_DIM = 1024` olarak sabitlenir (bkz. `matching-algorithm.md`).
- **`sehir_tercihi` ve `musaitlik_tercihi` (IHTIYAC_KARTI), nullable.** Eşleştirme'nin sert filtre adımı SQL üzerinden çalışabilsin diye — serbest metin `kisitlar` alanı bu amaçla sorgulanamaz. `IHTIYAC_KARTI.sehir_tercihi` ile `KURUM.sehir` farklı şeyler: ilki gencin nerede olması istendiği (filtre), ikincisi kurumun kendi yeri (filtre değil). Arayüzde "aranan şehir" ve "kurumun şehri" olarak ayrı ayrı soruluyor; tercih boşsa kurumun şehri varsayılan geliyor.
- **`calisma_modelleri` (KULLANICI, çoklu) ve `calisma_modeli` (IHTIYAC_KARTI, tekli).** Değerler: `is_yerinde | hibrit | uzaktan`. Konumdan ayrı bir alan — önce şehir listesine "Uzaktan / fark etmez" diye bir seçenek konmuştu, ama bu "İstanbul'da ama hibrit" gibi çok sık bir durumu ifade edilemez kılıyordu; LinkedIn ve Kariyer.net de ikisini ayrı tutuyor. **Müsaitlikle karıştırma:** müsaitlik çalışma tipidir (tam/yarı zamanlı, proje bazlı, staj), bu ise çalışma yeri. Eşleştirme filtresi: ihtiyaç `uzaktan` ise şehir filtresi uygulanmaz ve gencin `uzaktan`ı kabul etmesi yeter; `is_yerinde`/`hibrit` ise hem şehir eşleşir hem genç o modeli kabul etmiş olmalıdır. Modelini hiç belirtmemiş kart elenmez (bilinmeyeni "hayır" saymak sessiz eleme olurdu). Eski `sehir = 'uzaktan'` kayıtları `0e3cd1cd3fdf` migration'ıyla yeni alana taşındı.
- **Müsaitlik kod olarak saklanıyor** (`KULLANICI.musaitlikler`, `IHTIYAC_KARTI.musaitlik_tercihi`; `app/core/musaitlik.py`): `tam_zamanli | yarim_zamanli | proje_bazli | staj`. Eşleştirme filtresi düz eşitlik yaptığı için Tanımlama Ajanı'nın serbest metni ("tam zamanlı") tüm adayları sessizce eliyordu — şehirdeki hatanın aynısı. Ajanın çıkarım şeması `Literal`; istemciden gelen onay katı okunur (tanınmayan değer 422), checkpoint'ten okunan eski taslak hoşgörülü okunur (tanınmayan değer NULL). Eski satırlar `7c3a9e51b8d4` migration'ıyla koda çevrildi, tanınmayan NULL oldu (filtre uygulanmaz, eleme olmaz). **Gencin tarafı çoklu seçim** (`musaitlikler text[]`, `76b95c6a1658`; tekil değer tek elemanlı listeye taşındı): ihtiyaç tek tercih taşır, filtre "tercih gencin listesinde mi" diye sorar; liste boşsa genç elenmez (çalışma modelindeki kural; eskiden müsaitliği boş genç, tercihi olan ihtiyaçta eleniyordu). Kural `musaitlik_uyar_mi`.
- **Şehir adları kanonik yazımda saklanıyor** (`app/core/sehir.py`, 81 il + `uzaktan`). Sebep: filtre düz string karşılaştırması ve Türkçe'de `'istanbul' = 'İstanbul'` false — `lower()` ve `ILIKE` de çözmüyor (Postgres bu collation'da İ'yi küçültmüyor, Python'ın `lower()`'ı ise i + U+0307 üretiyor). Kayıt anında `sehir_kanonik()` uygulanıyor, eski satırlar `a1c4f7e2b903` migration'ıyla düzeltildi. Liste yalnızca il adlarından oluşur; "uzaktan" bir şehir değil, çalışma modelidir.
- **`sektor_ilgi_alani`, `araclar_teknolojiler` (YETENEK_KARTI), `aciklama` (SOMUT_CIKTI), `token` (REFERANS_ISTEGI).** Faz 1'de backend iskeletini yazarken Claude Code'un dokümanlar arası çapraz kontrolde yakaladığı eksiklerdi — diğer dosyalar (`agent-specs.md`, `matching-algorithm.md`, `api-contracts.md`) bu alanlara referans veriyordu ama ER diyagramında yoktu. Buradan eklendi.
- **`email` (KULLANICI) ve `iletisim_email` (KURUM), UNIQUE ve normalize (`lower(trim)`).** Onay anında kayıt bu alanla tek bir `INSERT … ON CONFLICT DO UPDATE` ile yazılıyor: yarışa dayanıklı, kayıtlı kişinin yeni verdiği bilgi güncelleniyor. Boş gelen alan kayıtlı değeri silmiyor (skalerlerde `COALESCE`, `calisma_modelleri` boşsa eskisi kalıyor) — taslak birleştirmedeki kuralın aynısı. Eski mükerrerler `cb9a542b6431` migration'ıyla birleştirildi (kartlar en küçük `id`'li kayda taşındı). Bu "e-postayla bul" mantığı Faz B'de hesaba bağlanınca kalkacak.
- **`iletisim_email` (KURUM).** `KULLANICI.email`'in kurum karşılığı — Keşif Ajanı'nda kart onaylanırken email üzerinden `Kullanici` bulunup/oluşturuluyordu, Tanımlama Ajanı'nda `Kurum` için aynı mekanizma gerekiyor. Tanımlama Ajanı'nın backend'i yazılırken fark edildi.
- **`puan` (REFERANS_ISTEGI) ve çok referanslı hesap.** Referansın 1-5 puanı kaydediliyor, çünkü `GUVEN_SKORU.ucuncu_taraf_onayi` tek bir yanıttan değil, **yanıtlamış tüm referansların ortalamasından** hesaplanıyor (1-5 → 0-3 çevrimi sonrası, 0.5 yukarı yuvarlanarak). En yüksek puanı almak "olumlu diyen birini bulana kadar referans sor" davranışını ödüllendirirdi; ortalama, zayıf bir referansın puanı aşağı çekmesine izin verir. Yuvarlama aşağı değil normal: aşağı yuvarlamada iki güçlü referans (5+4 → 2.5 → 2) tek bir 5'ten (3) düşük puan alıyordu — referans eklemek iddiayı zayıflatmamalı. Puan saklanmadan bu hesap yapılamıyordu — son yanıt öncekinin üzerine yazıyordu. Doğrulama Ajanı denenirken fark edildi.
- **`olusturma_tarihi` (REFERANS_ISTEGI).** Zaman aşımı dalı (`bekliyor` → `yanit_yok`, 5-7 gün) bir tarih olmadan hesaplanamıyordu. Ayrı bir zamanlayıcı kurulmadığı için bu geçiş okuma anında hesaplanıyor; alan onun dayanağı. Doğrulama Ajanı yazılırken eklendi.
- **`oturum_id` (YETENEK_KARTI, IHTIYAC_KARTI), nullable + UNIQUE.** Kartı doğuran sohbetin kimliği. Onay tekrarlanabilir olsun diye: aynı sohbet ikinci kez onaylanınca (çift tıklama, embedding hatası sonrası yeniden deneme) yeni kart açılmaz, mevcut kart döner. Eşzamanlı iki onayda ikincisi UNIQUE kısıta takılır ve mevcut kartı alır. Faz A'da inceleme bulgusu olarak eklendi.
- **`(ihtiyac_karti_id, yetenek_karti_id)` (ESLESME), UNIQUE.** Bir çift için tek eşleşme. Arka plan eşleştirmesi ile öneri okuması aynı anda çalışınca mükerrer satır açılıyordu; pipeline artık ihtiyaç kartı başına advisory lock ile sıraya giriyor, yeni satırlar `ON CONFLICT DO NOTHING` ile yazılıyor.
- **`olusturma_tarihi` (IHTIYAC_KARTI).** Eşleştirme Ajanı "kurumun en son ihtiyaç kartı"nı bulmak için `id` sırasına bakıyordu — ama `id` rastgele üretilen bir UUID (v4), zaman bilgisi taşımıyor, sıralaması kronolojik değil. Eşleştirme Ajanı yazılırken fark edildi, gerçek bir tarih alanıyla düzeltiliyor.
