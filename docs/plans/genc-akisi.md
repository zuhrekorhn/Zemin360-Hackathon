# Plan — Genç akışı: kayıt, onboarding, kart düzenleme, ana sayfa, gençten ilgi

> Durum: **onaylandı (28 Eyl).** Kararlar § 0'da; § 12'deki soruların yanıtları
> oraya işlendi. Planın geri kalanıyla çelişen yerde § 0 geçerlidir.
> Kapsam: yalnızca genç tarafı. Kurum tarafında yalnızca § 7'nin zorunlu kıldığı
> en küçük değişiklikler var (ilgi etiketi, ilgi gösterenler bölümü, "Şimdilik değil").
> Bu belgede önceki fazların **belgelenmiş kararlarını değiştiren** noktalar ⚠ ile
> işaretli. Hepsi § 12'deki açık sorularda da listeleniyor.

---

## 0. Onaylanan kararlar (28 Eyl)

1. **Görünürlük:** Genç `onerildi` eşleşmelerini, kurum ilgilenmeden görür. Ek iki iş:
   - Tanımlama'nın onay ekranına "Onaylanan ihtiyaç, eşleşen adaylara gösterilir" notu eklenir.
   - Faz B (§ 3, § 5) ve Faz D (Karar 3) belgelerindeki eski kararlar gerekçesiyle güncellenir.
2. **Müsaitlik çoklu seçim olur, `staj` dahil** (`kullanici.musaitlikler text[]`).
   - Mevcut tekil değerler migration'la tek elemanlı listeye çevrilir.
   - Filtre "ihtiyacın tercihi gencin listesinde mi" sorusunu sorar. Liste boşsa aday elenmez; `calisma_modelleri`'ndeki kural.
   - Sohbette ayrıca fırsat türü sorulmaz.
3. **En iyi 5 sınırı kalır.** Sayı tek sabitte (`TOP_N`). Belgelere bilinen sınır olarak yazılır: sıralamada 6. ve sonrası olan genç o fırsatı görmez.
4. **İhtiyaç kapanması:** `ihtiyac_karti.durum` alanı ve `ihtiyac_kapandi` kuralı şimdi eklenir. Kurumun "kapat" düğmesi firma görevinde.
5. **`app/servisler/` açılır.** Taşıma tek başına bir commit olur; içinde hiçbir davranış ya da mantık değişikliği bulunmaz; tüm testler geçmeden sonraki adıma geçilmez.
6. **Kurum yanıtsızlığı:** `genc_ilgisi_yanitsiz` eşiği 5 gün, sabit.
7. **Otomatik puanlama:**
   - Linksiz iş kalemi puanlanmaz, "doğrulanmamış" nötr durumda kalır.
   - Linki olan iş kalemi, kart **onaylandığında ve düzenlendiğinde** arka planda otomatik puanlanır. Böylece "sohbette verilen link puanlanmıyor" açığı kapanır.
8. **Referanslar:** İş kaleminin içeriği ya da linki değişince eski referans yanıtları puana girmez ama silinmez. Geçmiş olarak görünür kalır ve gence "referansı yeniden iste" seçeneği sunulur.
   - **Uygulama:** `somut_cikti.icerik_tarihi` (NULL = hiç değişmedi) ve `referans_istegi.yanit_tarihi` alanları eklenir.
   - **Kural:** Bir yanıt puana ancak iki durumda girer: `icerik_tarihi` NULL ise, ya da yanıt `icerik_tarihi`'nden sonra verildiyse.
9. **Gerekçe metni** gence aynen gösterilir; ikinci bir LLM çağrısı yok. Arayüzdeki başlık nötr: "Bu eşleşmenin gerekçesi".
10. **Eski hesaplar** yeni zorunlu alanlar için engellemeyen bir uyarı bandıyla çağrılır. Demo tohum verisi yeni alanlarla güncellenir.
11. **Frontend'e yeni test bağımlılığı eklenmez.** Karar mantığı (durum etiketleri, düğme görünürlüğü, profil eksik mi) `src/lib/` altında saf fonksiyonlara çıkar ve orada test edilir.
12. **Referans kişi Keşif sohbetinde de sorulur** (§ 5.4). E-posta, mevcut `ReferansIstegi` mekanizmasıyla ilgili iş kalemine bağlanır.
13. **Belge düzeltmesi:** `agent-specs.md`'de Doğrulama'nın linkin yalnızca başlık ve açıklamasını okuduğu açıkça yazılır; "içerik analizi" izlenimi veren ifadeler düzeltilir.

14. **İlgi gösterilmiş eşleşme korunur** (28 Eyl, ek kural; 9. adımı etkiler):
    - Pipeline'ın temizlik kuralı yalnızca `onerildi` kayıtlarını silebilir. `genc_ilgilendi`, genç ilgisini gösterdiği için "karar verilmiş kayıt" sayılır.
    - Pipeline bu kaydı **asla silmez**, skorunu ve gerekçesini de **değiştirmez**. (Kurumun karar verdiği `ilgileniliyor`/`kabul_edildi`/`reddedildi` kayıtlarında bugün skor tazeleniyor; `genc_ilgilendi`'de o da yok.)
    - Kayıt, yeniden hesaplamada en iyi 5'in dışına düşse bile kurum yanıtında "İlgi gösterenler" bölümünde görünür. En iyi 5 sınırı yalnızca `onerildi` kayıtlarına uygulanır.
    - Kart düzenlemesinden sonra kart ihtiyaca artık uymasa bile kayıt kalır. Kaydı yalnızca üç şey kapatır: kurumun "Şimdilik değil" demesi, gencin ilgisini geri çekmesi, ihtiyacın kapanması.
    - **Testler (gerçek veritabanı):**
      - (a) Genç ilgi gösterir, sonra daha güçlü 5 kart gelir ve yeniden hesaplanır: kayıt silinmez ve kurum yanıtında görünür.
      - (b) Genç ilgi gösterir, sonra kartını ihtiyaca uymayacak biçimde düzenler: kayıt silinmez.
      - (c) Mevcut `onerildi` temizlik davranışı değişmez.
15. **Arayüz metinleri:** `docs/icerik-rehberi.md`'ye bakınız (28 Eyl'de onaylandı; bu kararın geçici kuralının yerini aldı). Yeni ya da değişen her kullanıcı metni `docs/plans/genc-akisi-metinler.md` listesine eklenir; rehberde karşılığı olmayan terim uydurulmaz, listeye not düşülür. Mevcut metinlere genç akışı bitene kadar dokunulmaz; toplu denetim ayrı bir adım. Kod içindeki alan ve değişken adları (`somut_cikti`, `kurum`…) değişmez.
16. **8. adım ertelendi** (28 Eyl): "Yeni iş ekle" mini sohbeti özellik dondurmasından sonraya kaldı. Gerekçe: 7. adımdaki formla ekleme (`POST /yetenek-kartlari/{id}/ciktilar`) aynı ihtiyacı karşılıyor; mini sohbet üçüncü bir sohbet grafiği, yeni uçlar ve checkpointer kaydı istiyor, takvimde karşılığı yok. `somut_cikti.oturum_id` sütunu (1. adım) yerinde duruyor; ileride tekrar kuralı için kullanılacak.

**Uygulama sırası** (§ 10'un güncel hâli). Her adım ayrı commit; her adımda backend ve frontend testlerinin tamamı:

1. **Eklemeli migration'lar ve modeller.** Yalnızca yeni sütunlar ve varsayılanlar; davranış değişmez.
2. **`app/servisler/`'e taşıma.** Davranış değişmez, tek commit.
3. **Müsaitlik çoklu seçim:** migration, filtre ve testler.
4. **Kayıt formu:** backend, `/kayit`, `PATCH /profil`, `/profil`, demo tohum verisi, uyarı bandı.
5. **`karti_hazirla`:** otomatik puanlama ve yeniden eşleştirme; Keşif onayına bağlanır.
6. **Keşif sohbeti:** bağlam, iş kalemi alanları, referans; onboarding yönlendirmesi.
7. **Kart düzenleme:** versiyon, doğrulama sıfırlama, referans geçmişi ve yeniden iste.
8. ~~**"Yeni iş ekle"** mini sohbeti.~~ **Ertelendi** (karar 16).
9. **İlgi durum makinesi** ve ihtiyaç kapanma kuralı.
10. **Genç ana sayfası** ve kurum tarafındaki en küçük değişiklikler; Tanımlama onay notu.
11. **Canlılık `genc_ilgisi_yanitsiz`.**
12. **Belgeler.**

---

## 1. Doğrulama Ajanı bugün ne yapıyor? (rapor, değişiklik yok)

### 1.1 Kanıt linkiyle yapılan

`app/agents/dogrulama.py` › `linki_kontrol_et`:

- Linkin başında şema yoksa başa `https://` eklenir (`github.com/…` → `https://github.com/…`).
- Sunucu linke `GET` isteği atar: 8 sn zaman aşımı, yönlendirmeler izlenir.
- Yanıt başarılı değilse ya da ağ hatası olursa link "açılmıyor" sayılır.
- Sayfanın **yalnızca `<head>` kısmı** okunur (`</head>` görülene ya da 300 KB'a kadar). Oradan iki şey alınır, toplam en çok 400 karakter:
  - `<title>`, yoksa `og:title`,
  - `meta description`, yoksa `og:description`.
- **İçerik incelenmez.** GitHub reposunun dili, README'si, commit geçmişi, dosyaları okunmaz. Bu, `agent-specs.md` § 4'te bilinçli bir sınır ("Kod/commit geçmişi analiz etmez").
  - Yani bir GitHub linki için modelin gördüğü şey, repo sayfasının başlığı ve kısa açıklaması; örneğin "kullanici/proje: Mahalle kütüphanesi takip sistemi".

### 1.2 Güven puanının 4 bileşeni

Her bileşen 0-3 arası. Tek sayıya indirilmez, yan yana gösterilir.

| Bileşen | Kim hesaplar | Nasıl |
|---|---|---|
| `kanit_orijinalligi` | LLM (güçlü katman) | Rubrik: 0 link yok ya da açılmıyor · 1 açılıyor ama iddiayla ilgisiz · 2 ilgili ama kişinin kendi işi olduğu belirsiz · 3 işin kendisine götürüyor. **Kural:** link açılmıyorsa LLM ne derse desin 0'a çekilir. |
| `sonuc_olculebilirligi` | LLM | 0 sonuç yok · 1 yalnızca niteliksel · 2 sayı var ama neyin ölçüsü belirsiz · 3 sayı ve ölçtüğü açık |
| `rol_netligi` | LLM | 0 yazmıyor · 1 "katkıda bulundum" gibi belirsiz · 2 rol var ama ekipteki payı belirsiz · 3 açık ve spesifik |
| `ucuncu_taraf_onayi` | **Kural, LLM değil** | Referansın 1-5 puanı 0-3'e çevrilir (1→0, 2→1, 3→1, 4→2, 5→3). Yanıt veren **tüm** referansların ortalaması alınır, 0.5 yukarı yuvarlanır. Referans yoksa 0. |

**LLM'e giden girdi:** başlık, açıklama (Keşif'te toplanan sonuç ve rol de bu açıklamanın içine birleştiriliyor), link, linkin açılıp açılmadığı, `<head>`'den okunan özet, varsa itiraz notu. İtiraz notu "beyan" sayılıyor ve tek başına en çok bir basamak yükseltiyor.

**Eşleştirmeye etkisi:** Çıktı başına bileşenlerin toplamı 12'ye bölünür, puanlanmış çıktıların ortalaması alınır. Puanlanmamış çıktılar ortalamaya **girmez**; 0 olarak sayılmaz. Buna tamamlanmış pilot bonusu (+0.5) eklenir, toplamın tavanı 1.0. Sonuç skora 0.25 ağırlıkla girer.

### 1.3 Ne zaman çalışıyor, kanıt nereden geliyor

- **Rubrik yalnızca iki uçta çalışıyor:** `POST /dogrulama/kanit-ekle` ve `POST /dogrulama/itiraz`. İkisini de genç, kart sayfasında (`/kart/{id}`) kendisi tetikliyor.
- **Kart onaylanınca otomatik puanlama yok.** Sohbette verilen link kaydediliyor ama puanlanmıyor. Kart sayfası bunu "Bu kanıt henüz değerlendirilmedi" diye gösteriyor ve gencin basmasını bekliyor.
- **Kanıt linki iki yerden toplanıyor:**
  1. Keşif sohbetinde, iş kalemi başına (`SomutCiktiTaslak.kanit_linki` → `somut_cikti.kanit_linki`). Yani zaten iş kalemine bağlı, karta genel bir liste olarak değil.
  2. Kart sayfasındaki formdan, yine iş kalemi başına (`kanit-ekle`).
- **Referans kişi yalnızca kart sayfasından** ekleniyor; sohbette sorulmuyor. Referans linki e-postayla gitmiyor, genç kendisi iletiyor.
- **`kanit_bekleyen` bayrağı:** Kartın linksiz en az bir iş kalemi varsa `true`.

---

## 2. Mevcut durum özeti (bu görevi ilgilendiren kısmı)

- **Kayıt** (`POST /auth/kayit`): e-posta, şifre, rol, ad. Şehir, çalışma modeli ve müsaitlik **kart onayında** soruluyor (`KartOnaylaIstegi.profil`). Şehir yoksa onay 422 dönüyor.
- **Profil** (`kullanici`): `ad, email, sehir, calisma_modelleri[], musaitlik` (tek değer: `tam_zamanli | yarim_zamanli | proje_bazli | staj`). Profil düzenleme ucu yok.
- **Kart** (`yetenek_karti`, `somut_cikti`): Kart onaydan sonra değişmiyor, `versiyon` hep 1. Keşif'in topladığı sonuç ve rol bilgisi `aciklama` alanına birleştirilerek kaydediliyor.
- **Eşleştirme** yalnızca üç durumda çalışıyor: ihtiyaç kartı onaylanınca (arka planda), kurum "Yeniden hesapla" deyince, ve bir ihtiyaç kartının önerileri hiç hesaplanmamışsa `GET /oneriler` açılınca. **Yeni ya da değişen yetenek kartı eşleştirmeyi tetiklemiyor.** Pipeline ihtiyaç kartı başına en iyi 5 adayı (`TOP_N`) ve %40 eşiğini geçenleri yazıyor.
- **Eşleşme durumu:** `onerildi → ilgileniliyor (kurum) → kabul_edildi | reddedildi (genç)`. Kural `eslesme_durumu.gecis`'te. Genç, eşleşmeyi `onerildi` iken **görmüyor** (Faz B § 3, `GENCE_ACIK_DURUMLAR`).
- **Arka plan deseni:** `BackgroundTasks`, kendi oturumu, hata yutulur. İdempotentlik ihtiyaç kartı başına danışma kilidi (`pg_advisory_xact_lock`) ve `ON CONFLICT DO NOTHING` ile sağlanıyor. Testler bu işleri `tests/conftest.py`'de sahteyle değiştiriyor.
- **Frontend test altyapısı** yalnızca `src/lib/**/*.test.ts`: tarayıcısız saf fonksiyon testleri. Bileşen testi kütüphanesi yok (Testing Library ve jsdom kurulu değil).

---

## 3. Veri modeli ve migration'lar

Hepsi Alembic ile, `downgrade`'li. Yeni sütunlar nullable ya da varsayılanlı olacak, mevcut satırlar bozulmayacak.

### 3.1 `hesap`
- `kvkk_onay_tarihi timestamptz NULL`.
- **Neden profilde değil de hesapta:** Onay bir kişinin/hesabın; bir sonraki görevde firma hesapları da aynı alanı kullanacak.
- Mevcut hesaplarda NULL kalır. Bu hesaplar giriş yapmaya devam eder; panel onaylarını ister (§ 12, Soru 9).

### 3.2 `kullanici` (mevcut alanlar genişletilir, yenisi açılmaz)

| Alan | Tip | Not |
|---|---|---|
| `sehir`, `calisma_modelleri` | mevcut | Artık kayıtta zorunlu |
| `musaitlik` | mevcut | ⚠ § 12, Soru 3: tek değer mi kalacak, çoklu seçime mi dönecek |
| `kariyer_durumu` | `text NULL` | `ogrenci \| mezun \| calisiyor`. Kodlar `app/core/kariyer_durumu.py`'de (musaitlik.py deseni). Kayıtta zorunlu, eski satırda NULL |
| `okul`, `bolum` | `text NULL` | |
| `sinif` | `smallint NULL` | Öğrenci için |
| `mezuniyet_yili` | `smallint NULL` | |
| `musaitlik_baslangici` | `date NULL` | "Başlangıç tarihi" |
| `github_url`, `linkedin_url`, `portfolyo_url` | `text NULL` | Yalnızca http(s) URL kabul edilir |

Bilinçli olarak eklenmeyenler: fotoğraf, yaş/doğum tarihi, cinsiyet, medeni durum, TC kimlik no, adres, ücret beklentisi. Bu ilke `data-schema.md`'ye de yazılacak.

### 3.3 `yetenek_karti`
- `sertifikalar text[] default '{}'`, `diller text[] default '{}'` (ikisi de opsiyonel).
- `versiyon` artık her kart değişikliğinde artar.

### 3.4 `somut_cikti` (iş kalemi)

| Alan | Tip | Not |
|---|---|---|
| `is_turu` | `text NULL` | `proje \| staj \| is \| gonulluluk \| yarisma` |
| `kendi_rolu` | `text NULL` | Bugün `aciklama`'ya birleştiriliyor; düzenlenebilmesi için ayrı alan |
| `olculebilir_sonuc` | `text NULL` | Aynı gerekçe |
| `icerik_tarihi` | `timestamptz default now()` | İçeriğin (başlık, açıklama, rol, sonuç, link) son değiştiği an. Doğrulama sıfırlama ve referans geçerliliği buna bakar (§ 6.3) |

- Rubrik ve embedding metni bu üç alanı `aciklama`'yla birlikte okuyacak. Birleştirme tek bir yardımcı fonksiyonda yapılacak.
- **Eski satırlar:** Yeni alanlar NULL kalır; `aciklama` birleşik metni zaten taşıyor, anlam kaybı yok.

### 3.5 `eslesme` (gençten ilgi için genişletme — § 7)

| Alan | Tip | Not |
|---|---|---|
| `baslatan` | `text NULL` | `genc \| kurum`: ilk ilgiyi kim gösterdi. Eski `ilgileniliyor`/`kabul_edildi`/`reddedildi` satırları migration'da `kurum` olur |
| `genc_ilgi_tarihi` | `timestamptz NULL` | |
| `genc_iletisim_onayi_tarihi` | `timestamptz NULL` | "Kurum da ilgilenirse e-postam paylaşılsın" onayı |
| `kurum_ilgi_tarihi` | `timestamptz NULL` | |

`durum` için iki yeni değer: `genc_ilgilendi` ve `kapandi`.

### 3.6 `ihtiyac_karti`
- ⚠ **"Kapanma" alanı:** § 12, Soru 5'e bağlı. Önerim `durum text default 'acik'` (`acik | kapandi`).

### 3.7 Migration sırası
Her biri ayrı migration: 3.1 + 3.2 → 3.3 + 3.4 → 3.5 (+3.6). Her biri `alembic upgrade` / `downgrade` ile sınanır.

---

## 4. Durum geçişleri (§ 7 "ilgileniyorum")

### 4.1 Karar: tek `durum` alanı genişletiliyor, türetilmiş durum değil

**Gerekçe:** `durum` bugün çok yerde okunuyor: pipeline temizliği, Canlılık kuralları, GİRVAK sayıları, sahiplik, bildirim hedefleri, Faz B ve C testleri. Durumu alanlardan türetmek bunların hepsini yeniden yazmayı gerektirir.

Bunun yerine `durum` tek doğruluk kaynağı olarak kalıyor. Yeni tarih alanları yalnızca "kim, ne zaman" bilgisini taşıyor, hiçbir karar onlara bakmıyor. Görünen üç durum (Beklemede / Karşılıklı ilgi / Kapandı) arayüzde `durum`'dan çevriliyor.

### 4.2 Geçiş tablosu

Kural tek yerde: `app/agents/eslesme_durumu.py` › `gecis(durum, olay, rol)`. Tablo `(olay, kaynak) → (kim, hedef)` biçimine genişliyor. Mevcut satırlar **aynen** kalıyor.

| Şu an | Olay | Kim | Sonra | Yan etki |
|---|---|---|---|---|
| `onerildi` | `ilgileniyorum` | kurum | `ilgileniliyor` | Mevcut: gence bildirim |
| `ilgileniliyor` | `kabul` | genç | `kabul_edildi` | Mevcut: iş birliği, iletişim, plan önerisi |
| `ilgileniliyor` | `red` | genç | `reddedildi` | Mevcut |
| `onerildi` | `genc_ilgi` | genç | `genc_ilgilendi` | **Yeni.** Eşik kuralı (§ 4.3), iletişim onayı zorunlu, kuruma bildirim |
| `genc_ilgilendi` | `ilgiyi_geri_cek` | genç | `onerildi` | **Yeni.** İlgi tarihleri temizlenir |
| `genc_ilgilendi` | `ilgileniyorum` | kurum | `kabul_edildi` | **Yeni: karşılıklı ilgi.** Genç ayrıca onay vermez; iş birliği açılır, iletişim açılır, plan önerisi başlar (kabul ucuyla aynı yan etki fonksiyonu). İki tarafa bildirim |
| `genc_ilgilendi` | `simdilik_degil` | kurum | `kapandi` | **Yeni.** Gence nötr bildirim: "…kapandı" |
| `onerildi`, `genc_ilgilendi`, `ilgileniliyor` | `ihtiyac_kapandi` | sistem | `kapandi` | **Yeni.** § 12, Soru 5'e bağlı |

**Genel kurallar:**
- Tablo dışı her geçiş 409 döner ve mevcut durumu söyler (mevcut davranış).
- Aynı geçişin tekrarı 200 döner, yan etkisi olmaz (mevcut davranış).
- `ilgiyi_geri_cek` yalnızca karşılıklı olmadan önce mümkün; `kabul_edildi`'de 409.

**Görünen durumlar:**

| `durum` | Genç görür | Kurum görür |
|---|---|---|
| `onerildi` | Sana uygun | Aday |
| `genc_ilgilendi` | Beklemede | Aday + "İlgi gösterdi" etiketi |
| `ilgileniliyor` | Kurum ilgileniyor (mevcut kabul/ret ekranı) | Beklemede |
| `kabul_edildi` | Karşılıklı ilgi | Karşılıklı ilgi |
| `kapandi`, `reddedildi` | Kapandı | Kapandı / Reddedildi |

### 4.3 Eşik kuralı (backend'de)

Saf fonksiyon `ilgi_gosterilebilir_mi(eslesme)`: kayıt var, gencin kartına ait, `skor >= SKOR_ESIGI` ve ihtiyaç kartı açık. Değilse 404 (başkasının ya da gencin göremediği kayıt) veya 409 (eşik altı, kapalı).

Eşik altı bir aday için zaten eşleşme kaydı yazılmıyor. Kural yine de saf fonksiyonda duruyor ve testle sabitleniyor.

### 4.4 İletişim bilgisi
`eslestirme.iletisim()` yine yalnızca `kabul_edildi`'de ve yalnızca iki tarafa açıyor. Karşılıklı ilgi `kabul_edildi`'ye çıktığı için ayrıca bir kural gerekmiyor. Test: `genc_ilgilendi` ve `onerildi`'de hiçbir yanıtta e-posta yok.

---

## 5. Onboarding ve Keşif sohbeti

### 5.1 Kayıt
- `KayitIstegi`'ne `genc_profili: GencKayitProfili | None` eklenir. `rol == "genc"` ise zorunlu, `kurum` ise gönderilmez.
- Kurum kaydı değişmez.
- KVKK onayı `kvkk_onay: Literal[True]` olarak gelir; sunucu tarihi yazar.

**Doğrulamalar:**
- Şehir kanonik listeden (`sehir_kanonik`).
- Çalışma modelleri: en az bir tane, tanınan kodlar.
- Durum ve müsaitlik: tanınan kodlar.
- Sınıf 1-8 (hazırlık dahil), mezuniyet yılı 1950 ile bu yıl+8 arası.
- URL'ler http(s).

**Etkilenen yerler:** Test yardımcıları ve `scripts/demo_hesaplari.py` genç kaydını yeni alanlarla yapacak şekilde güncellenecek. Bu bir API sözleşmesi değişikliği; `api-contracts.md` güncellenecek.

### 5.2 Akış
- Kayıttan sonra `/kesif?ilk=1` açılır.
- Sohbetin başında "Şimdilik atla" düğmesi var; basınca `/genc`'e gider.
- **"Profil eksik"** saklanan bir durum değil, **türetiliyor**: onaylı yetenek kartı yoksa eksik. `/me` yanıtına `profil_eksik: bool` eklenir.
  - Kartı olmayan genç zaten eşleştirmeye girmiyor; yeni bir kural gerekmiyor.
- `/kesif` onay formundaki şehir, çalışma modeli ve müsaitlik soruları kalkar; bunlar artık kayıtta.
  - Şehri olmayan **eski** hesaplarda form bu alanları göstermeye devam eder. Onaydaki 422 kuralı korunuyor.

### 5.3 Keşif sohbetine profil bağlamı
- `AjanTanimi`'na isteğe bağlı bir `baglam` eklenir. Sohbet açılırken durum içine yazılır; çıkarım düğümü onu sistem talimatının hemen arkasına ikinci bir `SystemMessage` olarak ekler.
  - Motorun geri kalanı değişmez; Tanımlama bu alanı kullanmaz.
- **Bağlam metni:** şehir, çalışma modeli, müsaitlik, durum, okul ve bölüm. Talimatta: "Bu bilgileri SORMA."
- **Deterministik güvence:** Sabit soruların ve ek soruların hiçbiri bu alanları sormuyor. Model bu alanlardan birini `takip_konusu` olarak işaretlerse soru kullanılmaz; bu, mevcut `zorunlu_alan_sorusu` kuralının genişletilmiş hâli.
  - Test: bağlam istem metnine giriyor; modelin form alanını soran önerisi elenip sabit soru soruluyor.

### 5.4 Sohbette toplanacaklar ve istem güncellemesi
- Mevcut istem baştan yazılmıyor; eklemeler:
  - iş kaleminin türü,
  - kanıt linki **ve** referans kişinin e-postası (iş kalemi başına),
  - opsiyonel sertifika ve dil,
  - "beceri seviyesini soyut sorma, örnekle ortaya çıkar" yönergesi.
- **Aradığı fırsat türü:** § 12, Soru 3'e bağlı. Müsaitlik kayıtta alınıyor; ikisi büyük ölçüde örtüşüyor.
- **Ek sorular:** Bugün iş kalemi başına rol ve sonuç soruluyor, tavan toplam 2. Yeni sıra: rol → sonuç → "Bu işi gösteren bir link ya da işini doğrulayabilecek biri var mı?"
  - Kanıt ve referans tek soruda soruluyor ki sohbet uzamasın.
  - Tavan toplam **4**'e çıkıyor (her soru bir kez, "bilmiyorum"da ısrar yok; mevcut kural).
- **Referans e-postası:** Kart onayında ilgili iş kalemine `ReferansIstegi` olarak yazılır. Geçersiz e-posta sessizce atılır ve önizlemede düzeltilebilir.
- **Korunanlar:** "Hiç projem yok" zinciri ve "potansiyel" kuralı aynen kalıyor.

### 5.5 Onaydan sonra (arka plan)
Yeni arka plan işi: `karti_hazirla(kart_id, versiyon)`. Mevcut desenle aynı: `BackgroundTasks`, kendi oturumu, hata yutulur, `conftest.py`'de sahteyle değiştirilir.

Sırasıyla:
1. **Embedding.** Onayda bugün olduğu gibi senkron hesaplanıyor. Burada yalnızca eksikse ya da kart değiştiyse yeniden hesaplanır.
2. **Doğrulama puanlaması.** Linki olan ve `guven_skoru` olmayan iş kalemleri puanlanır (⚠ § 12, Soru 6). Linksiz iş kalemi puanlanmaz; mevcut "kanıtsız = bonus yok, ceza yok" ilkesi.
3. **Yeniden eşleştirme** (§ 6.4).

**İdempotentlik:**
- İş kart başına danışma kilidiyle sıraya girer.
- İş başında `kart.versiyon` beklenen değerden büyükse çıkar; daha yeni bir iş zaten sırada.
- Puanlanmış iş kalemi yeniden puanlanmaz.
- Eşleştirme mevcut ihtiyaç kartı kilidini ve `ON CONFLICT`'i kullanır.

---

## 6. Kart ve profil düzenleme

### 6.1 Yeni uçlar

| Uç | Kim | Ne yapar |
|---|---|---|
| `PATCH /profil` | genç (kendi) | Kayıt formundaki alanlar. Boş gelen alan silinmez (mevcut kural); URL'ler boş dizeyle silinebilir |
| `PATCH /yetenek-kartlari/{id}` | kartın sahibi | Rol, deneyim, sektör, araçlar, sertifikalar, diller |
| `POST /yetenek-kartlari/{id}/ciktilar` | kartın sahibi | İş kalemi ekler (formdan) |
| `PATCH /yetenek-kartlari/{id}/ciktilar/{cid}` | kartın sahibi | Başlık, tür, açıklama, rol, sonuç, kanıt linki |
| `DELETE /yetenek-kartlari/{id}/ciktilar/{cid}` | kartın sahibi | |
| `POST /kesif/is-ekle/baslat` · `/cevap` · `/onayla` | kartın sahibi | "Yeni iş ekle" mini sohbeti (§ 6.5) |

Referans ekleme mevcut `POST /dogrulama/kanit-ekle` ile yapılmaya devam ediyor.

**Hata sözleşmesi:** Başkasının kartı ya da iş kalemi **404**, yanlış rol **403**, token yok **401**. Her uç için `test_sahiplik.py` deseniyle test yazılacak.

### 6.2 Kart değişikliği kuralları (saf fonksiyonlar, `app/agents/kart_duzenleme.py`)
- `versiyon_artmali_mi(eski, yeni) -> bool`: yalnızca gerçekten bir alan değiştiyse. Aynı değerle gelen PATCH versiyonu artırmaz.
- `dogrulama_sifirlanmali_mi(eski_kalem, yeni_kalem) -> bool`: başlık, açıklama, rol, sonuç ya da kanıt linki değiştiyse `True`. Yalnızca iş türü değiştiyse `False`.
- `yeniden_eslestirme_gerekir_mi(degisen_profil_alanlari) -> bool`: şehir, çalışma modeli ya da müsaitlik değiştiyse `True`. Okul, durum, linkler gibi alanlar için `False`.

### 6.3 Doğrulama sıfırlama
Değişen iş kaleminde:
- `guven_skoru` silinir,
- `icerik_tarihi = now()` olur,
- kanıt linki varsa kalem arka planda yeniden puanlanır.

Değişmeyen kalemlere dokunulmaz.

⚠ **Referanslar** (§ 12, Soru 7): Önerim, `ucuncu_taraf_onayi`'nın yalnızca `icerik_tarihi`'nden **sonra** yanıtlanmış referanslardan hesaplanması. Eski yanıtlar geçmiş olarak görünür ama puana girmez. Böylece "önce gerçek kanıtla puan al, sonra metni şişir" yolu referans tarafında da kapanır.

### 6.4 Yeniden eşleştirme (açık: "sonradan gelen genç")
- Yeni fonksiyon: `yetenek_kartini_eslestir(oturum, kart)`.
- Mevcut pipeline'ı ihtiyaç kartı başına çağırır; yeni bir eşleştirme mekanizması kurulmuyor.
- Hangi ihtiyaç kartları için:
  - (a) Bu kartla benzerliği alt sınırı (0.45) geçen **açık** ihtiyaç kartları (tek SQL sorgusu).
  - (b) Bu kartın hâlâ `onerildi` kaydı olan ihtiyaç kartları; kart artık uymuyorsa kayıt temizlensin diye.
- Kart değiştiyse bu kartın `onerildi` kayıtlarının gerekçesi boşaltılır; pipeline yenisini yazar. Karar verilmiş kayıtlara dokunulmaz; bu da mevcut kural.
- **Yan etki (mevcut davranış):** Pipeline en iyi 5'i seçtiği için yeni gelen güçlü bir kart, o ihtiyacın 5. sıradaki `onerildi` önerisini listeden düşürebilir. Kurum "Yeniden hesapla" dediğinde de bugün aynısı oluyor. Kurum yeni öneri için bildirim alır (mevcut `yeni_oneri`).
- **Katman:** § 11'e bakın.

### 6.5 "Yeni iş ekle" mini sohbeti
- İkinci bir `AjanTanimi` (`KESIF_IS_EKLE`), aynı motor.
- Açılış sorusu: "Yeni işini anlat."
- Zorunlu alan: başlık. Ek sorular: rol → sonuç → kanıt/referans (tavan 3).
- "Hiç projem yok" dalı yok. Rol ve beceri gibi kart geneli alanlar sorulmaz.
- Checkpointer'a üçüncü grafik olarak kaydedilir (`app.state.is_ekle_grafigi`).
- Onayda: önizlenen iş kalemi karta eklenir, versiyon artar, `karti_hazirla` çalışır. Aynı `oturum_id` ile ikinci onay yeni iş kalemi açmaz (Faz A tekrar kuralı). Bunun için `somut_cikti.oturum_id UNIQUE NULL` alanı eklenir (§ 3.4'e eklenecek).

---

## 7. Genç ana sayfası (`/genc`) ve yeni okuma uçları

| Uç | Ne döner |
|---|---|
| `GET /eslestirme/firsatlarim` | Gencin kartlarının `onerildi` ve `genc_ilgilendi` eşleşmeleri: ihtiyaç kartı, kurum adı, uyum yüzdesi (`round(skor×100)`), gerekçe |
| `GET /eslestirme/ilgilerim` | Gencin başlattığı ilgiler ve görünen durumları |
| `GET /yetenek-kartlari/{id}/guclendir` | "Kartını güçlendir" satırları |

- **⚠ Görünürlük değişikliği** (§ 12, Soru 1): Bu, Faz B'nin "genç `onerildi`'yi görmez" kararını ve Faz D'nin "yeni fırsat anonim" kararını değiştiriyor. `GENCE_ACIK_DURUMLAR` ve `ihtiyac_kartini_gorebilir_mi` buna göre genişler.
- **"Neden sana uygun":** Mevcut gerekçe metni aynen kullanılır; ek LLM çağrısı yok. Metin 3. şahısla, kuruma hitaben yazılıyor ("…bu kartın önerilmesinin nedeni…"). ⚠ § 12, Soru 8.
- **"Kartını güçlendir"** (saf fonksiyon `guclendirme_etkisi`, LLM yok):
  - Her kanıtsız ya da puanlanmamış iş kalemi için şu varsayılır: o kaleme orijinalliği 3 olan bir kanıt eklendi, diğer bileşenler aynı kaldı.
  - Bu varsayımla kartın yeni skoru hesaplanır.
  - Gencin görebildiği fırsatlarda, yeni skorla sıralamasının kaç tanesinde yükseldiği sayılır.
  - Metin şablondur: "Bu işe kanıt eklersen {n} fırsatta öne çıkabilirsin." n = 0 ise "Kanıt, yeni fırsatlarda kartını güçlendirir."
  - Metin yine de "girdide olmayan sayı yok" denetiminden geçer (Canlılık'taki `kisisel_metin_gecerli_mi` ile aynı mantık).
- **Sayfa bölümleri:** en üstte "Kartını tamamla, kurumlar seni görebilsin" (profil eksikse) → Sana uygun fırsatlar → Kartını güçlendir → İlgilerim → Bana gelen ilgiler (mevcut) → İş birliklerim (mevcut).

### 7.1 Gençten ilgi uçları

| Uç | Kim | Geçiş |
|---|---|---|
| `POST /eslestirme/{id}/genc-ilgi` | genç | `{iletisim_onayi: true}` zorunlu; `onerildi → genc_ilgilendi` |
| `POST /eslestirme/{id}/ilgiyi-geri-cek` | genç | `genc_ilgilendi → onerildi` |
| `POST /eslestirme/ilgileniyorum` | kurum | Mevcut uç; `genc_ilgilendi`'de karşılıklı ilgi |
| `POST /eslestirme/{id}/simdilik-degil` | kurum | `genc_ilgilendi → kapandi` |

- **Kurum tarafında en küçük değişiklik:**
  - `OneriYaniti`'na `genc_ilgi_gosterdi: bool` ve `durum` eklenir.
  - Öneriler sayfasında "İlgi gösterdi" etiketi, "İlgi gösterenler" bölümü ve "Şimdilik değil" düğmesi olur.
  - Sıralama ve skor değişmez.
- **Canlılık:**
  - Yeni tür `genc_ilgisi_yanitsiz`: kuruma, **5 gün** sonra, tek kademe (⚠ § 12, Soru 4).
  - Eşik ve kural `canlilik_kurallari.py`'deki tabloya eklenir; tekrar kuralı mevcut hâliyle geçerli.
  - `yeni_firsat` bildiriminin bağlantısı gencin kart sayfası yerine `/genc#firsatlar` olur.

---

## 8. Frontend

- `/kayit`: Rol genç seçilince yeni alanlar görünür. İstemci tarafı doğrulama `src/lib/kayit.ts`'de (saf, testli). Kayıttan sonra `/kesif?ilk=1`'e gidilir.
- `/kesif`: "Şimdilik atla" düğmesi. Onay formunda profil alanları eski hesaplar dışında kalkar. İş kalemi önizlemesinde tür, rol, sonuç, link ve referans düzeltilebilir.
- `/genc`: § 7'deki bölümler.
- `/kart/[id]`: "Düzenle" modu (alanlar ve iş kalemleri) ve "Yeni iş ekle" (mini sohbet, mevcut `sohbet.tsx` parçaları).
- `/profil`: yeni sayfa; genç profil düzenleme.
- `/kurum/oneriler`: etiket, bölüm ve düğme (§ 7.1).
- `src/lib/api.ts`: yeni tipler ve çağrılar, backend şemalarıyla birebir.
- **Testler:** ⚠ § 12, Soru 10. Bugünkü desen saf fonksiyon testi. Önerim: görünüm mantığını `src/lib/` altına çıkarıp orada test etmek. Bunlar durum etiketleri, kayıt doğrulaması, onboarding yönlendirmesi ve güçlendir metni. Gerçek bileşen testi için `@testing-library/react` ve `jsdom` eklemek gerekiyor; bu yeni bir bağımlılık.

---

## 9. Test planı (backend)

| Konu | Test |
|---|---|
| İlgi geçişleri | § 4.2 tablosu birebir. Her geçerli geçiş, her rol için geçersiz geçiş (409 ve mesajı), tekrarın 200 ve yan etkisiz olması, mevcut Faz B tablosunun değişmediği |
| Eşik | Eşik altı ya da kapalı ihtiyaca `genc-ilgi` → 409. `ilgi_gosterilebilir_mi` tablo testi |
| İletişim | `onerildi` ve `genc_ilgilendi`'de hiçbir yanıtta e-posta yok. Karşılıklı ilgide iki tarafa var, GİRVAK'a `null` |
| İletişim onayı | `iletisim_onayi` yoksa ya da `false`sa 422 |
| Doğrulama sıfırlama | Değişen kalemin `guven_skoru`'su silinir; değişmeyeninki korunur. Yalnızca iş türü değişince korunur. `icerik_tarihi` öncesi referans puana girmez |
| Versiyon | Gerçek değişiklikte +1, aynı değerde değişmez |
| Yeniden eşleştirme | Onay, kart düzenleme ve filtre alanı değişikliğinde `karti_hazirla` sıraya girer; okul ya da link değişince girmez. İki kez çalıştırınca eşleşme satırı ve bildirim çiftlenmez (gerçek DB testi) |
| Sonradan gelen genç | Önce ihtiyaç, sonra yetenek kartı → `karti_hazirla` sonrası eşleşme kaydı var |
| Yetki | Yeni her uç için 401/403/404 matrisi (`test_sahiplik.py` deseni) |
| Kayıt | Zorunlu alan eksikliği, geçersiz şehir/kod/URL, KVKK `false` → 422. Kurum kaydı değişmedi. Toplanmayan alanlar gönderilirse yok sayılır ya da 422 döner |
| Keşif bağlamı | Bağlam istem metnine giriyor; form alanını hedefleyen model sorusu elenip sabit soru soruluyor; ek soru sırası ve tavan 4 |
| Güçlendir | `guclendirme_etkisi` tablo testleri; metinde girdide olmayan sayı yok |
| Canlılık | `genc_ilgisi_yanitsiz` eşiği ve tekrar kuralı |

LLM ve Voyage çağrıları testlerde sahte. Yeni arka plan işleri `conftest.py`'ye eklenecek.

---

## 10. Uygulama sırası

Her adım ayrı commit; her adım sonunda backend ve frontend testlerinin tamamı çalışır.

1. **Migration'lar ve modeller** (§ 3). Davranış değişmez.
2. **Kayıt formu** (backend + `/kayit`) ve `PATCH /profil`, `/profil` sayfası.
3. **`karti_hazirla` arka plan işi** ve `yetenek_kartini_eslestir`; Keşif onayına bağlanır. Sonradan gelen genç açığı burada kapanır.
4. **Keşif sohbeti:** profil bağlamı, iş kalemi alanları, referans, ek soru sırası; onboarding yönlendirmesi ve "Şimdilik atla".
5. **Kart düzenleme uçları** ve kuralları (versiyon, doğrulama sıfırlama); `/kart/[id]` düzenleme modu.
6. **"Yeni iş ekle"** mini sohbeti.
7. **İlgi durum makinesi** genişlemesi ve uçları (backend).
8. **Genç ana sayfası** (`/genc`): fırsatlar, güçlendir, ilgilerim; kurum tarafında en küçük değişiklik.
9. **Canlılık** `genc_ilgisi_yanitsiz`.
10. **Belgeler:** `api-contracts.md`, `architecture.md`, `data-schema.md`, `agent-specs.md` § 1 ve § 3, `faz-b` notuna değişiklik notu, README, CLAUDE.md.

---

## 11. Katman kararı (onay gerekiyor)

Projede bugün `app/services/` benzeri bir katman yok. Desen şu:

- `app/agents/`: saf kurallar ve LLM çağrıları.
- `app/api/`: uçlar ve orkestrasyon (veritabanı, bildirim, arka plan işi).

Eşleştirme pipeline'ı (`_pipeline_calistir`) `app/api/eslestirme.py` içinde duruyor. Bu görevde pipeline üç yerden çağrılacak: ihtiyaç onayı, kart hazırlama ve profil değişikliği.

**Öneri:**
- Pipeline'ı ve yeni orkestrasyonları (`karti_hazirla`, `yetenek_kartini_eslestir`, ilginin yan etkileri) yeni bir `app/servisler/` klasörüne taşımak.
- Uçlar ince kalır.
- Taşıma davranış değiştirmez; önce taşıma, ayrı bir commit olarak.

**Alternatif:** Mevcut desende kalmak; yeni fonksiyonlar `app/api/` modüllerinde durur.

**Kart sahipliği:** Yeni kodda sahiplik kontrolleri yalnızca `sahiplik.py` üzerinden yapılacak. Kart sahibinin hesabına tek bir `kart_sahibi_hesap_id(kart)` yardımcısıyla ulaşılacak. Bir sonraki görevde firma da kart sahibi olduğunda değişiklik bu iki yerde kalır. Bu görevde `kullanici_id` FK'si değiştirilmiyor.

---

## 12. Açık sorular (onayla birlikte yanıt gerekiyor)

1. **⚠ Görünürlük (Faz B § 3 ve § 5, Faz D Karar 3):** Genç artık `onerildi` eşleşmelerini, yani kurum adını ve ihtiyaç kartını, kurum ilgilenmeden görecek. Görev metni bunu istiyor. Bu kararların değişmesini onaylıyor musun? Onaylarsan ilgili belgelere değişiklik notu düşeceğim.
2. **Fırsat havuzu:** Pipeline ihtiyaç başına en iyi 5'i yazıyor. 6. sıradaki, eşik üstü bir genç o ihtiyacı fırsat olarak görmeyecek.
   - **Öneri:** Şimdilik 5'te kalmak; kurum listesi ve LLM maliyeti değişmez.
   - **Alternatif:** Eşik üstü tümünü yazmak, kuruma yine ilk 5'i göstermek, gerekçeyi yalnızca gösterilenlere üretmek.
3. **Müsaitlik ve fırsat türü:** Bugün `musaitlik` tek değer, dört kod (`staj` dahil) ve eşleştirmede düz eşitlik filtresi. Görev kayıtta "tam / yarı / proje", sohbette "aradığı fırsat türü: staj / proje / yarı / tam" istiyor; ikisi örtüşüyor.
   - **Öneri:** Profilde çoklu seçim `musaitlikler[]`, dört kodun hepsiyle. Filtre "ihtiyacın tercihi gencin listesinde" olur; liste boşsa elenmez (`calisma_modelleri`'ndeki kural). Sohbette fırsat türü ayrıca sorulmaz.
   - Bu, eşleştirme filtresinin davranışını değiştiriyor; mevcut satırlar migration'la tek elemanlı listeye çevrilir.
4. **Kurum yanıtsız eşiği:** `genc_ilgisi_yanitsiz` için 5 gün ve tek hatırlatma uygun mu?
5. **İhtiyaç kartı kapanması:** Bugün ihtiyacı kapatan bir yol yok ve bu firma tarafının işi.
   - **Öneri:** Bu görevde `ihtiyac_karti.durum` alanını, `ihtiyac_kapandi` geçişini (testli) ve eşleştirmenin kapalı ihtiyacı atlamasını ekleyip, kurumun "kapat" düğmesini firma görevine bırakmak.
   - **Alternatif:** Düğmeyi de şimdi eklemek.
6. **Onayda otomatik puanlama:** Linki olan iş kalemleri arka planda puanlanacak; genç artık "değerlendir"e basmak zorunda kalmayacak.
   - Linksiz kalemler puanlanmasın mı? Puanlanırsa ölçülebilirlik ve rol puanı alırlar, bu da doğrulama bonusunu değiştirir.
   - **Öneri:** Puanlanmasın.
7. **Referans ve sıfırlama:** İçerik değişince eski referans yanıtları puana girmesin mi? **Öneri:** Girmesin (§ 6.3).
8. **"Neden sana uygun":** Mevcut gerekçe kurumun bakış açısıyla yazılıyor.
   - **Öneri:** Aynen göstermek; ek LLM çağrısı yok.
   - **Alternatif:** Gence hitaben ikinci bir gerekçe; eşleşme başına bir çağrı daha ve yeni bir alan.
9. **Eski hesaplar:** KVKK onayı ve yeni zorunlu alanları olmayan mevcut genç hesaplarından, panele girişte bir kez tamamlamaları istensin mi (eşleştirme bundan etkilenmez)? **Öneri:** Evet, engellemeyen bir bant.
10. **Frontend bileşen testi:** `@testing-library/react` ve `jsdom` eklensin mi? **Öneri:** Mantığı `src/lib/`'e çıkarıp mevcut desenle test etmek. Bileşen testi ancak açıkça istenirse.
11. **Katman** (§ 11): `app/servisler/` açılsın mı?

---

## 13. Riskler

- **İlgi durum makinesi, Faz B'nin en çok test edilen yeri.** Tablo genişlerken mevcut satırların birebir aynı kalması testle sabitleniyor. Adım 7 yalnızca geçişleri ekliyor.
- **Maliyet:** Kart hazırlama, benzerlik alt sınırını geçen her ihtiyaç için pipeline çalıştırıyor. Gerekçe yalnızca yeni ya da gerekçesi boşaltılmış kayıtlar için üretiliyor. 10 kurum ölçeğinde sorun değil; havuz büyürse izlenmeli.
- **En iyi 5 sınırı:** Yeni gelen güçlü kart, kurumun henüz bakmadığı bir öneriyi listeden düşürebilir. Bu mevcut davranış ama artık daha sık tetiklenecek.
- **KVKK:** Referans kişinin e-postası artık sohbetten de alınıyor. Üçüncü kişinin verisi olduğu için aydınlatma metninde anılması gerekiyor. Metnin içeriği hukuki bir iş; ben yalnızca yer tutucu koyacağım.
- **Demo takvimi:** Roadmap'e göre özellik dondurma 3 Ekim akşamı. Bu plan 10 adım; kesim gerekirse önerim sırası şöyle: 6 (Yeni iş ekle) → 9 (Canlılık yeni türü) → 8'in güçlendir bölümü.

## 14. Kapsam dışı notlar (düzeltilmeyecek, yalnızca not)

- **SSRF:** ~~Kanıt linki kontrolünde iç/özel IP engeli yok.~~ Kapandı (30 Eyl, `app/core/guvenli_istek.py`).
- **Ana sayfa:** Hâlâ "Faz 2" diyor (`frontend/src/app/page.tsx:140`).
- **Supervisor:** Belgelerdeki "LangGraph supervisor pattern" ifadesi kodla uyuşmuyor.

---

## 15. Kapanış (29 Eyl)

### Uygulananlar (§ 0 kararlarıyla)

| Adım | Commit | Özet |
|---|---|---|
| 1 | `d18bb3f` | Eklemeli alanlar (profil, KVKK, çalışma, ilgi kaydı, ihtiyaç durumu) |
| 2 | `370dd8a` | Eşleştirme pipeline'ı `app/servisler/`'e (davranış değişmedi) — karar 5 |
| 3 | `c7070eb` | Müsaitlik çoklu seçim, staj dahil; boş liste elenmez — karar 2 |
| 4 | `0257641` | Kayıt formu, KVKK onayı, `/profil`, eski hesaplara bant, demo verisi — karar 10 |
| 5 | `2b05abf` | Kart hazırlama: linkli çalışma otomatik puanlanır, kart mevcut ihtiyaçlarla eşleşir — karar 7 |
| 6 | `1602159` | Keşif form bilgilerini sormaz; çalışma başına kanıt ve referans — karar 12 |
| 7 | `05a95bf` | Kart düzenleme; değişen çalışmanın göstergesi sıfırlanır, eski referans geçmişte — karar 8 |
| 9 | `99ba692` | Gençten ilgi, karşılıklı ilgi, "şimdilik değil", ihtiyaç kapanma kuralı; ilgi gösterilmiş kayıt korunur — kararlar 1, 4, 14 |
| 10 | `710fe10`, `3cf366c` | Genç ana sayfası (fırsatlar, kartını güçlendir, ilgilerim), firma tarafında ilgi gösterenler, açık iletişim onayı — kararlar 3, 9, 11 |
| 11 | `87f6fca` | Canlılık: yanıtsız genç ilgisi, firmaya 5 gün, tek kademe — karar 6 |
| 12 | — | Belgeler: api-contracts, architecture, data-schema, agent-specs (§ 1, 3, 4, 5; Doğrulama'nın yalnızca başlık/açıklama okuduğu açık — karar 13), Faz B/D notları, matching-algorithm, README, CLAUDE.md, roadmap |

### Ertelenen

- **8. adım, "Yeni iş ekle" sohbeti** (karar 16): dondurma sonrası. Form tabanlı ekleme aynı ihtiyacı karşılıyor; `somut_cikti.oturum_id` yerinde.
- **Firmanın ihtiyaç "kapat" düğmesi** (karar 4): kural ve servis hazır (`servisler/ilgi.py › ihtiyaci_kapat`), uç ve arayüz firma görevinde.
- **Toplu metin denetimi** (karar 15): liste `genc-akisi-metinler.md`, kurallar `icerik-rehberi.md`.

### Bilinen sınırlar

- **En iyi 5 sınırı** (karar 3): İhtiyaç başına sıralamada 6. ve sonrası olan genç o fırsatı görmez.
- **"Neden uygun?" metni:** Firmaya hitaben 3. şahısla yazılıyor ve gence aynen gösteriliyor (karar 9).
- **Arka plan işleri:** Eşleştirme, puanlama ve plan önerisi yanıttan sonra çalışıyor; sayfa kendiliğinden yenilenmiyor. Düzenlemeden hemen sonra gösterge boş görünür.
- **"Kartını güçlendir":** En iyi durumu varsayıyor (kanıt 3/3); metin bunu "öne çıkabilirsin" diye söylüyor.
- **Referans:** E-posta gönderilmiyor (SMTP yok). Genç yanıt linkini kendisi iletiyor; ilke olarak kendi referansını kendisi doldurabilir.
- **İlgiyi geri çekme:** Genç ilgisini geri çekince firmaya bildirim gitmiyor; firma ekranındaki işaret kalkıyor.
- **Hatırlatmalarda hitap:** Yanıtsız genç ilgisi hatırlatması yalnızca şablonla gidiyor. Kişiselleştirme istemi herkese "sen" diyor, diğer firma hatırlatmaları da öyle.
- **Onay pencereleri:** Tarayıcının "Tamam/İptal" düğmelerini kullanıyor; rehber § 5.6 eylem adı istiyor.
- **Mükerrer kontrol:** Aynı `oturum_id` kuralı yalnızca kart onayında var. "Yeni iş ekle" ertelendiği için çalışma eklemede tekrar koruması, form düğmesinin çift tıklamayı engellemesine dayanıyor.

### Kapsam dışı kalan, hâlâ açık işler

Öncelik: **D** = deploy (Faz E, 4 Eki) öncesi şart · **T** = teslim ve demo (5 Eki) öncesi · **S** = dondurma sonrası.

| İş | Öncelik | Not |
|---|---|---|
| ~~Kanıt linki kontrolünde iç/özel IP engeli (SSRF)~~ | **Kapandı** (30 Eyl) | `app/core/guvenli_istek.py`: iç ağ, şema/port, yönlendirme adımları ve DNS yeniden bağlama |
| KVKK aydınlatma metninin hukuki onayı | **D** | `/kvkk` şu an platformun ne yaptığını anlatan taslak; GİRVAK'ın onayladığı metin gelmeli |
| Tohum verinin genç akışı alanlarıyla hazırlanması | **D** | Faz E: kayıt alanları, ilgi gösterilmiş ve karşılıklı ilgili örnekler |
| Faz E'nin kendi maddeleri | **D** | Canlı CORS, `TARAMA_ANAHTARI` ile cron, migration'ların sıfırdan çalışması |
| Toplu metin denetimi | **T** | "… Ajanı" adları, firmaya "sen", uzun tire, "skor/eşik" geçen firma metinleri, Canlılık istemi ve şablonlarının hitabı, onay pencereleri. Liste: `genc-akisi-metinler.md` |
| Ana sayfadaki "Faz 2" yazısı | **T** | `frontend/src/app/page.tsx`; tek satır, metin denetimine girebilir |
| Belgelerdeki "LangGraph supervisor pattern" ifadesi | **T** | Kodda supervisor yok; README, CLAUDE.md ve architecture'da düzeltilmeli, jüri sorabilir |
| README eksikleri | **T** | Proje adı yer tutucu, canlı adres, ekran görüntüleri; README MIT diyor ama `LICENSE` dosyası yok (Faz F) |
| ~~`yeni_firsat` bildirim metni hâlâ anonim~~ | **T** | **Kapandı (30 Eyl):** metin denetiminde firma adı eklendi (`faz-d-canlilik.md` karar 3) |
| Firma tarafı | **T** | Sıradaki görev: firma profili ve düzenlemesi, ihtiyaç kapatma düğmesi, girişim/startup kapsam kararı |
| "Yeni iş ekle" sohbeti | **S** | Karar 16 |
| Onay pencereleri için özel bileşen | **S** | Eylem adlı düğmeler için; denetimde istenirse T |
| En iyi 5 sınırının gözden geçirilmesi | **S** | Havuz büyüyünce |
| Benzerlik alt sınırının (0,45) yeniden kalibrasyonu | **S** | 4 kartla ayarlandı |
| Gence hitaben ayrı "Neden uygun?" metni | **S** | Ek dil modeli çağrısı gerektirir |
| Hesap silme ve KVKK onayını geri alma | **S** | Şu an yalnızca "talep için program ekibine başvur" |
| ESCO taksonomisi | **S** | Belgede zaten isteğe bağlı |
