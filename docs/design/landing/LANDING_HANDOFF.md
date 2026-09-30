# Zemin360 — Karşılama Sayfası Uygulama Brief'i (v2)

v2 notu: Bu sürüm `docs/icerik-rehberi.md` (onaylı içerik rehberi) ve `design-language.md` ile hizalandı. Çelişki olursa sıralama şöyledir: **içerik rehberi > design-language.md > bu brief**. Bu brief'teki metinler rehbere göre yeniden yazıldı; yeniden yorumlanmaz, birebir kullanılır.

Görsel referans `reference/` klasöründeki iki HTML dosyasıdır. Bu dosyalar yalnızca **düzen, bölüm sırası ve boşluklar** için referanstır. Renk, font ve metin için referans alınmaz; renk ve font `design-language.md`'den, metin bu belgeden gelir.

## 0. Başlamadan önce

1. Mevcut `/` sayfasını, layout'u, global stilleri, `design-language.md`'yi ve içerik rehberini incele.
2. Sadece karşılama sayfası değişir. Diğer sayfalara, giriş/kayıt akışına ve backend'e dokunma.
3. Mevcut CTA hedeflerini (genç kayıt, firma kayıt, giriş) koru.
4. Önce kısa bir plan çıkar, onay al, sonra uygula.

## 1. Görsel sistem

- **Palet ve font:** `design-language.md`'deki mevcut palet ve IBM Plex Sans kullanılır. Yeni renk token'ı ya da yeni font eklenmez. Başlıklarda mevcut sistemde hangi yazı tipi kullanılıyorsa o kullanılır.
- Referans dosyadaki renkler rol olarak eşlenir: koyu yeşil → mevcut birincil renk; turuncu → mevcut vurgu rengi (#B8823C); krem zemin → mevcut sayfa zemini; koyu bant → mevcut en koyu ton.
- **Kontrast:** Vurgu renginin (#B8823C) üzerinde beyaz metin 4.5:1 kontrastı sağlamıyorsa, firma butonunda ya koyu metin kullanılır ya da vurgunun mevcut koyu tonu. Kontrast, renk sadakatinden önce gelir.
- `design-language.md` kuralları geçerlidir: bölüm üst etiketleri **büyük harfle yazılmaz** (cümle düzeni), butonların sonunda **ok (→) kullanılmaz**.
- Düzen referanstaki gibi: 1200px içerik genişliği, bölümler arası 96–112px, iki sütunlu hero, altı sütunlu süreç kartları.

## 2. Hitap kuralı (içerik rehberi § 3)

Karşılama sayfası hem gençlere hem firmalara açık olduğu için **ortak bölümler hitapsız ve nesneldir.** Yalnızca "Nasıl çalışır" sekmelerinde hitap ayrılır: genç sekmesi **sen**, firma sekmesi **siz**. Butonlar birinci tekil kişi ("Fırsat arıyorum") olduğu için hitap sorunu yaratmaz.

## 3. Bölümler ve metinler (birebir)

### 3.1 Navbar
- Solda "Zemin360".
- Linkler: Nasıl çalışır · Gençler için · Firmalar için · Neden Zemin360
- Sağda: **Giriş yap** (sade link), **Kayıt ol** (birincil buton).
- Mobilde: logo, "Giriş yap", menü ikonu (`aria-label="Menüyü aç"`).

### 3.2 Hero
Sol sütun:
- Etiket: **Genç yetenekler ve firmalar için buluşma platformu**
- H1: **Yetenek ve ihtiyaç, kanıtla buluşsun.**
- Alt metin: **Gençler yaptıkları çalışmaları görünür kılıyor, firmalar aradıkları yeteneği ya da iş birliği ortağını buluyor. Her eşleşmenin nedeni iki tarafa da açıkça gösteriliyor.**
- İki eşit buton-kart (üstte soru satırı yok, altta "Hesabın var mı?" satırı yok; giriş navbar'da):
  - Birincil renk: **Fırsat arıyorum** / alt satır: *Genç yetenekler için* → genç kayıt
  - Vurgu rengi: **Yetenek ya da ortak arıyorum** / alt satır: *Firmalar için* → firma kayıt

Sağ sütun, demo kartı:
- Üst satır: **Kısa bir sohbet** + sağda **Örnek** rozeti
- Platform mesajı: *Son bir yılda tamamladığın, sonucunu gösterebileceğin bir çalışman var mı?*
- Kullanıcı mesajı: *Mahalle kütüphanesine ödünç takip sistemi yazdım. 400 kitap ve 120 üyeyi takip ediyor.*
- Ayraç: **Yetenek kartın hazır**
- Kart: **Ayşe Y.** · *1 çalışma · 1 referans* · chip'ler: Veritabanı tasarımı, Yazılım geliştirme, Uçtan uca proje
- Fırsat kutusu: **Sana uygun · Kooperatif üye kayıt sistemi** / *Benzer bir sorunu daha önce çözmüş, sonucu somut, referansı doğrulanmış.*

Animasyon: öğeler sırayla belirir (~600ms arayla, fade + hafif yukarı kayma). `prefers-reduced-motion` açıksa animasyon yok.

### 3.3 Sorun bandı (koyu zemin)
- H2: **İyi fırsatlar çoğu zaman doğru kişiyi tanıyanlara gidiyor.**
- **Yapılanlar görünmüyor.** Bir özgeçmiş, bir gencin gerçekte neler başardığını anlatmaya yetmiyor.
- **İhtiyaç netleşmiyor.** “Dijitalleşmek istiyoruz” gibi genel bir istek, kiminle çalışılması gerektiğini söylemiyor.
- **Başlayan iş birliği yarım kalıyor.** Tanışmadan sonra süreç takip edilmediğinde, umut vadeden iş birlikleri sessizce sönüyor.

### 3.4 Nasıl çalışır (`id="nasil"`)
- Üst etiket: **Nasıl çalışır** · H2: **Üç adımda doğru eşleşme.**
- Sekmeler: **Genç yetenek** | **Firma** (erişilebilir tablist, ok tuşlarıyla geçiş). Navbar'daki "Gençler için / Firmalar için" ilgili sekmeyi seçip buraya kaydırır.

Genç sekmesi (sen):
1. **Kısa bir sohbetle başla.** Form doldurmak ya da CV yüklemek yerine, yaptığın çalışmaları birkaç soruyla anlat. Yetenek kartın bu sohbetten oluşur. — *Sonuç: Yetenek kartın*
2. **Çalışmalarını kanıtla.** Her çalışman için bir kanıt linki ekle ya da seni tanıyan birinden referans iste. Kanıtın güçlendikçe kartın öne çıkar. — *Sonuç: Güven göstergesi*
3. **Sana uygun fırsatları gör.** Hangi fırsata neden uygun olduğunu açıkça gör. İlgileniyorsan firmaya bildir. — *Sonuç: Sana uygun fırsatlar*

Firma sekmesi (siz):
1. **İhtiyacınızı kendi cümlelerinizle anlatın.** Aklınızdakini olduğu gibi yazın. İhtiyacı netleştirmek için size birkaç soru sorulur. — *Sonuç: Taslak ihtiyaç*
2. **İhtiyaç kartınızı onaylayın.** Genel bir istek; kapsamı, beklenen sonucu ve başarı ölçütü belli bir tanıma dönüşür. — *Sonuç: İhtiyaç kartı*
3. **Uygun adayları ve iş ortaklarını görün.** İhtiyacınıza uygun genç yetenekleri ve iş birliği yapabileceğiniz firmaları, neden uygun olduklarıyla birlikte görün. — *Sonuç: Adaylar ve olası iş ortakları*

### 3.5 Şeffaf eşleşme
Sol:
- Üst etiket: **Şeffaf eşleşme** · H2: **Her eşleşmenin nedeni açıkça görünür.**
- Metin: **Tek bir puan yerine dört başlıkta değerlendirme: kanıt, sonuç, rol ve referans. Firma neye güvenebileceğini, genç neyi güçlendirebileceğini görür.**
- Link: **Değerlendirme nasıl yapılıyor?** (şimdilik `#`)

Sağ, kart: başlık **Neden uygun?** + **Örnek** rozeti. Alt başlık: *Üye kayıtlarını elle tutmaktan kurtulmak isteyen bir kooperatifin ihtiyacıyla*

| Başlık | Açıklama | Seviye |
|---|---|---|
| Kanıt | Kanıt linki açılıyor, çalışmayı kendisi geliştirmiş. | Güçlü |
| Sonuç | 400 kitap ve 120 üye belirtilmiş, kullanım süresi yok. | Orta |
| Rol | Çalışmanın tamamını tek başına üstlenmiş. | Güçlü |
| Referans | Kütüphane sorumlusu referans isteğini yanıtladı. | Orta |

Kartın altında küçük not: *Kanıt, sonuç ve rol yapay zekâ desteğiyle değerlendirilir; referans puanını referans kişi verir.*

Seviye çubuğu sadece renge dayanmaz; kelime (Zayıf / Orta / Güçlü) her zaman görünür, çubukta `aria-label="Seviye: Güçlü"`.

### 3.6 Süreç (`id="surec"`)
- Üst etiket: **Tanışmadan iş birliğine** · H2: **Eşleşmeyle bitmiyor, iş birliği boyunca süreç takip ediliyor.**
- Metin: **Her adım yapay zekâ desteğiyle ilerler; son kararı her zaman kullanıcı verir.**

| # | Soru (italik, tırnak içinde) | Başlık | Açıklama |
|---|---|---|---|
| 01 | “Beni kim fark edecek?” | Yetenek kartı oluşturur | Kısa bir sohbetten, gencin çalışmalarını anlatan bir yetenek kartı çıkarır. |
| 02 | “Tam olarak neye ihtiyacımız var?” | İhtiyacı netleştirir | Genel bir isteği, ölçülebilir bir ihtiyaç kartına dönüştürür. |
| 03 | “Anlatılanlar gerçekten doğru mu?” | Kanıtı değerlendirir | Çalışmaları kanıt, sonuç, rol ve referans başlıklarında değerlendirir. |
| 04 | “Kiminle çalışmalıyım?” | Doğru kişiyle buluşturur | Uygun eşleşmeleri, neden uygun olduklarıyla birlikte önerir. |
| 05 | “İş birliği ne durumda?” | İş birliğini izler | Planı ve adımları iki tarafın da gördüğü tek bir ekranda tutar. |
| 06 | “Bağlantılarımız hâlâ canlı mı?” | Bağlantıları canlı tutar | Sessizleşen bağlantıları fark eder, hatırlatma gönderir. |

- Altta döngü ikonu + **Tamamlanan her iş birliği, sonraki eşleşmeleri daha isabetli hâle getirir.**

### 3.7 Güven
- **Unvan değil, kanıt.** Yetenek kartları, açılabilen kanıtlar ve yanıtlanan referanslarla güçlenir.
- **Onay olmadan hiçbir şey kaydedilmez.** Yetenek kartı da ihtiyaç kartı da sahibi onaylamadan kaydedilmez. + link *KVKK aydınlatma metni* (şimdilik `#`)
- **Herkes aynı tabloyu görür.** İş birliği başladığında plan, adımlar ve son durum iki tarafın da erişebildiği ortak bir alanda tutulur.
- Alt satır: *Türkiye Girişimcilik Vakfı'nın (GİRVAK) Zemin360 programı kapsamında geliştirilmektedir.* + iki logo placeholder kutusu (gerçek logo eklenmez).

### 3.8 Kapanış CTA'sı
- H2: **Yapılan iş görünsün, doğru kişiler buluşsun.**
- Butonlar: **Fırsat arıyorum** · **Yetenek ya da ortak arıyorum** (hero ile aynı route'lar)

### 3.9 Footer
- "Zemin360" + *Genç yetenekleri ve firmaları kanıtla buluşturan platform*
- Gizlilik · KVKK · İletişim (şimdilik `#`)

## 4. Mobil

Metinler her ekran boyutunda aynıdır; tek kaynaktan (`content/landing.ts`) gelir. Mobilde yalnızca yerleşim değişir. Demo kartı mobilde de tam gösterilir. Süreç kartları mobilde tek sütun ya da yatay kaydırma.

## 5. Kaldırılacaklar

- "Backend bağlı" rozeti ve "Faz 2…" notu public sayfadan kalkar; gerekirse yalnızca `NEXT_PUBLIC_SHOW_DEV_STATUS=true` iken görünür.
- Eski "Altı problem, altı ajan" bölümü ve ajan isimli tüm metinler.

## 6. Erişilebilirlik

- Gerçek `<a>` / `<button>`, en az 44px dokunma alanı, görünür focus.
- Kontrast en az 4.5:1 (büyük başlıkta 3:1).
- Tek `h1`, bölümler `h2`.
- 375 / 768 / 1280 / 1440px'te yatay kaydırma yok.

## 7. Kabul kriterleri

- [ ] Metinler bu belgeyle birebir aynı ve içerik rehberinin terim sözlüğüne uyuyor.
- [ ] Palet ve font `design-language.md`'den geliyor; yeni token yok.
- [ ] Büyük harfli üst etiket ve butonlarda ok yok.
- [ ] CTA'lar doğru route'lara gidiyor; sekmeler fare ve klavyeyle çalışıyor.
- [ ] Demo animasyonu reduced-motion'a uyuyor.
- [ ] Dev rozeti production'da görünmüyor.
- [ ] Yeni metinler `docs/plans/genc-akisi-metinler.md` listesine eklendi.
- [ ] Lint ve build hatasız.

## 8. Commit kuralı

Commit mesajlarında Claude, Opus ya da "Co-Authored-By" gibi herhangi bir yapay zekâ imzası/atıf satırı bulunmaz.
