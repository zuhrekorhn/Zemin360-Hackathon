# Faz D — Canlılık Ajanı + GİRVAK paneli (özellik notu)

> Durum: **onaylandı (27 Eyl).** § 9'daki dört kararda öneriler seçildi; § 8'deki
> olaylar listesi sapması kabul edildi. Onayla gelen iki ek § 4 (cron kimliği) ve
> § 7 (hedef etiketleri) içine işlendi. Roadmap § Faz D'nin maddeleri ve kesim
> çizgisi bu notun çerçevesi; yeni özellik eklenmez.

## 0. Amaç ve kabul

"Yaşayan bir ağ" (README problem 4): kurulan bağlantılar sessizce ölmesin.
Canlılık Ajanı döngünün her aşamasında hareketsiz kalan kaydı fark eder ve
ilgili kişiye kısa, kişiye özel bir hatırlatma bırakır. Yeni bir ihtiyaç
geldiğinde, uzun süredir kartı olan gençlere "sana uygun yeni bir ihtiyaç var"
fırsatını bildirir. GİRVAK programın hedeflerini gerçek sayılarla, pasifleşen
bağlantıları ve son Canlılık olaylarını tek panelde görür.

**Kabul:**
- Yerelde kayıtların zamanı geri alınarak (§ 6 demo aracı) her pasiflik türü için "taramayı şimdi çalıştır"a basılır.
- Doğru kişiye tek bir hatırlatma gider; aynı tarama tekrarlanınca yeni hatırlatma çıkmaz.
- Yeni ihtiyaç kartı eski bir karta fırsat bildirimi olarak düşer.
- GİRVAK panelinde hedefler, pasifler ve olaylar görünür.
- Bunların hepsi çıkmaz sokak olmadan yürümeli.

**Sınır (agent-specs § 5):**
- Canlılık davranış tahmini yapmaz: kural tabanlı eşikler yeter.
- Toplu ya da jenerik spam göndermez.
- Hiçbir kaydın durumunu değiştirmez: hatırlatır, karar vermez.
- Gerçek e-posta göndermez; uygulama içi bildirim kullanır.

## 1. Pasiflik: neye göre, ne zaman, kime

Pasiflik **okuma anında**, mevcut alanlardan hesaplanır. Doğrulama zaman
aşımıyla ve Takip gecikmesiyle aynı desen; yeni bir "pasif" alanı saklanmaz.

- **Hareket ölçüsü:** Eşleşmenin `son_aktivite_tarihi`. Faz B ve C'de her geçişte ve her Takip eyleminde güncelleniyor.
- **Gecikme ölçüsü:** Milestone'un `hedef_tarih`'i.

| Tür (`tur`) | Kayıt ve durum | Eşik | Kime | Ne der (örnek) |
|---|---|---|---|---|
| `oneri_bekliyor` | Eşleşme `onerildi` | Öneri **7 gündür** hareketsiz | Kurum (ihtiyacın sahibi) | "İhtiyaç kartın için 3 öneri bir haftadır yanıt bekliyor; gerekçelere göz atmak birkaç dakika sürer." İhtiyaç kartı başına **tek, toplu** bildirim |
| `ilgi_yanitsiz_1` | Eşleşme `ilgileniliyor` | **3 gün** | Genç | "Moda Dayanışma Kooperatifi 3 gündür yanıtını bekliyor; kabul ya da ret, ikisi de onlara yol gösterir." |
| `ilgi_yanitsiz_2` | Eşleşme `ilgileniliyor` | **10 gün** | Genç (ikinci ve son hatırlatma) + kurum (bilgi) | Kuruma: "Elif henüz yanıt vermedi; bu arada diğer önerilere de bakabilirsin." |
| `plan_onaysiz` | İş birliği `plan_bekliyor` | **5 gün** hareketsiz | Planı henüz onaylamamış taraf(lar) | "Planınız 5 gündür onay bekliyor; senin onayınla iş birliği başlar." |
| `isbirligi_hareketsiz` | İş birliği `aktif` | **14 gün** hareketsiz | İki taraf | "İki haftadır adımlarda hareket yok; sıradaki adım 'Kayıt ekranı'." |
| `adim_gecikti` | `aktif` iş birliğinde gecikmiş adım | Hedef tarihten **1 gün** sonra | Adımı henüz işaretlememiş taraf(lar) | "'Kayıt ekranı' adımının hedef tarihi 3 gün geçti; tamamlandıysa işaretle, değilse karşı tarafla konuşun." |
| `yeni_firsat` | Yeni ihtiyacın önerisi (§ 2) | — | Genç | "Kartına uyan yeni bir ihtiyaç var (sektör: sivil toplum). Kanıt eklemek kartını öne çıkarır." |

**Kurallar:**
- **Kapsam dışı kayıtlar:** `reddedildi` eşleşmeler ve `tamamlandi` iş birlikleri hatırlatılmaz. Hesabı olmayan (Faz B öncesi) profil de hatırlatılmaz.
- **Öncelik:** Aynı iş birliğinde aynı kişiye aynı taramada tek hatırlatma gider. `adim_gecikti`, `isbirligi_hareketsiz`'den önce gelir; gecikmiş adım zaten "hareket yok" demektir.
- **Eşikler tek yerde:** Saf bir modülde durur (`app/agents/canlilik_kurallari.py`) ve tablo testle sabitlenir. `.env`'den değiştirilmez; demo için zaman aracı var (§ 6).
- **Bildirimler:** Faz B tablosuna, Canlılık türleriyle yazılır. Tıklayınca ilgili sayfaya gider: kurum öneriler sayfasına, genç "Bana gelen ilgiler"e, iş birliği bildirimleri `/isbirligi/{id}`'ye. Metinde ad olabilir, e-posta olmaz.

## 2. "Yeni fırsat" dalı

Yeni bir ihtiyaç kartı onaylanınca Eşleştirme zaten bütün yetenek kartlarını
yeniden tarıyor ve kuruma öneri yazıyor (Faz B). Eski kartların sahibi olan
gençler ise bundan habersiz: Faz B kararıyla genç, eşleşmeyi ancak kurum
ilgilenince görüyor.

- **Ne olur:** Tarama, **son 7 gün içinde** açılmış ihtiyaç kartlarının `onerildi` önerilerine bakar. Önerilen yetenek kartı **en az 14 gün önce** oluşturulmuşsa ("eski kart"), kartın sahibine `yeni_firsat` bildirimi gider. Bildirim her (genç, ihtiyaç kartı) çifti için bir kez gider. Genç çoğu zaman yeni kartı yeni oluşturmuş olur; o zaman fırsat dalı gereksizdir, eski kart eşiği bu yüzden var.
- **Ne söylenir:** → **Karar 3.**
  - **Öneri, anonim:** Kurumun adı ve ihtiyacın metni söylenmez; yalnızca sektör ve "kartını güçlendir" çağrısı (kanıt ekle). Bağlantı gencin kendi kart sayfasına gider. Faz B'nin "genç, kurum ilgilenmeden eşleşmeyi görmez" kararı bozulmaz.
  - **Alternatif:** İhtiyaç kartını gence baştan göstermek. Faz B'nin sahiplik tablosunu (§ 3) değiştirir; gencin "ilgi göstermeden önce kurumu görme" hakkı olur.
- **Ne yapmaz:** Gence "başvur" düğmesi açmaz (tek yönlü başvuru akışı yok); eşleşmenin durumunu değiştirmez.
- **Kesilebilir:** Roadmap kesim çizgisi (2). Hatırlatmalar onsuz tam çalışır.

## 3. Tekrarın önlenmesi

Aynı hatırlatmanın her taramada yeniden gitmemesi için tek kural:

> **Bir kayıt için aynı türde olay, o kaydın son hareketinden SONRA zaten
> yazılmışsa yenisi yazılmaz.**

- **Hareketsizlik dönemi:** Her dönemde tür başına en çok bir hatırlatma gider.
  - Taraflardan biri bir şey yaparsa (`son_aktivite_tarihi` ilerler) dönem kapanır; hareketsizlik yeniden eşiği aşarsa yeni dönem başlar.
  - Böylece "yanıt verdi, sonra yine sustu" durumu yeniden hatırlatılır; "hiç kıpırdamadı" durumu her taramada tekrarlanmaz.
- **Kademeler:** `ilgi_yanitsiz_1` ve `_2` ayrı türlerdir; her biri bir kez gider. İkinciden sonra o dönemde başka ilgi hatırlatması gitmez: "son hatırlatma" budur.
- **Gecikmiş adım:** Anahtar adım başınadır (`milestone_id`); her gecikmiş adım dönem başına bir kez hatırlatılır.
- **Yeni fırsat:** Anahtar (yetenek kartı, ihtiyaç kartı) çiftidir; bir kez gider, dönem kavramı yoktur.
- **Eşzamanlı taramalar:** Cron ile düğme aynı anda çalışırsa taramalar `pg_advisory_xact_lock` ile sıraya girer (Eşleştirme pipeline'ıyla aynı desen). İkinci tarama birincinin yazdıklarını görür ve hiçbir şey yazmaz.
- **İdempotent:** Taramayı art arda iki kez çalıştırmak ikinci seferde sıfır olay üretir. Testle sabitlenir.

## 4. Periyodik tarama: nasıl çalışır

Taramanın **asıl işi bir uç nokta**: `POST /canlilik/tarama`. Eşleştirme'nin
"arka plan işi bir endpoint" deseni ve CLAUDE.md'deki "zamanlayıcı yok,
bilinçli" kararıyla aynı. Soru yalnızca bu ucu kimin, ne sıklıkla çağıracağı.

| | A) Uygulama içi zamanlayıcı | B) Platform cron'u (öneri) |
|---|---|---|
| Nasıl | FastAPI açılışında (`lifespan`) bir asyncio döngüsü ya da APScheduler; N saatte bir taramayı çağırır | Railway/Render cron işi (ya da GitHub Actions `schedule`) günde bir iki kez ucu çağırır; istek, `.env`'deki `TARAMA_ANAHTARI` ile imzalı başlık taşır |
| Kurulum | Kod içinde, ek altyapı yok | Faz E'de platformda bir cron satırı |
| Uyku modu | Ücretsiz katmandaki servis uyuyunca zamanlayıcı da uyur; tarama kaçar | Cron isteği servisi uyandırır; tarama kaçmaz |
| Çoklu süreç | Her worker kendi zamanlayıcısını çalıştırır; kilit gerekir (yine de) | Tek çağrı |
| Yeniden başlatma | Sayaç sıfırlanır, tarama zamanı kayar | Etkilenmez |
| CLAUDE.md kararı | "Zamanlayıcı yok" kararını bozar | Kararla uyumlu: iş yine bir uç nokta |
| Yerelde | Kendiliğinden çalışır | Kendiliğinden çalışmaz; düğme ya da betik |

- **Öneri: B.** → **Karar 1.**
  - Canlıda cron günde iki kez (09:00 ve 18:00, İstanbul) çağırır.
  - Yerelde ve demoda GİRVAK panelindeki **"Taramayı şimdi çalıştır"** düğmesi, ayrıca `scripts/canlilik_taramasi.py` kullanılır.
  - Kurulum Faz E'nin yayına alma maddesine eklenir.
- **Yetki:** Uç iki yoldan çağrılabilir:
  - GİRVAK token'ıyla (düğme).
  - `X-Tarama-Anahtari` başlığıyla (cron). **Cron bir kullanıcı token'ı taşımaz:** GİRVAK'ın token'ı 7 günde düşer ve tarama sessizce durur. Cron'un kimliği `.env`'deki ayrı gizli anahtar `TARAMA_ANAHTARI`'dır (en az 32 karakter); başlık sabit zamanlı karşılaştırılır.
  - **Anahtar tanımlı değilse** başlık yolu tamamen kapalıdır, uç yalnızca GİRVAK token'ıyla çalışır. Yanlış anahtar 401 döner. Testle sabitlenir.
  - Bunların dışındaki her çağrı 401/403.
- **Yanıt:** Tarama özeti: türe göre olay sayısı, gönderilen bildirim sayısı, süre. Panelde "son tarama" olarak gösterilir.

## 5. Kişiye özel hatırlatma metni

- **Hızlı katman, tek LLM çağrısı:** Girdi yapılandırılmıştır: tür, alıcının rolü, karşı tarafın adı, kaç gün, adım adı. Çıktı en fazla iki cümle, nötr ve destekleyici, bir eylem çağrısıyla. Suçlama ve uydurma yoktur; kurallar Takip özetiyle aynı.
- **Şablona düşer:** LLM yanıt vermezse ya da çıktı kurala uymazsa (boş, çok uzun), her türün **sabit şablon metni** kullanılır; hatırlatma asla kaybolmaz. LLM kişiselleştirme kesilirse şablonlar tek başına yeter.
- **Toplu çağrı sınırı:** Bir taramada LLM çağrıları en çok 4'er eşzamanlı gider. Çağrı sayısı, alıcı ve kayıt başına bir hatırlatmayla sınırlı.
- **Yazılanlar:** Metin hem `canlilik_olayi.mesaj_metni`'ne hem bildirime yazılır. İkisi aynı işlemde yazılır: olay yazılıp bildirim kaybolmaz ya da tersi olmaz.

## 6. Veri modeli ve demo aracı

`CANLILIK_OLAYI` zaten var (Faz 0: `eslesme_id`, `tetiklenme_tarihi`, `tur`,
`mesaj_metni`). Migration veri silmeden şunları ekler:

| Alan | Tip | Neden |
|---|---|---|
| `alici_hesap_id` | uuid FK hesap, null, SET NULL | Kime gitti (GİRVAK listesinde ad; tekrar kuralında alıcı ayrımı) |
| `milestone_id` | uuid FK milestone, null, SET NULL | `adim_gecikti` adım başına tekrar anahtarı |
| `ihtiyac_karti_id` | uuid FK ihtiyac_karti, null, SET NULL | `yeni_firsat` ve toplu `oneri_bekliyor` anahtarı |

- **İndeks:** `(eslesme_id, tur, tetiklenme_tarihi)`, tekrar kuralının sorgusu için.
- **Olay ve eşleşme:** Olay yine eşleşmeye bağlıdır (`eslesme_id` zorunlu kalır). Toplu `oneri_bekliyor` bildiriminde her eşleşme için ayrı bir olay yazılır; kuruma tek bildirim gider.
- **Demo aracı:** `scripts/zamani_geri_al.py --gun N`, yalnızca yerel; `APP_ENV=production`'da çalışmaz.
  - Bütün eşleşmelerin `son_aktivite_tarihi`'ni, ihtiyaç ve yetenek kartlarının `olusturma_tarihi`'ni ve milestone `hedef_tarih`'lerini N gün geriye çeker.
  - Pasifleşme günlerce beklemeden yerelde gösterilir. Roadmap'teki demo notunun yerel karşılığı; canlıda tohum veri bunu hazır getirir (Faz E).

## 7. GİRVAK paneli

`/girvak` sayfası dört bölüme genişler. "Faz D'de gelecek" diyen bir ekran yok.

1. **Program hedefleri:** Her biri sayı / hedef ve ince bir ilerleme çizgisiyle. Hedef sayıları sabit, tek yerde (`app/core/program.py`).
   - **Etiket iki parçalı:** Her hedef programın kendi adıyla **ve** platformda neyi ölçtüğümüzle birlikte görünür. Örnek: "80 startup başvurusu — platformda: en az bir yetenek kartı olan genç". Program hedefiyle bizim ölçümümüz arasındaki fark gizlenmez.
   - Programın adları ve ölçüm tanımları da aynı dosyada, tek yerde; yanıtta `program_adi` ve `olcum` alanları olarak döner.
   - Tanımlar → **Karar 2**:

   | Hedef | Öneri: sayılan şey |
   |---|---|
   | Başvuru — 80 | En az bir yetenek kartı olan genç (kayıt olup kart oluşturmayan başvuru sayılmaz) |
   | Kurum — 20 | En az bir ihtiyaç kartı olan kurum |
   | Eşleşme — 10 | Karşılıklı onaylanmış eşleşme (`kabul_edildi`) |
   | Pilot — 5 | Tamamlanmış iş birliği |

2. **Pasifleşen bağlantılar:** Şu an eşiği aşmış kayıtlar, okuma anında aynı kurallarla hesaplanır, hiçbir şey yazılmaz. Her satırda tür, taraflar (adlar), kaç gündür hareketsiz ve son hatırlatmanın tarihi var. En uzun süredir hareketsiz olan önce gelir.
3. **Son Canlılık olayları:** Son 20 olay; tür, alıcının adı, mesaj ve zaman.
4. **"Taramayı şimdi çalıştır":** Düğme ve son taramanın özeti (türe göre sayılar).

**Grafik:** Hedeflerin ilerleme çizgisinin ötesinde bir grafik (ör. eşleşme hunisi) **kesilebilir** (kesim çizgisi 1); sayılar her durumda kalır.

## 8. Uç noktalar ve yetki

| Uç nokta | Kim | Not |
|---|---|---|
| `POST /canlilik/tarama` | GİRVAK ya da `X-Tarama-Anahtari` | Tarama özeti döner; idempotent |
| `GET /canlilik/pasifler` | GİRVAK | Okuma anında pasif kayıtlar; kişisel veri yalnızca ad |
| `GET /canlilik/olaylar` | GİRVAK | Son olaylar (varsayılan 20) |
| `GET /girvak/sayilar` (mevcut) | GİRVAK | `hedefler` eklenir: `{basvuru, kurum, eslesme, pilot}` her biri `{sayi, hedef, program_adi, olcum}` |

**Sözleşme sapması:** `api-contracts.md`'deki `GET /canlilik/hatirlatma/{eslesme_id}`
("üretilen mesajı gösterir") yerine olaylar listesi öneriyorum. Mesaj zaten
bildirimle kişiye ulaşıyor; GİRVAK'ın ihtiyacı liste. Sözleşme güncellenir.

Genç ve kurum bu uçları çağıramaz (403). Onlar hatırlatmayı bildirim olarak görür.

## 9. Kararlar (onaylandı: dördünde de öneri)

1. **Tarama tetikleyicisi:**
   - **Öneri:** B, platform cron'u. Yerelde ve demoda düğme ya da betik.
   - **Alternatif:** A, uygulama içi zamanlayıcı.
2. **Hedef tanımları:** Öneri § 7'deki tablo. "Başvuru" için alternatif: kayıtlı her genç hesabı.
3. **Yeni fırsat ne söyler:** *(Değişti, 28 Eyl: genç akışında genç önerilmiş fırsatları zaten görüyor — `plans/genc-akisi.md` § 0 karar 1; anonimliğin gerekçesi kalmadı. Bildirimin metni ve bağlantısı genç ana sayfası adımında fırsatlar bölümüne yönlenecek.)*
   - **Öneri:** Anonim; kurum adı ve ihtiyaç metni yok, sektör ve "kartını güçlendir" var.
   - **Alternatif:** İhtiyaç kartını gence göstermek; Faz B sahiplik kuralını değiştirir.
4. **Eşik değerleri:** Öneri § 1'deki tablo (7 / 3 ve 10 / 5 / 14 gün, gecikmede 1 gün; fırsatta 7 günlük yeni ihtiyaç ve 14 günlük eski kart).

## 10. Kesilebilir olanlar (roadmap kesim çizgisi)

| Sıra | Kesilen | Kalan |
|---|---|---|
| 1 | GİRVAK panelinin grafik kısmı | Hedef sayıları ve ilerleme çizgisi, pasifler, olaylar, tarama düğmesi |
| 2 | "Yeni fırsat" dalı (§ 2) | Bütün hatırlatma türleri |
| — | LLM kişiselleştirme (§ 5) | Şablon metinler; hatırlatma aynen gider |
| — | Canlıda cron kurulumu (Faz E'ye bağlı) | Düğme ve betik |

**Kesilmez:**
- Hatırlatma türleri, tekrar kuralı ve tarama ucu. Roadmap'in "yaşayan ağ" maddesi bunlardır.
- GİRVAK hedef sayıları.

## 11. Kapsam dışı

- Gerçek e-posta ya da SMS
- Hatırlatma tercihleri, sessize alma
- Davranış tahmini, puanlama
- Canlılık'ın bir kaydın durumunu değiştirmesi (ör. eşleşmeyi otomatik kapatma)
- GİRVAK'ın kullanıcı yönetimi
- Hedeflerin panelden düzenlenmesi (sabit)
- Haftalık rapor

## 12. Uygulama sırası

Onaydan sonra; her adım ayrı commit, en az bir test, adım sonunda kısa özet:

1. Migration (§ 6), pasiflik kuralları ve tekrar kuralı saf fonksiyonlar olarak (§ 1, § 3), tablo testleriyle.
2. Tarama: aday toplama (SQL), şablon metinlerle olay ve bildirim yazımı, danışma kilidi, `POST /canlilik/tarama` (GİRVAK ve anahtar), `scripts/canlilik_taramasi.py`. İdempotentlik testi.
3. LLM kişiselleştirme (hızlı katman, şablona düşer). **Kesilebilir.**
4. Yeni fırsat dalı. **Kesilebilir.**
5. GİRVAK uçları: hedefler, pasifler, olaylar.
6. Frontend: GİRVAK paneli (hedefler, tarama düğmesi ve özeti, pasifler, olaylar), Canlılık bildirimlerinin hedefleri; grafik varsa en son.
7. `scripts/zamani_geri_al.py`, iki pencereli (ve GİRVAK) tarayıcı deneme listesi.
8. Belgeler (api-contracts, data-schema, agent-specs § 5, README, CLAUDE.md, roadmap).
