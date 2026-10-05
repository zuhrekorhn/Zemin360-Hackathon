# Zemin360 İçerik Rehberi

> Durum: **Onaylandı (28 Eylül 2026).** Karar veren: Zühre Nur Korhan. Alınan terim kararları § 9'da.
>
> Kullanım: Arayüzde kullanıcıya görünen **her** metin bu rehbere göre yazılır: sayfa başlıkları, butonlar, form etiketleri, yardım metinleri, hata mesajları, boş durumlar, bildirimler, onay pencereleri ve sohbet soruları. Backend'den gelip arayüzde gösterilen hata cümleleri de dahil. Kod içi yorumlar, teknik belgeler ve commit mesajları kapsam dışı. Yeni ya da değişen her metin `docs/plans/genc-akisi-metinler.md` listesine eklenir.

---

## 1. Kime yazıyoruz

Metinleri **jüri için değil, ürünü kullanacak kişiler için** yazıyoruz. Teknik mimari ne kadar güçlü olursa olsun, kullanıcı onu görmez; yalnızca kendisine ne kazandırdığını görür.

| Kitle | Kim | Ne ister | Ton |
|---|---|---|---|
| **Genç** | 18-30 yaş; öğrenci, yeni mezun ya da ilk işlerinden birinde. CV'si zayıf olabilir, hiç projesi olmayabilir. | Görünür olmak, fırsata ulaşmak, yaptığının ciddiye alınması. | Sıcak, cesaretlendirici, yargılamayan. Samimi ama ciddi. |
| **Firma** | Startup, KOBİ ya da kurumsal şirket temsilcisi. Zamanı kısıtlı. | Doğru adaya ya da iş ortağına hızlıca ulaşmak, neden uygun olduğunu anlamak. | Profesyonel, net, saygılı. Kısa ve sonuca odaklı. |
| **GİRVAK (yönetici)** | Program ekibi. | Programın durumunu izlemek, pasif kalan bağlantıları görmek. | Nesnel, raporlama dili. |

## 2. Temel ilkeler

1. **Sade yaz.** Kullanıcının bilmediği hiçbir kavramı açıklamasız kullanma. Bir cümle, bir fikir.
2. **Kazancı söyle, mekanizmayı değil.** "Kartın vektöre çevrildi" değil, "Kartın artık firmalara görünüyor."
3. **Dürüst ol.** Abartma, garanti verme. Bir şey henüz hazır değilse bunu söyle. "Mükemmel eşleşme", "garanti iş" gibi ifadeler kullanma.
4. **Yapay zekâyı saklama, kişileştirme de.** Kullanıcı bir yapay zekâ desteğiyle konuştuğunu bilmeli; bunu gereken yerde bir kez söyle ("yapay zekâ desteğiyle"). Ama "Keşif Ajanı", "Takip Ajanı" gibi isimler kullanıcıya gösterilmez; platformun kendisi konuşur.
5. **Olumsuz haberi nazik ver.** Gence hiçbir zaman "reddedildin" denmez; "Bu fırsat kapandı" denir. Firmaya da "aday elendi" yerine nötr ifadeler kullanılır.
6. **Kısa tut.** Buton 1-3 kelime, form etiketi 1-4 kelime, yardım metni en fazla 2 cümle.
7. **Tutarlı ol.** Aynı kavrama her yerde aynı adı ver (bkz. § 4). Aynı eylemin butonu her ekranda aynı yazılır.

## 3. Hitap

| Kime | Hitap | Fiil biçimi | Örnek |
|---|---|---|---|
| Genç | **sen** | "Ekle", "Anlat", "Kartını oluştur" | "Henüz yetenek kartın yok." |
| Firma | **siz** (küçük harfle) | "Ekleyin", "Tanımlayın" | "Henüz bir ihtiyaç tanımlamadınız." |
| GİRVAK | **siz** | "Görüntüleyin" | "Son 7 günde pasifleşen bağlantılar" |
| İki tarafın birlikte gördüğü ekran (iş birliği sayfası gibi) | **Hitapsız, nesnel** | "Plan iki taraf onaylayınca kilitlenir." | Kimin baktığına göre değişen parçalar ayrı metin olur. |

**Sen hitabında sınır:** Samimi ama argo yok, emoji yok, ünlem az. "Harika!", "Süper!" gibi abartılı tepkiler kullanılmaz.

**Siz hitabında sınır:** Resmî ama bürokratik değil. "Tarafınızca", "işbu", "müteakip" gibi kalıplar kullanılmaz.

## 4. Terim sözlüğü

Her kavramın **tek** adı var. "Kullanma" sütunundaki karşılıklar kullanıcıya görünen metinde geçmez (kodda ve teknik belgelerde geçebilir).

| Kavram | Kullan | Kullanma | Not |
|---|---|---|---|
| Gencin yetkinlik özeti | **yetenek kartı** | CV, profil kartı | Onaydan önce: "kartının taslağı" |
| Kayıt bilgileri (şehir, okul vb.) | **profil** | hesap bilgileri, kullanıcı bilgileri | |
| Gencin yaptığı somut işler | **çalışma** | somut çıktı, iş kalemi, çıktı, iş, deneyim | "Çalışmaların", "Çalışma ekle" |
| Çalışmanın türü | Proje · Staj · İş deneyimi · Gönüllülük · Yarışma | "İş" (tek başına) | "İş" tek başına genel kavramla karışır |
| Çalışmayı gösteren link | **kanıt** | delil, belge | Form etiketinde "Kanıt linki" olabilir |
| Çalışmayı doğrulayan kişi | **referans** | üçüncü taraf, onaylayan | |
| Gencin GitHub, YouTube vb. hesabı | **bağlı hesap** ("hesabını bağla") | entegrasyon, OAuth, sosyal hesap, hesap bağlama | Bölüm başlığı: "Bağlı hesaplar" |
| Kanıt olarak yüklenen PDF / resim | **dosya** (PDF) · **görsel** (resim) | belge (tek başına), ek, upload | Form etiketi: "PDF ya da görsel ekle"; buton: "Yükle ve değerlendir" |
| Gencin dosyayı firmalara açması | **Firmalar görebilir** | herkese açık, paylaş | Varsayılan kapalı: "Dosyayı yalnızca sen ve GİRVAK görür" |
| Barkodlu resmî belge | **e-Devlet belgesi** | barkodlu belge, resmî evrak | "e-Devlet belgen GİRVAK’ın incelemesinde." |
| Profil açıklamasına yazılan kod (`z360-…`) | **doğrulama kodu** | profil kodu, token, doğrulama tokenı | "Profil" kayıt bilgileri demek; platformdaki sayfa için "profilin" yalnızca platform adıyla ("Medium profilin") |
| Dört bileşenli değerlendirme | **güven göstergesi** | rubrik, güven skoru, puan, doğrulama skoru | |
| Göstergenin dört başlığı | **Kanıt · Sonuç · Rol · Referans** | kanıt orijinalliği, sonuç ölçülebilirliği, rol netliği, üçüncü taraf onayı | Uzun adlar yalnızca açıklama metninde |
| Firmanın tanımladığı ihtiyaç | **ihtiyaç** (firma tarafında) | talep, ilan | Başlıkta "ihtiyaç kartı" olabilir |
| Gencin gördüğü eşleşen ihtiyaç | **fırsat** | ihtiyaç kartı, ilan, iş ilanı | Aynı kayıt, gence "fırsat" olarak görünür |
| Firmanın gördüğü eşleşen genç | **aday** | yetenek, profil, sonuç | |
| Platformu kullanan kuruluş | **firma** | kurum (yeni metinlerde), şirket, kuruluş | Startup, KOBİ, kurumsal hepsi "firma" |
| Eşleşmenin gücü | **uyum** ("%72 uyum") | skor, eşleşme puanı, benzerlik | |
| Eşleşmenin açıklaması | **Neden uygun?** | gerekçe, gerekçe metni, bu eşleşmenin gerekçesi | İki tarafta da aynı başlık |
| Tarafların ilgisi | **ilgileniyorum** / **karşılıklı ilgi** | talep, başvuru, beğeni | Platform bir "başvuru" sistemi değil |
| Eşleşme sonrası çalışma | **iş birliği** | proje, pilot (tek başına), işbirliği (bitişik) | TDK: ayrı yazılır |
| İş birliğinin aşamaları | **plan** ve **adım** | milestone, görev, kilometre taşı | |
| Tamamlanmış iş birliği rozeti | **tamamlanan iş birliği** | pilot, pilot iş birliği, tamamlanmış pilot | Genç ve firma için aynı. Sayıyla: "2 tamamlanan iş birliği" |
| Sohbetle kart oluşturma | **kısa bir sohbet** | Keşif Ajanı, Keşif, ajan | Sayfa başlığı: "Yetenek kartını oluştur" |
| Sohbetle ihtiyaç tanımlama | **kısa bir sohbet** | Tanımlama Ajanı, Tanımlama | Sayfa başlığı: "İhtiyacınızı tanımlayın" |
| Plan önerisi | **plan önerisi** | Takip Ajanı'nın planı, ajandan plan | "Platform bir plan önerir" |
| Hatırlatmalar | **hatırlatma** | Canlılık Ajanı, canlılık olayı | |

### Kullanıcıya hiç gösterilmeyen kelimeler

ajan · pipeline · embedding · vektör · rubrik · skor · eşik · token · checkpoint · LLM · model (yapay zekâ modeli anlamında) · oturum (sohbet anlamında) · faz · HTTP kodları (404, 409, 422…) · veritabanı alan adları (`onerildi`, `kanit_bekleyen` vb.)

## 5. Metin türlerine göre kurallar

### 5.1 Sayfa başlıkları
- Sayfanın ne işe yaradığını söyler, sistemin iç adını değil.
- Cümle düzeni: yalnızca ilk harf büyük. "Yetenek kartını oluştur", ~~"Yetenek Kartını Oluştur"~~.

### 5.2 Butonlar
- **Fiille başlar ve sonucu söyler:** "Kartı onayla", "Çalışma ekle", "İhtiyacı kaydedin".
- "Tamam", "Gönder", "Devam", "Evet" gibi belirsiz butonlar kullanılmaz; onay pencerelerinde bile eylemin adı yazılır ("Sil", "Vazgeç").
- İşlem sürerken aynı fiilin süren hâli ve üç nokta: "Kaydediliyor…", "Ekleniyor…".
- Birincil eylem ekranda bir tanedir.

### 5.3 Form etiketleri ve yardım metinleri
- Etiket isim ya da kısa isim öbeğidir, soru değildir: "Şehir", "Çalışma modeli".
- Zorunlu olmayan alanın yanında "(isteğe bağlı)" yazar. Zorunlu alanlar ayrıca işaretlenmez.
- **Neden sorduğumuzu söyle**, özellikle kişisel bilgilerde: "Firmalar seni bu şehirdeki fırsatlarla eşleştirebilsin diye."
- Yer tutucu bir örnektir ve "ör." ile başlar: "ör. Marmara Üniversitesi". Yer tutucu, etiketin yerine kullanılmaz.

### 5.4 Hata mesajları
- **Ne oldu + ne yapmalı**, iki kısa cümle: "Bu e-posta ile zaten bir hesap var. Giriş yapmayı dene."
- Kullanıcıyı suçlamaz: ~~"Geçersiz giriş yaptınız"~~ → "E-posta ya da şifre eşleşmedi."
- Teknik kod, alan adı ya da İngilizce hata metni göstermez.
- Sistemden kaynaklanan hatalarda sorumluluğu üstlenir: "Şu an bağlantı kuramadık. Birkaç saniye sonra tekrar dene."

### 5.5 Boş durumlar
- Üç parça: **ne yok + neden önemli + ilk adım (buton).**
- Örnek: "Henüz yetenek kartın yok. Kartın olmadan firmalar seni göremez." [Kartını oluştur]

### 5.6 Onay pencereleri
- Soru eylemin sonucunu söyler: "“Kütüphane sistemi” silinsin mi? Kanıtı ve referans istekleri de silinir."
- Butonlar eylemin adıdır: "Sil" / "Vazgeç".

### 5.7 Bildirimler
- **Kim + ne oldu + ne yapabilirsin:** "Kooperatif A profilinle ilgileniyor. Kabul edersen iletişim bilgileriniz paylaşılır."
- Olumsuz durumlar nötr: "Kooperatif A'nın ihtiyacı kapandı." Neden kapandığı yazılmaz.

### 5.8 Bekleme ve arka plan işleri
- Kullanıcı neyi beklediğini ve ne zaman biteceğini bilmeli. Süreyi bilmiyorsak kesin süre vermeyiz.
- Örnek: "Kaydedildi. Değişen çalışman yeniden değerlendiriliyor; güven göstergesi kısa süre içinde güncellenir. Sayfayı yenileyerek görebilirsin."

### 5.9 Durum etiketleri

| Durum | Genç görür | Firma görür |
|---|---|---|
| Eşleşme önerildi | Sana uygun | Aday |
| Genç ilgi gösterdi | İlgin iletildi | İlgi gösterdi |
| Firma ilgi gösterdi | Firma seninle ilgileniyor | Yanıt bekleniyor |
| Karşılıklı ilgi | Karşılıklı ilgi | Karşılıklı ilgi |
| Kapandı / reddedildi | Kapandı | Kapandı |

Gence "Reddedildi", "Elendi", "Başarısız" gibi etiketler gösterilmez.

### 5.10 Sohbet soruları
- **Tek soru** sorar. İki soru tek mesajda birleşecekse ikincisi ilkinin devamı olmalı.
- Gerekirse bir örnek verir: "Sayıyla anlatabilir misin? Örneğin kaç kişi kullandı ya da ne kadar zaman kazandırdı?"
- Bilmeme hakkı tanır, ısrar etmez: "Bilmiyorsan geçebiliriz."
- Formda zaten alınmış bir bilgiyi sormaz.
- Soyut seviye sormaz ("Python'da ne kadar iyisin?"); o araçla ne yaptığını sorar.
- Sohbetin sonunda ne olacağını söyler: "Bilgilerinle bir kart taslağı hazırladım. Kontrol et, istediğin yeri düzelt, sonra onayla."

## 6. Yazım ve imla

- TDK yazım kuralları geçerlidir. Sık karışanlar: **iş birliği**, **yapay zekâ**, **e-posta**, **her şey**, **bir şey**, **birkaç**.
- **Yüzde işareti sayıdan önce:** %72 (~~72%~~).
- **Tarih:** 12 Ekim 2026. **Saat:** 14.30.
- **Tırnak:** “ ” ve ‘ ’. Özel adlara gelen ek kesme işaretiyle ayrılır: GİRVAK'ın.
- **Uzun tire (—) arayüz metninde kullanılmaz.** Cümleyi nokta ya da virgülle böl. Mevcut metinlerde çok sık geçiyor; denetimde temizlenecek.
- **Üç nokta** tek karakterdir: …
- Başlık ve butonlarda cümle düzeni: yalnızca ilk harf büyük.

## 7. Önce ve sonra: mevcut metinlerden örnekler

| Ekran | Şu an | Olmalı |
|---|---|---|
| Genç paneli, boş durum | "Henüz yetenek kartın yok. Keşif Ajanı’yla kısa bir sohbet yap; ne yaptığını birlikte bir karta dönüştürelim." | "Henüz yetenek kartın yok. Birkaç soruyla neler yaptığını anlat, kartını birlikte oluşturalım." [Kartını oluştur] |
| Kart sayfası, açıklama (genç) | "Doğrulama Ajanı her somut çıktıyı dört ayrı başlıkta puanlar — tek bir “güven puanı”na indirmez." | "Her çalışman dört açıdan değerlendirilir: kanıt, sonuç, rol ve referans. Tek bir puana indirilmez; böylece neyin güçlü, neyin eksik olduğunu görürsün." |
| Firma paneli, boş durum | "Henüz ihtiyaç kartın yok. Tanımlama Ajanı’yla kısa bir sohbet yap; ihtiyacını ölçülebilir bir karta çevirelim." | "Henüz bir ihtiyaç tanımlamadınız. Kısa bir sohbetle ihtiyacınızı netleştirin, size uygun adayları gösterelim." [İhtiyacınızı tanımlayın] |
| İş birliği sayfası, buton | "Ajandan plan iste" | "Plan önerisi al" |
| İş birliği sayfası, başlık | "Takip Ajanı’nın özeti" | "Durum özeti" |
| Firma paneli, kart satırı | "eşleştirmeye hazır değil" | "henüz adaylarla eşleştirilmedi" |
| Kart sayfası, yükleme | "Kart okunuyor…" | "Kart yükleniyor…" |
| Keşif sohbeti, ek soru | "“X” işinde senin payın neydi? Tek başına mıydın, ekipçe miydi — hangi kısmı sen yaptın?" | "“X” üzerinde tek başına mı çalıştın, ekipçe mi? Ekipçeyse hangi kısmı sen yaptın?" |
| Kart sayfası, bölüm başlığı | "Somut çıktılar" | "Çalışmaların" |
| Genel hata | "İstek başarısız: 422" | "Bazı alanlar eksik ya da hatalı. İşaretli alanları kontrol et." |

## 8. Süreç

1. **Yeni metin:** Claude Code bu rehbere göre yazar ve `docs/plans/genc-akisi-metinler.md` listesine ekler.
2. **Denetim:** Liste, genç akışı bittikten sonra toplu olarak gözden geçirilir. Son onayı Zühre verir.
3. **Rehber değişikliği:** Terim ya da kural değişirse önce bu dosya güncellenir, sonra metinler.
4. **Şüphede:** Bir metnin hangi terimi kullanacağı belirsizse rehbere bakılır; rehberde yoksa terim uydurulmaz, listeye not düşülür.

## 9. Alınan kararlar (28 Eylül 2026)

1. **Somut işlerin adı: "çalışma".** "İş" ve "deneyim" başka kavramlarla (tür listesindeki "İş deneyimi", "deneyim seviyesi" alanı) karıştığı için kullanılmaz; "proje" yalnızca bir tür adıdır.
2. **Eşleşme açıklamasının başlığı: "Neden uygun?"** Genç ve firma ekranında aynı başlık. Açıklama metni şimdilik firmaya hitaben 3. şahısla yazılıyor ve gence de aynen gösteriliyor; bu bilinen bir sınır.
3. **Tamamlanmış iş birliği rozeti: "tamamlanan iş birliği".** Genç ve firma için aynı. "Pilot" kelimesi kullanıcıya gösterilmez.
4. **Kayıt ekranındaki rol seçimi:** "Genç yetenek olarak katılıyorum" / "Firma olarak katılıyorum".
5. **Yapay zekâ açıklaması** iki yerde yapılır:
   - Sohbetin başında bir kez: "Bu sohbet yapay zekâ desteğiyle ilerler. Kartın sen onaylamadan kaydedilmez." Firma tarafındaki ihtiyaç sohbetinde: "Bu sohbet yapay zekâ desteğiyle ilerler. İhtiyacınız siz onaylamadan kaydedilmez."
   - Güven göstergesinin açıklamasında: "Kanıt, sonuç ve rol yapay zekâ desteğiyle değerlendirilir; referans puanını referans kişi verir."
