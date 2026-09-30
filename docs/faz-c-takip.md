# Faz C — Takip Ajanı (özellik notu)

> Durum: **tamamlandı (27 Eyl)**, tarayıcıda iki pencereyle doğrulandı. Aşağıda
> § 12 uygulamada netleşen ayrıntıları topluyor.
>
> Önceki durum: **onaylandı (27 Eyl).** § 9'daki üç kararda öneriler seçildi; § 7'deki
> iki sözleşme sapması kabul edildi. Roadmap § Faz C'nin kabul ölçütü ve sınırı
> bu notun çerçevesi; yeni özellik eklenmez.

## 0. Amaç ve kabul

Döngünün son yarısı: genç kabul edince açılan iş birliği, milestone'larla
ilerler, tamamlanır ve tamamlanma gencin kartına **"tamamlanmış pilot"**
sinyali olarak geri döner; bu sinyal Eşleştirme'nin doğrulama bonusuna girer.
Geri besleme döngüsü burada kapanır (roadmap § "Tam ne demek" madde 1).

**Kabul:** İki ayrı tarayıcıda, genç ve kurum aynı iş birliği sayfasında:
1. Ajanın önerdiği planı görür, düzenler, ikisi de onaylar.
2. Milestone'ları iki taraflı işaretler; tarihi geçen milestone görünür biçimde işaretlenir.
3. Son milestone tamamlanınca iş birliği `tamamlandi` olur.
4. Gencin kartında "tamamlanmış pilot" görünür ve o kartın eşleşme skoru bu sinyal kadar yükselir.

Bunların hepsi çıkmaz sokak olmadan yürümeli.

**Sınır (roadmap):** Ajan karar vermez, milestone'u kendisi kapatmaz; öneri
ve özet üretir. Tamamlanma bir kural sonucudur, ajanın kararı değil.

## 1. Takip Ajanı ne yapar, ne yapmaz

| Yapar | Yapmaz |
|---|---|
| İş birliği açılınca ihtiyaç kartının başarı kriterinden 3-5 milestone'luk **plan önerir** (tek LLM çağrısı, yapılandırılmış çıktı) | Planı kendisi onaylamaz; iki taraf onaylamadan plan yürürlüğe girmez |
| Plan ve ilerleme değişince **kısa durum özeti** yazar | Milestone'u işaretlemez, kapatmaz; iş birliğini bitirmez |
| Özette tarihi geçen milestone'u söyler | Kimseyi değerlendirmez, puan vermez |

Sohbet ajanı değil: Eşleştirme ve Doğrulama gibi tek seferlik hesaplardır
(SQL → istem → tek LLM çağrısı). Dolayısıyla `sohbet_motoru.py`'yi kullanmaz;
LLM zinciri ve yedek model `app/core/llm.py`'den.

**LLM katmanı:**
- Plan önerisi: **güçlü** katman. Tek seferlik, nüans önemli: başarı kriterine bağlı, ölçülebilir ara hedefler.
- Durum özeti: **hızlı** katman. Kısa, sık, girdisi tamamen yapılandırılmış sayılar.

**LLM yoksa:** Arıza ya da hız sınırı olursa plan boş kalır. Taraflar
milestone'ları elle ekleyebilir, "Planı yeniden öner" düğmesi de vardır.
Özet yoksa sayfa yine deterministik zaman çizelgesini gösterir. Çıkmaz sokak yok.

## 2. Veri modeli (migration, veri silmez)

`ISBIRLIGI` ve `MILESTONE` zaten var (Faz 0 şeması). Eklenenler:

**`isbirligi`:**

| Alan | Tip | Anlam |
|---|---|---|
| `durum` (mevcut) | string | Yeni değer kümesi: `plan_bekliyor` → `aktif` → `tamamlandi` |
| `genc_plan_onayi` | timestamptz null | Gencin mevcut planı onayladığı an |
| `kurum_plan_onayi` | timestamptz null | Kurumun mevcut planı onayladığı an |
| `tamamlanma_tarihi` | timestamptz null | Son milestone tamamlandığı an |
| `durum_ozeti` | text null | Ajanın son özeti |
| `ozet_tarihi` | timestamptz null | Özetin yazıldığı an |
| `plan_onerildi_mi` | bool | Ajan bu iş birliği için plan önerdi mi? Kabulde arka plan işinin ikinci kez çalışmasını önler |

**`milestone`:**

| Alan | Tip | Anlam |
|---|---|---|
| `aciklama` | text null | Ölçülebilir tanım ("ne olunca tamam sayılır") |
| `sira` | int | Zaman çizelgesindeki sıra |
| `genc_isaret` | timestamptz null | Genç "tamamlandı" dedi |
| `kurum_isaret` | timestamptz null | Kurum "tamamlandı" dedi |
| `kanit_linki` | string null | İsteğe bağlı; Doğrulama Ajanı puanlamaz (kapsam dışı) |
| `durum` (mevcut) | string | `bekliyor` \| `tamamlandi`. İki işaret de varsa `tamamlandi` |

- **Gecikme saklanmaz**, okuma anında hesaplanır: `hedef_tarih < bugün` ve `durum != tamamlandi` ise gecikmiş sayılır. Doğrulama'nın 7 günlük zaman aşımıyla aynı desen; zamanlayıcı yok.
- **Mevcut kayıtlar:** Faz B'de açılan `aktif` durumlu, planı olmayan iş birlikleri migration'da `plan_bekliyor` olur. Senin tarayıcı denemesindeki iş birliği de böylece plan önerisinden devam eder.
- **Aktivite:** Her Takip eylemi (plan düzenleme, onay, işaret) eşleşmenin `son_aktivite_tarihi`'ni günceller; Canlılık (Faz D) pasifliği buradan okuyacak.

## 3. Durum makineleri (saf fonksiyonlar, tablo testli)

Faz B'deki `gecis()` deseni: kural tek yerde, uç noktalar yalnızca uygular.

**Plan (iş birliği):**

| Şu an | Olay | Kim | Sonra | Yan etki |
|---|---|---|---|---|
| `plan_bekliyor` | milestone ekle / düzenle / sil, plan öner | genç ya da kurum | `plan_bekliyor` | **İki tarafın onayı da sıfırlanır** (herkes son hâli onaylasın); karşı tarafa bildirim |
| `plan_bekliyor` | planı onayla | genç ya da kurum | kendi onayı yazılır; iki onay da varsa `aktif` | Karşı tarafa bildirim; `aktif` olunca iki tarafa |
| `aktif` | plan düzenleme | — | **409** | Onaylanmış plan kilitli (bkz. § 8 kapsam dışı) |
| `tamamlandi` | her şey | — | **409** | — |

- En az bir milestone yoksa plan onaylanamaz (409, "Önce en az bir milestone ekleyin").
- Aynı tarafın onayı tekrarlanırsa 200 döner, yan etkisiz.

**Milestone işareti** (yalnızca iş birliği `aktif` iken):

| Şu an | Olay | Kim | Sonra |
|---|---|---|---|
| `bekliyor`, işaret yok | işaretle | genç / kurum | Kendi işareti yazılır; karşı tarafa "onayını bekliyor" bildirimi |
| `bekliyor`, karşı taraf işaretlemiş | işaretle | diğer taraf | `tamamlandi`; iki tarafa bildirim |
| `bekliyor`, kendi işareti var | işareti geri al | aynı taraf | İşaret silinir |
| `tamamlandi` | işareti geri al | — | **409** (iki taraf onaylamış bir adım geri açılmaz) |

**Tamamlanma kuralı:** İş birliği `aktif` iken son `bekliyor` milestone da
`tamamlandi` olunca iş birliği `tamamlandi` olur ve `tamamlanma_tarihi`
yazılır. Ajan değil kural karar verir; iki taraf her milestone'u zaten ayrı
ayrı onayladı. → **Karar 1** (§ 9).

## 4. Plan önerisi

- **Ne zaman:** Genç kabul edince (Faz B'nin `kabul` ucu) arka plan işi olarak başlar; Eşleştirme'deki `eslestirmeyi_arka_planda_calistir` deseni, zamanlayıcı yok. Yanıt beklenmez. Arka plan işi çalışmadıysa ya da LLM hata verdiyse taraflar sayfadan "Plan öner" diyebilir.
- **Girdi:**
  - İhtiyaç kartı: problem tanımı, başarı kriteri, kısıtlar, müsaitlik tercihi, çalışma modeli.
  - Yetenek kartı: rol alanı, araçlar, somut çıktı başlıkları.
  - İletişim bilgisi girmez.
- **Çıktı (yapılandırılmış):** 3-5 milestone; her biri `{baslik, aciklama, hafta}`.
  - `hafta`: başlangıçtan kaçıncı haftada bittiği. 1-12 arası, artan.
  - Hedef tarih `baslangic_tarihi + hafta`'dan hesaplanır.
  - Son milestone başarı kriterine bağlanmalı.
- **İstem kuralları:**
  - Kartlarda olmayan bir sayı ya da araç uydurulmaz.
  - Her milestone "ne olunca tamam" sorusunu yanıtlar.
  - Sonuç 3'ten az ya da 5'ten fazla milestone ise ya da haftalar artmıyorsa çıktı reddedilir ve yedek modele gidilir. Eşleştirme gerekçesindeki doğrulama deseni.
- **Yeniden öner:** Yalnızca `plan_bekliyor`'da çalışır. Mevcut milestone'ları siler, yenilerini yazar, iki onayı sıfırlar. Arayüz önce onay sorar.

## 5. Durum özeti

- **Ne zaman:** Plan onaylanınca ve her milestone tamamlandığında arka plan işi yeniden yazar. Okuma anında LLM çağrılmaz.
- **Girdi (yalnızca sayılar ve başlıklar):** Kaç milestone var, kaçı tamamlandı, hangileri gecikmiş, hangisi karşı tarafın işaretini bekliyor, son hareketten beri kaç gün geçti.
- **Çıktı:** En fazla 2 cümle, nötr dil, suçlama yok ("X haftadır hareket yok, Y adımı karşı tarafın onayını bekliyor").
- **Gecikme:** Zaman çizelgesinde her okumada gösterilir, özetten bağımsız. Özet bir sonraki değişiklikte güncellenir. Faz D'de Canlılık'ın günlük taraması özeti de tazeleyebilir.

## 6. "Tamamlanmış pilot" sinyali ve Eşleştirme

- **Sinyal saklanmaz, hesaplanır:** `tamamlanan_pilot` = o yetenek kartının `tamamlandi` durumundaki iş birliği sayısı. Tek doğruluk kaynağı `isbirligi.durum`; kartta ayrıca tutulan bir sayaç olmaz, iki kaynak ayrışamaz.
- **Kart görünümü:** `tamamlanan_pilot: int` alanı eklenir. Kartta bir rozet görünür: "1 tamamlanmış pilot"; kuruma da, öneri listesinde de. Kurum adı yazmaz; genç ve kurum zaten biliyor.
- **Doğrulama bonusuna girişi.** → **Karar 2** (§ 9). Öneri:

  ```
  dogrulama_bonus = min(1.0, guven_orani + 0.5 × [tamamlanan_pilot ≥ 1])
  skor            = 0.75 × benzerlik + 0.25 × dogrulama_bonus   (değişmez)
  ```

  - Pilotu olmayan kartın skoru bugünküyle aynı kalır; demo kalibrasyonu (0.442) bozulmaz.
  - Tamamlanmış pilot skora en çok +0.125 ekler.
  - **Alakayı yaratmaz:** Benzerlik alt sınırı (0.45) skordan önce uygulanmaya devam eder (`matching-algorithm.md` § 5).
- **Gerekçe istemi:** Gerekçeye kartın tamamlanmış pilot sayısı da verilir ("daha önce bir pilotu iki tarafın onayıyla tamamladı").
- **Belge:** `matching-algorithm.md` § 4 güncellenir.

## 7. Uç noktalar ve sahiplik

Faz B sözleşmesi aynen geçerli: 401 token yok, 403 rol uygun değil, 404 başkasının kaynağı.

- **Taraflar:** Eşleşmedeki yetenek kartının genci ve ihtiyaç kartının kurumu.
- **GİRVAK:** Yalnızca okur.

| Uç nokta | Genç (taraf) | Kurum (taraf) | GİRVAK | Not |
|---|---|---|---|---|
| `GET /isbirligi/{id}` | ✓ | ✓ | ✓ (e-postasız) | Plan, milestone'lar (gecikme hesaplı), onaylar, özet, `iletisim`. İki tarafa **aynı görünüm** |
| `POST /isbirligi/{id}/plan-oner` | ✓ | ✓ | — | Yalnızca `plan_bekliyor`'da |
| `POST /isbirligi/{id}/milestone-ekle` | ✓ | ✓ | — | Sözleşmede zaten var |
| `PATCH /isbirligi/{id}/milestone/{mid}` | ✓ | ✓ | — | Taslakta başlık/açıklama/tarih; `aktif`'te yalnızca `kanit_linki` |
| `DELETE /isbirligi/{id}/milestone/{mid}` | ✓ | ✓ | — | Yalnızca `plan_bekliyor` |
| `POST /isbirligi/{id}/plan-onayla` | ✓ | ✓ | — | Çağıranın rolü hangi onayı yazacağını belirler |
| `POST /isbirligi/{id}/milestone/{mid}/isaretle` | ✓ | ✓ | — | |
| `POST /isbirligi/{id}/milestone/{mid}/isareti-geri-al` | ✓ | ✓ | — | |
| `GET /isbirliklerim` (mevcut) | ✓ | ✓ | — | Satıra `durum`, `ilerleme {tamamlanan, toplam}`, `geciken` eklenir |
| `GET /girvak/sayilar` (mevcut) | — | — | ✓ | İş birliği duruma göre (`plan_bekliyor` / `aktif` / `tamamlandi`) |

- **Sözleşme sapması:** `api-contracts.md`'deki `GET /isbirligi/{id}/zaman-cizelgesi` yerine tek bir `GET /isbirligi/{id}` öneriyorum; zaman çizelgesi ve özet aynı yanıtta, sözleşme güncellenir. İşaretleme de PATCH yerine ayrı POST uçlarında: Faz B'deki kabul/red gibi, durum geçişi tek bir eyleme karşılık gelsin.
- **Bildirimler** (Faz B tablosu, yeni türler):

| Olay | Kime | Metin (örnek) |
|---|---|---|
| Ajan plan önerdi | iki taraf | "Kooperatif X ile iş birliğin için bir plan önerildi; gözden geçir ve onayla." |
| Plan düzenlendi | karşı taraf | "Elif planı düzenledi; son hâli onayını bekliyor." |
| Plan onaylandı (ikisi de) | iki taraf | "Plan iki tarafça onaylandı; iş birliği başladı." |
| Milestone işaretlendi | karşı taraf | "Kooperatif X 'Veri modeli' adımını tamamlandı olarak işaretledi; sen de onayla." |
| İş birliği tamamlandı | iki taraf | "İş birliği tamamlandı; kartına tamamlanmış pilot olarak eklendi." |

  Tıklayınca iş birliği sayfasına gidilir. Aynı eylemin tekrarı bildirim yazmaz; metinde e-posta yok.

## 8. Ekranlar

- **`/isbirligi/[id]`:** İki tarafa aynı sayfa.
  - Üstte taraflar (gencin adı, kurum adı), e-postalar, durum özeti.
  - Altında zaman çizelgesi: sıralı milestone'lar; her birinde hedef tarih, gecikme etiketi ve iki tarafın işaret durumu ("Sen işaretledin, kurumun onayı bekleniyor").
  - `plan_bekliyor`: Milestone'lar düzenlenebilir; "Milestone ekle", "Planı yeniden öner" ve "Planı onayla" düğmeleri; iki tarafın onay durumu görünür.
  - `aktif`: "Tamamlandı olarak işaretle" / "İşaretimi geri al", isteğe bağlı kanıt linki.
  - `tamamlandi`: "Tamamlandı" başlığı, tamamlanma tarihi; gencin tarafında "kartına eklendi" notu.
- **Paneller:** Genç ve kurum panelindeki "İş birliklerim" satırları bu sayfaya gider; satırda durum ve ilerleme ("2/4 adım", "1 gecikmiş") görünür.
- **Kart ve öneriler:** Kart sayfasında ve öneri kartında "N tamamlanmış pilot" rozeti.
- **GİRVAK sayıları:** "Tamamlanan pilot" sayısı (Faz D'deki pilot hedefi, 5, buna bağlanacak).

## 9. Kararlar (onaylandı)

1. **Tamamlanma otomatik mi?** → **Evet, otomatik.**
   - **Öneri:** Son milestone iki tarafça tamamlanınca iş birliği kendiliğinden `tamamlandi` olur. Her adım zaten iki taraflı onaylandı; ayrıca bir "iş birliğini bitir" onayı tıklama ekler.
   - **Alternatif:** İki tarafın ayrıca "tamamlandı" demesi.
2. **Pilot bonus formülü:** → **§ 6'daki toplamsal, tavanlı formül.**
   - **Öneri:** § 6'daki toplamsal, tavanlı formül. Mevcut skorlar değişmez, en çok +0.125.
   - **Alternatifler:**
     - (b) Pilot varsa bonus doğrudan 1.0 (+0.25'e kadar): güçlü, ama kanıtlı kartları geçer.
     - (c) Ağırlıklı karışım (`0.6 × güven + 0.4 × pilot`): pilotsuz kartların skoru düşer, demo kalibrasyonu yeniden yapılmalı.
3. **Onaylanmış plan kilitli mi?** → **Evet, kilitli.**
   - **Öneri:** Evet, `aktif`'te plan düzenlenmez; yalnızca işaret ve kanıt. Plan değişikliği isteği kapsam dışı.
   - **Alternatif:** Bir taraf "planı yeniden aç" der, iki taraf yeniden onaylar. Durum makinesine bir dal ekler.

## 10. Kapsam dışı

- Onaylanmış planda değişiklik (Karar 3 "evet" ise)
- İş birliğini iptal etme ya da yarıda bırakma: pasifleşme Canlılık'ın (Faz D) işi
- Milestone kanıtının Doğrulama Ajanı'nca puanlanması
- Dosya yükleme
- Takvim entegrasyonu
- Taraflar arası mesajlaşma
- İş birliği sonunda karşılıklı değerlendirme formu
- Birden fazla genç ya da kurum temsilcisiyle iş birliği

## 11. Uygulama sırası

Onaydan sonra; her adım ayrı commit, en az bir test, adım sonunda kısa özet:

1. Migration (§ 2) ve iki saf durum makinesi (§ 3), tablo testleriyle.
2. Plan önerisi: LLM istemi ve yapılandırılmış çıktı doğrulaması, kabulde arka plan işi, `plan-oner` ucu, LLM yoksa boş plan.
3. Plan düzenleme ve iki taraflı onay: milestone ekle/düzenle/sil, `plan-onayla`; sahiplik (401/403/404) ve bildirim testleri.
4. İşaretleme, okuma anında gecikme, tamamlanma kuralı, `GET /isbirligi/{id}`, `/isbirliklerim` ilerlemesi.
5. Tamamlanmış pilot sinyali: kart görünümü, doğrulama bonusu, gerekçe istemi; `matching-algorithm.md`.
6. Durum özeti (hızlı katman, arka plan). **Kesilebilir:** süre daralırsa atlanır. Döngü onsuz da tam çalışır; diğer adımlar ona bağımlı değildir (özet alanı boş kalabilir, arayüz onsuz da eksiksiz).
7. Frontend: `/isbirligi/[id]`, panel bağlantıları, pilot rozeti, GİRVAK sayısı.
8. Belgeler (api-contracts, data-schema, agent-specs § 6, README, CLAUDE.md) ve iki tarayıcıda deneme listesi.

## 12. Uygulamada netleşenler

Notun kararlarından sapma yok; notta yazmayan ama uygulamada gereken ayrıntılar:

- **Kurala uymayan plan:** § 4'te "yedek modele gidilir" dendi; uygulamada yedek model yalnızca sağlayıcı arızasında devreye giriyor (Faz A deseni). Kurala uymayan çıktı aynı zincirden bir kez **düzeltme notuyla** yeniden isteniyor (Eşleştirme gerekçesinin deseni); yine uymazsa plan boş kalıyor.
- **Bildirim tekilleştirme:** Karşı tarafta okunmamış bir "plan düzenlendi" bildirimi varken yenisi yazılmıyor; art arda beş düzenleme beş bildirim olmuyor.
- **Bildirimden sayfaya:** `GET /bildirimler` satırı iş birliği varsa `isbirligi_id` taşıyor; Takip bildirimleri ve "kabul" doğrudan `/isbirligi/{id}`'ye gidiyor.
- **Plan beklerken:** Kabulden hemen sonra açılan sayfa, plan henüz gelmediyse 4 sn'de bir, en çok 8 kez yokluyor; sonra "Ajandan plan iste" düğmesi.
- **Satır kilidi:** Yazan her uç iş birliği satırını `FOR UPDATE` ile okuyor; çift tıklama iki kez uygulanmıyor. Plan önerisi LLM beklenirken de kilidi tutuyor (eşzamanlı düzenleme sıraya giriyor).
- **Özet yalnız kendi alanlarını yazar:** arka plan işi `UPDATE … SET durum_ozeti, ozet_tarihi`; LLM beklenirken yapılan başka bir değişikliği ezmiyor.
- **Bildirim zamanı:** `olusturma_tarihi` INSERT anında `clock_timestamp()` ile atanıyor (aynı işlemdeki bildirimlerin sırası kararlı; `now()` işlem başlangıcını dönüyordu).
- **Testlerde arka plan işleri:** kabulün plan önerisi ve özet `tests/conftest.py`'de sahteyle değiştiriliyor; gerçek işi sınayan testler fonksiyonu içe aktarma anında yakalıyor.


## Ek: Firma–firma iş birliği (firma akışı)

Aynı tablo, aynı kurallar, aynı uçlar (`plans/firma-akisi.md` § 9). Ortak (aday) firma takip kurallarında "genç" tarafının yerindedir: `genc_plan_onayi`, `genc_isaret` onun alanlarıdır (karar 12, kolon adları değişmedi). Plan önerisi için ayrı istem (`app/agents/takip.py` › `firma_plan_oner`), geçerlilik kuralı aynı. `IsbirligiDetayi` ve `IsbirligiOzeti` `aday_turu` ve `aday_adi` taşır; `genc_adi`/`rol_alani` yalnızca genç adayında dolu. Tamamlanan firma–firma iş birliği aday firmanın eşleştirme bonusuna girer (`matching-algorithm.md` § 7).
