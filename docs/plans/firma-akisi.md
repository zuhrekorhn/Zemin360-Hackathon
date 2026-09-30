# Firma akışı: kayıt, firma kartı, iki kapı, firma–firma eşleşme, doğrulama, ilan kapatma

> Durum: **onaylandı** (29 Eyl). Kararlar 1-20 onaylı; dondurma tarihi bu görev için kayabilir (§ 13). Kod, onaydan sonra § 12'deki sırayla,
> adım başına commit ve testle yazılır. Kullanıcı metinleri
> [`../icerik-rehberi.md`](../icerik-rehberi.md)'ye uyar; yeni metinler
> `firma-akisi-metinler.md`'ye yazılır.

## 0. Kararlar

### Sorularla netleşenler (29 Eyl)

| # | Konu | Karar |
|---|---|---|
| 1 | Firma türü | Kayıtta seçilir: **Girişim, KOBİ, Kurumsal**. Profilden değiştirilebilir. |
| 2 | Kayıt formu | **Zorunlu:** firma adı, tür, sektör, şehir, KVKK onayı. **İsteğe bağlı:** web sitesi, çalışan sayısı aralığı (1-10 / 11-50 / 51-250 / 250+), kuruluş yılı, 1-2 cümle tanıtım, formu dolduranın adı ve görevi. Formdaki bilgi sohbette tekrar sorulmaz. |
| 3 | Firma kartı | **Sohbetle** oluşur (mevcut sohbet motoru, yeni bir `AjanTanimi`), firma onaylar. Sonra formla düzenlenebilir. |
| 4 | Ortak arama | **Belirli bir iş için:** firma ihtiyaç sohbetinde "iş birliği ortağı"nı seçer, sohbet bir ilan (ihtiyaç kartı) çıkarır, ilana uyan firmalar önerilir. Genç aramayla aynı yol. |
| 5 | Eşleşme şartları | **Kesin:** aranan firma türü (ilan sahibi birini ya da birkaçını seçer; boşsa hepsi), kendi firması önerilmez, kapalı ilan öneri almaz. **Şehir:** varsayılan "fark etmez", ilan sahibi şart koyabilir. **Sektör şart değil.** **Sıralama:** konuya uyum; doğrulanmış firma ve tamamlanan iş birlikleri biraz öne çıkarır. |
| 6 | Firma doğrulaması | Sistem **ipucu** verir (kayıt e-postasının alan adı web sitesininkiyle aynı mı; siteye bağlanılmaz, yalnızca iki yazı karşılaştırılır). **GİRVAK onaylar** ("Onayla" / "Şimdilik değil"). Doğrulanmamış firma da her şeyi kullanır; yalnızca "Doğrulanmış firma" işareti olmaz. |
| 7 | İlan kapatma | Kapatırken neden sorulur: "Platformda bulduk", "Başka yoldan bulduk", "Vazgeçtik". Neden yalnızca GİRVAK'a görünür; karşı taraf "fırsat kapandı" görür. **Kapanan ilan tekrar açılmaz**; firma yeni ilan açar. Genç ve ortak ilanlarında aynı düğme. |
| 8 | Firmalar arası ilgi | **İki yönlü**, genç tarafıyla aynı: ilan sahibi önerilen firmaya ilgi gösterebilir; önerilen firma da "Size uygun iş birliği fırsatları"nda ilanı görüp ilgi gösterebilir (açık iletişim onayıyla). İkisi de ilgilenince e-postalar paylaşılır, iş birliği ve takip başlar. |
| 9 | Kayıttan sonra | **İki kapılı ana sayfa**: "Genç yetenek bul" ve "İş birliği ortağı bul". Kart isteğe bağlı; kartı olmayan firma ortak olarak önerilmez, ana sayfada "Firma kartınızı oluşturun" bandı. Eski firma hesaplarına engellemeyen "Profilinizi tamamlayın" bandı; demo verisi doldurulur. |

### Onayına sunulan tasarım kararları

Bunlar soruların doğal sonucu olarak benim önerim; itiraz etmezsen böyle yapılır.

| # | Konu | Öneri | Neden |
|---|---|---|---|
| 10 | Firma kartının tablosu | Yeni tablo `firma_karti` (firma başına bir kart, `versiyon`'lu). Yetenek kartı genişletilmez. | Yetenek kartının alanları (rol, deneyim seviyesi, çalışmalar, güven göstergesi rubriği) gence özel; zorlamak iki tarafı da bozar. **Paylaşılan kısım aynen kullanılır:** eşleşme tablosu, pipeline, ilgi durum makinesi, iş birliği, takip, bildirimler. Paralel bir eşleştirme ya da ilgi sistemi kurulmaz. |
| 11 | Eşleşme tablosu | `eslesme.yetenek_karti_id` nullable olur, yanına nullable `firma_karti_id` gelir; **tam biri dolu** (CHECK). Ayrı UNIQUE `(ihtiyac_karti_id, firma_karti_id)`. Hangisinin dolacağını ilanın `aranan` alanı (`genc` \| `firma`) belirler. | Bir satır, bir durum makinesi, bir iş birliği ilişkisi. |
| 12 | Taraf kavramı | Durum makinesindeki `genc` / `kurum` rolleri **"aday tarafı" / "ilan tarafı"** anlamına genişler. Firma–firma'da aday firma, makinede aday tarafının geçişlerini yapar (ilgi, geri çekme, kabul/ret). Kolon adları (`genc_ilgi_tarihi`, `genc_plan_onayi`, `genc_isaret`, `baslatan='genc'`) **değişmez**, belgede "aday tarafı" diye tanımlanır. Rol kontrolü hesabın rolünden değil, eşleşmedeki tarafından yapılır: `sahiplik.py` › `taraf(hesap, eslesme)`. | Kolon yeniden adlandırma migration'ı ve 100'e yakın dokunuş yarım gün ek iş ve regresyon riski getirir; dondurmaya 4 gün var. Alternatif (yeniden adlandırma) dondurma sonrası temizlik olarak listelenir. |
| 13 | Firma–firma skoru | Aynı formül ve aynı iki sınır: `0.75 × benzerlik + 0.25 × bonus`, benzerlik alt sınırı 0.45, skor eşiği %40, ilk 5. Bonus: doğrulanmış firma +0.5, en az bir tamamlanan iş birliği +0.5, tavan 1.0. | `matching-algorithm.md` § 4-5 ile tutarlı. Firma metinleri için 0.45'in ayarı ölçülmedi; bilinen sınır olarak yazılır. |
| 14 | Gerekçe | Firma adayı için ayrı gerekçe istemi ("Neden uygun?", ilan sahibine "siz"). | Genç istemi yetenek kartı alanlarına bakıyor. |
| 15 | Kartın güncel tutulması | Firma kartı onaylanınca ve düzenlenince arka planda embedding + ilgili açık **ortak ilanlarıyla** yeniden eşleştirme (`kart_hazirlama.py` deseni). Firma kartı düzenlenince firma doğrulaması sıfırlanmaz; **web sitesi ya da iletişim e-postası değişirse** doğrulama "bekliyor"a döner. | Sonradan gelen firma da mevcut ilanlarla eşleşsin. Doğrulama kartla değil, kimlikle ilgili. |
| 16 | Görünürlük | Aday firma, kendisine önerilen ilanın firma adını, problemini ve başarı kriterini görür (gençteki karar 1'in aynısı). Firma kartını yalnızca sahibi, ona önerilmiş ilanların sahibi ve GİRVAK görür; **genç firma kartını görmez**. E-postalar yalnızca `kabul_edildi`'de, iki tarafa. | Mevcut sahiplik sözleşmesi (404 başkasının kaynağı). |
| 17 | "Doğrulanmış firma" işareti | Firma adının geçtiği her yerde: gencin fırsatları, aday firma listesi, ilgilerim, iş birliği sayfası. | Soru 6'nın amacı. |
| 18 | Canlılık | Firma–firma eşleşmeleri **bu görevde taranmaz** (sorgu `yetenek_karti_id IS NOT NULL` ile süzülür, çökme olmasın). Dondurma sonrasına "S" olarak yazılır. | Hatırlatma alıcısı ve metinleri gence göre kurulu; kişiselleştirme istemi "sen" diyor (metin denetimi maddesi). Zaman. |
| 19 | GİRVAK sayıları | Eşleşme ve iş birliği sayıları **toplamda firma–firma'yı da sayar**, altında kırılım: "genç–firma" / "firma–firma". Ek satırlar: onay bekleyen firmalar, kapanan ilanlar ve nedenleri. | Programın asıl hedefi firma–firma iş birliği. |
| 20 | Demo verisi | Mevcut demo firması (Moda Dayanışma Kooperatifi) KOBİ olarak doldurulur. İki yeni demo firma: bir **girişim** (kartlı, doğrulanmış) ve bir **kurumsal** (ortak ilanı açık). | Ortak arama demoda gösterilebilsin. |

## 1. Bugünkü durum

- `kurum`: ad, sektör, şehir, iletişim e-postası. Tür, web sitesi, doğrulama yok.
- Firmanın kendi kartı yok; firmalar yalnızca ilan sahibi.
- İhtiyaç sohbeti (Tanımlama) → ihtiyaç kartı → gençler önerilir; ilgi iki yönlü, karşılıklı ilgi, iş birliği ve takip çalışıyor.
- `ihtiyac_karti.durum` ve `ihtiyaci_kapat` servisi hazır; uç ve düğme yok.
- Eşleşme satırı her zaman bir yetenek kartına bağlı; ~100 yerde `eslesme.yetenek_karti` okunuyor.

## 2. Veri modeli (migration'lar eklemeli; eski satırlar değişmez)

**`kurum`** (eklenen alanlar)

| Alan | Tür | Not |
|---|---|---|
| `tur` | `girisim \| kobi \| kurumsal`, nullable | Eski hesaplarda boş → bant |
| `web_sitesi` | text, nullable | Normalize edilir (şema, `www.` ve sondaki `/` atılır) |
| `calisan_araligi` | `1-10 \| 11-50 \| 51-250 \| 250+`, nullable | |
| `kurulus_yili` | int, nullable | 1900..bu yıl |
| `tanitim` | text, nullable | En çok 300 karakter |
| `yetkili_ad`, `yetkili_gorev` | text, nullable | |
| `dogrulama_durumu` | `bekliyor \| dogrulandi \| simdilik_degil`, varsayılan `bekliyor` | |
| `dogrulama_tarihi` | timestamptz, nullable | GİRVAK'ın kararı |

KVKK onayı mevcut `hesap.kvkk_onay_tarihi`'nde. Alan adı ipucu **saklanmaz**, okuma anında hesaplanır (`app/core/alan_adi.py`, saf; ücretsiz e-posta sağlayıcıları listesiyle).

**`firma_karti`** (yeni)

| Alan | Tür | Not |
|---|---|---|
| `kurum_id` | FK, UNIQUE | Firma başına bir kart |
| `ne_yapiyoruz` | text | Ürün ya da hizmet (zorunlu) |
| `yetkinlikler` | text[] | Güçlü olunan alanlar (zorunlu, en az 1) |
| `onceki_isler` | text, nullable | Yapılan işler, müşteri türleri |
| `aranan_isbirligi` | text, nullable | Ne tür ortak arıyor |
| `isbirligi_turleri` | text[] | `pilot \| tedarik \| ortak_urun \| yatirim \| diger`, isteğe bağlı |
| `embedding`, `versiyon`, `oturum_id` UNIQUE, `olusturma_tarihi` | | Yetenek kartındaki desen |

**`ihtiyac_karti`** (eklenen alanlar)

| Alan | Not |
|---|---|
| `aranan` | `genc \| firma`, varsayılan `genc` (eski satırlar genç ilanı) |
| `aranan_firma_turleri` | text[], boş = hepsi; yalnızca `aranan = firma` |
| `isbirligi_turu` | yalnızca ortak ilanında, isteğe bağlı |
| `kapanma_nedeni` | `platformda_bulundu \| baska_yoldan_bulundu \| vazgecildi`, nullable |
| `kapanma_tarihi` | nullable |

**`eslesme`**: § 0, karar 11.

## 3. Taraflar ve durum makinesi (karar 12)

- `gecis()` ve `GECISLER` tablosu **değişmez**. Değişen, rolün nereden geldiği: `sahiplik.taraf(hesap, eslesme) → "genc" | "kurum" | None`. Aday tarafı: yetenek kartının genci ya da aday firma kartının firması. İlan tarafı: ilanın firması.
- Genç uçları (`/genc-ilgi`, `/ilgiyi-geri-cek`, kabul/ret) ve firma uçları (`/ilgileniyorum`, `/simdilik-degil`) bugün `rol_gerekli(...)` ile hesabın rolüne bakıyor. Firma–firma için:
  - **aday firma uçları** ayrı ve ince: `POST /eslestirme/{id}/firma-ilgi`, `.../firma-ilgiyi-geri-cek`, `.../firma-kabul`, `.../firma-red`. Aynı servisi çağırırlar, `rol_gerekli(ROL_KURUM)` + `taraf == aday`.
  - ilan tarafı uçları aynı kalır, yalnızca sahiplik kontrolü `taraf`'a geçer.
- Firma aynı eşleşmede iki tarafta olamaz (kendi firması önerilmez); `taraf` bunu varsayar ve testle sabitlenir.
- İletişim (`iletisim`): firma–firma'da `aday_email` = aday firmanın `iletisim_email`'i. Şema: mevcut `genc_email` alanı yanına `aday_firma_email` eklenir (genç ekranları değişmez).

## 4. Eşleştirme

- `pipeline_calistir` tek kalır; ilk satırda `ihtiyac.aranan`'a göre aday kaynağı seçilir: `adaylari_getir` (bugünkü) ya da `firma_adaylarini_getir` (yeni). Kilit, temizleme, karar 14 koruması, ON CONFLICT, gerekçe paralelliği, bildirim **aynı kod**. Farklı olan: aday kimliği (`yetenek_karti_id` / `firma_karti_id`) ve gerekçe istemi. Bunlar küçük bir "aday türü" tanımında toplanır (`app/agents/eslestirme.py`).
- **Firma adayı SQL filtresi:** `firma_karti.embedding IS NOT NULL`, `kurum.id != ilan.kurum_id`, `aranan_firma_turleri` boş değilse `kurum.tur = ANY(...)`, ilanda şehir varsa `kurum.sehir` eşit (kanonik). Sonra benzerlik alt sınırı, skor, eşik, ilk 5 (karar 13).
- **Firma kartı hazırlama** (`app/servisler/firma_karti_hazirlama.py`): onay ve düzenlemede embedding, sonra açık ortak ilanlarından benzerlik alt sınırını geçenler için pipeline (genç tarafındaki `ilgili_ihtiyac_kartlari` deseni). `tests/conftest.py`'ye sahtesi eklenir.
- Aday firmaya bildirim: yeni fırsat için ayrı bildirim yok (gençte de yok); firma ana sayfasında görür.

## 5. Sohbetler

**Firma kartı sohbeti** (yeni `AjanTanimi`, `app/agents/firma_karti.py`; belgede Keşif'in firma soru seti olarak geçer)
- Kayıt formundaki bilgiler (ad, tür, sektör, şehir, tanıtım, web sitesi) sohbetin başında bağlam olarak gider, sorulmaz (`profil_baglami` deseni).
- Zorunlu alanlar: `ne_yapiyoruz`, `yetkinlikler`. İsteğe bağlı: `onceki_isler`, `aranan_isbirligi`, `isbirligi_turleri`. Zorunlu tur tavanı 2, Tanımlama gibi.
- Açılış (firmaya "siz"): "Firmanızın ne yaptığını birkaç cümleyle anlatın: hangi ürünü ya da hizmeti sunuyorsunuz, kimler için?" Sohbet başında rehberdeki "yapay zekâ desteğiyle ilerler" notu.
- Onay → `firma_karti` yazılır (aynı `oturum_id` ikinci kez onaylanınca mevcut kart döner), hazırlama arka planda.
- Düzenleme: `/kurum/kart` sayfasında form; `versiyon` kontrolü (409), içerik değişince yeniden hazırlama.

**Ortak ilanı** (Tanımlama'nın ikinci tanımı, aynı motor)
- Kapı seçimi sohbetten önce: `/tanimlama?aranan=firma`. `sohbet/baslat` isteğe `aranan` alır, oturum durumuna yazılır, onay bunu karta taşır.
- Soru seti: problem, ölçülebilir başarı kriteri, iş birliği türü, aranan firma türleri (sohbette sorulur, formda düzeltilir), şehir şartı var mı. Çalışma modeli ve müsaitlik sorulmaz.
- Firma profili (tür, sektör, şehir) bağlam olarak gider.

## 6. Firma doğrulaması

- `app/core/alan_adi.py` (saf): `alan_adi_ipucu(eposta, web_sitesi) → "uyusuyor" | "uyusmuyor" | "ucretsiz_eposta" | "site_yok"`. `www.` ve alt alan adı toleransı (`ik.marketx.com` ↔ `marketx.com` uyuşur). Ağ isteği yok.
- GİRVAK: `GET /girvak/firmalar?durum=bekliyor` (ad, tür, sektör, site, ipucu, kayıt tarihi), `POST /girvak/firmalar/{id}/dogrula` gövde `{karar: "dogrulandi" | "simdilik_degil"}`. Tekrar 200 ve yan etkisiz. Firmaya bildirim: onaylanınca "Firmanız doğrulandı. Adınızın yanında artık “Doğrulanmış firma” işareti görünüyor." "Şimdilik değil"de bildirim yok (olumsuz haber nazik; firma profilinde "Doğrulama bekleniyor" görmeye devam eder).
- Profil yanıtı `dogrulandi: bool` döner; `dogrulama_durumu`'nun kendisi yalnızca GİRVAK'a.

## 7. İlan kapatma

- `POST /ihtiyac-kartlari/{id}/kapat` gövde `{neden}`; sahibi değilse 404, zaten kapalıysa 200 yan etkisiz. Mevcut `ihtiyaci_kapat` servisini çağırır (bekleyenler `kapandi`, bildirim "… tarafındaki fırsat kapandı."), neden ve tarih yazılır.
- Arayüz: ilan satırında "İhtiyacı kapat" → sayfa içi onay alanı (tarayıcı penceresi değil): üç neden, "Kapat" / "Vazgeç". Kapalı ilan "Kapandı" etiketiyle listenin altına iner.

## 8. Arayüz

| Sayfa | İçerik |
|---|---|
| `/kayit` (firma) | Karar 2'deki form, KVKK kutusu; kayıttan sonra `/kurum` |
| `/kurum` | Üstte iki kapı ("Genç yetenek bul" → `/tanimlama`, "İş birliği ortağı bul" → `/tanimlama?aranan=firma`); kart yoksa bant; eski hesapta profil bandı; "İlanlarınız" (genç / ortak etiketiyle, kapat düğmesi); **"Size uygun iş birliği fırsatları"** (aday firma olarak), **"İlgilerimiz"**; iş birlikleri |
| `/kurum/profil` | Profil düzenleme (tür, site, çalışan aralığı…), doğrulama durumu satırı |
| `/kurum/kart` | Kart yoksa sohbet, varsa kart ve "Kartı düzenle" formu |
| `/kurum/oneriler` | Aday firmalar için aynı sayfa: kart özeti, "Doğrulanmış firma" işareti, "Neden uygun?", "İlgileniyorum" / "Şimdilik değil", ilgi gösterenler üstte |
| `/isbirligi/[id]` | Taraf adları iki firma; takip aynen |
| `/girvak` | "Onay bekleyen firmalar" (ipucu ile, iki düğme), kırılımlı sayılar, kapanan ilanlar |

Yeni frontend mantığı saf `src/lib/*.ts` fonksiyonlarında ve Vitest'le (yeni bağımlılık yok).

## 9. İş birliği ve takip

- `isbirligini_ac` değişmez. Takip uçlarındaki "genç mi kurum mu" kontrolü `taraf`'a geçer; `genc_plan_onayi` / `genc_isaret` aday tarafının alanıdır (karar 12).
- Plan önerisi istemi "genç" diyorsa firma–firma için tarafsız metin ("aday taraf") kullanılır.
- Tamamlanan firma–firma iş birliği, aday firmanın bonusuna girer (karar 13).

## 10. Sahiplik ve hata sözleşmesi

Her yeni uç için 401 / 403 / 404 üçlüsü ve 409 (geçersiz geçiş, sürüm çakışması, kapalı ilan) testlenir, `tests/test_sahiplik.py` dünyasına iki firma kartı ve bir ortak ilanı eklenerek. Özellikle:
- aday firma başka firmanın eşleşmesine ilgi gösteremez (404);
- ilan sahibi aday uçlarını, aday firma ilan sahibi uçlarını çağıramaz (409 değil 404 — taraf değilse kaynak yok sayılır; tarafsa ama yanlış olaysa 409);
- genç firma kartını ve ortak ilanlarını göremez (404);
- GİRVAK doğrulama uçları dışında yazamaz.

## 11. Testler

- **Saf:** `alan_adi_ipucu`, firma türü filtresi, bonus formülü, `taraf`, kapatma nedeni doğrulaması, profil eksikleri, frontend lib'leri.
- **Gerçek veritabanı:** migration'ın eski satırlara dokunmadığı; firma adayı SQL'i (tür, şehir, kendi firması); pipeline'ın ortak ilanında karar 14 korumasını koruduğu; firma–firma karşılıklı ilgide iş birliğinin açıldığı ve e-postaların yalnızca iki tarafa döndüğü; kapatmanın bekleyenleri kapattığı; firma kartı düzenlemesinde doğrulamanın yalnızca site/e-posta değişince sıfırlandığı.
- **Regresyon:** mevcut 1119 backend ve 71 frontend testi her adımda.

## 12. Adımlar

Her adım ayrı commit; testler geçmeden commit yok; her adım sonunda kısa durum.

| # | Adım | Tahmini süre |
|---|---|---|
| 1 | **Taraf kavramı** (davranış değişmez): `sahiplik.taraf`, genç ve firma uçlarında rol yerine taraf kontrolü, `eslesme` üzerinden okunan yerlerin yardımcıya toplanması | 0,5 gün |
| 2 | **Kayıt ve profil:** `kurum` alanları + migration, kayıt formu, `/kurum/profil`, eski hesap bandı | 0,5 gün |
| 3 | **İlan kapatma:** uç, neden alanları, sayfa içi onay, GİRVAK satırı | 0,25 gün |
| 4 | **Firma doğrulaması:** `alan_adi_ipucu`, GİRVAK listesi ve kararı, işaret, bildirim | 0,5 gün |
| 5 | **Firma kartı:** tablo, sohbet tanımı, onay, `/kurum/kart`, düzenleme formu, hazırlama | 1 gün |
| 6 | **Ortak ilanı:** `ihtiyac_karti.aranan` alanları, Tanımlama'nın ikinci tanımı, iki kapı | 0,5 gün |
| 7 | **Firma–firma eşleştirme:** `eslesme` kolonları + CHECK, aday türü, firma adayı SQL'i, gerekçe istemi, öneriler sayfası | 0,75 gün |
| 8 | **Firmalar arası ilgi ve iş birliği:** aday firma uçları, "Size uygun iş birliği fırsatları", "İlgilerimiz", iletişim, takip, bonus | 1 gün |
| 9 | **GİRVAK sayıları, Canlılık süzgeci, demo verisi** | 0,5 gün |
| 10 | **Belgeler ve deneme senaryosu** (`firma-akisi-deneme.md`), kapanış | 0,5 gün |

**Toplam ≈ 6 gün; özellik dondurmaya (3 Eki akşamı) ≈ 4,5 gün var.** Plan bu hâliyle takvime sığmıyor.

## 13. Takvim ve kesim çizgisi

**Karar (29 Eyl):** Plan kesilmeden uygulanır; özellik dondurma tarihi bu görev için kayabilir. Aşağıdaki kesim sırası yalnızca yeni bir takvim sıkışmasında kullanılır.

Sıra, en değerli ve en az riskli parçalar önce bitsin diye böyle. Kayma olursa kesim şu sırayla (önce kesilen önce):

1. **Firma kartı sohbeti → form** (adım 5'te ~0,5 gün kazanç). Kart önce formla açılır, sohbet dondurma sonrasına kalır (Soru 3'teki C seçeneği).
2. **Aday firmanın ilk ilgiyi göstermesi** (adım 8'de ~0,5 gün): yalnızca ilan sahibi ilgi gösterir, aday firma kabul/ret eder. Durum makinesi zaten iki yolu da destekliyor; kesilen yalnızca "fırsatlar" bölümü ve uçlar.
3. **GİRVAK kırılımları** (sayılar toplamda kalır).

**Asla kesilmez:** kayıt ve profil, ilan kapatma, firma doğrulaması, ortak ilanı → firma önerisi → karşılıklı ilgi → iş birliği.

## 14. Kapsam dışı

- Firma–firma için Canlılık hatırlatmaları (karar 18).
- Kolonların "aday/ilan" adıyla yeniden adlandırılması (karar 12).
- Web sitesine bağlanarak doğrulama, vergi numarası, ticaret sicili.
- SSRF engeli: sıradaki ayrı görev.
- Toplu metin denetimi: ayrı adım; yeni metinler ise baştan rehbere uygun yazılır.

## 15. Kapanış (30 Eyl)

**Uygulandı:** adımlar 1-10, kararlar 1-20. Elle tarayıcı denemesi yapılmadı (senaryo: [`firma-akisi-deneme.md`](firma-akisi-deneme.md)).

| Adım | Commit | Özet |
|---|---|---|
| — | `7d8e32d`, `81f37ef` | Commit kuralı `CLAUDE.md`'de; plan onaylı |
| 1 | `d260083` | Taraf kavramı: durum geçişi hesabın rolünden değil eşleşmedeki taraftan (davranış değişmedi) |
| 2 | `47349ee` | Kayıt formu ve profil (tür, sektör, şehir, KVKK; isteğe bağlı alanlar), `/kurum/profil`, eski hesaplara bant |
| 3 | `95ab16b` | İlan kapatma: nedenli, sayfa içi onay, GİRVAK sayısı; pipeline kilitten sonra durumu yeniden okur |
| 4 | `eaa56c8` | Firma doğrulaması: alan adı ipucu (ağ isteği yok), GİRVAK onayı, "Doğrulanmış firma" işareti |
| 5 | `e944587`, `f590894` | Firma kartı: tablo, okuma/düzenleme, aynı motorla sohbet, `/kurum/kart` |
| 6 | `0b8a5b5` | Ortak ilanı ve iki kapı (`ihtiyac_karti.aranan`, Tanımlama'nın ikinci soru seti) |
| 7 | `7578d9f`, `a786033` | Firma–firma eşleştirme: aynı tablo ve pipeline, firma adayları, bonus, ayrı gerekçe; öneriler sayfası |
| 8 | `e585de6`, `be5be26`, `bd92951` | Firmalar arası ilgi (iki yönlü), iş birliği ve takip, firma panelinde fırsatlar/ilgiler |
| 9-10 | (bu kapanışla) | GİRVAK kırılımı, demo firmaları; belgeler, deneme senaryosu |

**Plandan sapmalar:**
- Firma kartı düzenlemesinde "versiyon çakışmasında 409" yerine genç kartındaki gibi satır kilidi (iki düzenleme sırayla işlenir).
- Canlılık süzgeci 9. adım yerine 7. adımda geldi (ilk firma eşleşmesinde tarama çökmesin diye).
- İş birliği görünümü (`/isbirligi/{id}`, `/isbirliklerim`) iki tarafa tek bir alan dışında aynı: `tarafim`. Ortak firmanın rolü de "kurum" olduğu için arayüz tarafı rolden okuyamıyordu.
- İletişim yanıtına `aday_firma_email` eklendi (genç eşleşmesinde boş); mevcut alanlar değişmedi.

**Bilinen sınırlar:**
- 0.45 benzerlik alt sınırı firma metinleri için ölçülmedi.
- Firma profili (tür, şehir, doğrulama) değişince mevcut öneriler kendiliğinden yeniden hesaplanmaz; "Yeniden hesapla" ya da bir sonraki pipeline çalışması günceller.
- Canlılık firma–firma eşleşmelerini taramaz (karar 18).
- "Neden uygun?" metni ilanı açan firmaya hitaben yazılıyor ve aday firma da aynısını görüyor (genç tarafındaki sınırın aynısı).
- Kolon adları "genç" diyor ama "aday tarafı" anlamında (karar 12): `genc_ilgi_tarihi`, `genc_plan_onayi`, `baslatan='genc'`.
- Tamamlanan iş birliği bonusu yalnızca firmanın **aday** olarak tamamladıklarını sayar; ilan sahibi olarak tamamladıkları sayılmaz.

**Açık işler** (D = deploy öncesi, T = teslim/demo öncesi, S = sonra):

| İş | Öncelik |
|---|---|
| SSRF engeli (kanıt linki kontrolü) | **D**, sıradaki görev |
| Elle tarayıcı denemesi (genç + firma senaryoları) | **T** |
| Toplu metin denetimi (`genc-akisi-metinler.md`, `firma-akisi-metinler.md`; rehbere aday firma sütunu) | **T** |
| Kolonları "aday/ilan" adıyla yeniden adlandırma | **S** |
| Firma–firma için Canlılık hatırlatmaları | **S** |
| Firma profili değişince önerilerin yeniden hesabı | **S** |
| Firma kartı için "sohbetle yeniden doldur"; web sitesi ya da ticaret sicili ile doğrulama | **S** |
