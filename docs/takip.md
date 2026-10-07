# Takip Ajanı

Karşılıklı ilgiyle açılan iş birliğinin planı, iki taraflı onayı, adım adım ilerleyişi ve
tamamlanmanın eşleştirmeye geri dönmesi. Bölüm numaraları sabittir; kod yorumları onlara
gönderme yapar.

## 0. Amaç

Döngünün son yarısı: iş birliği bir süreç planıyla ilerler, tamamlanır ve tamamlanma adayın
kartına sinyal olarak geri döner; sinyal Eşleştirme'nin doğrulama bonusuna girer. Geri besleme
döngüsü burada kapanır.

**Sınır:** ajan karar vermez. Planı onaylamaz, adımı işaretlemez, iş birliğini bitirmez; plan
ve özet önerir. Tamamlanma bir kural sonucudur.

## 1. Takip Ajanı ne yapar, ne yapmaz

| Yapar | Yapmaz |
|---|---|
| Eşleşmenin türüne uyan süreç şablonunun her adımını ilana ve adaya göre **kişiselleştirir**: "ne olunca tamam sayılır" ve hazırlık önerisi (T1) | Adım uydurmaz, eklemez, sırasını değiştirmez |
| Plan ve ilerleme değişince **kısa durum özeti** yazar | Planı onaylamaz, adımı işaretlemez, iş birliğini bitirmez |
| Özette geciken adımı söyler | Kimseyi değerlendirmez, puan vermez; adım kanıtını puanlamaz |

Sohbet ajanı değildir: tek seferlik hesaptır (SQL → istem → tek LLM çağrısı), `sohbet_motoru.py`'yi
kullanmaz; LLM zinciri ve yedek model `app/core/llm.py`'den.

**LLM katmanı:** plan kişiselleştirme **güçlü** katman (nüans önemli), durum özeti **hızlı**
katman (kısa, girdisi yapılandırılmış sayılar).

**LLM yoksa:** plan şablonun kendi metniyle yazılır, hiç boş kalmaz; özet yoksa sayfa
deterministik zaman çizelgesini gösterir. Çıkmaz sokak yok.

## 2. Veri modeli

**`isbirligi`**

| Alan | Anlam |
|---|---|
| `durum` | `plan_bekliyor` → `aktif` → `tamamlandi`; erken sonlanırsa `sonlandi` |
| `surec` | Süreç şablonunun anahtarı (T1) |
| `genc_plan_onayi`, `kurum_plan_onayi` | Aday tarafının ve ilan tarafının mevcut planı onayladığı an (F12) |
| `tamamlanma_tarihi` | Son adım tamamlandığı an |
| `sonlanma_nedeni`, `sonlanma_tarihi` | Erken sonlanma (T2) |
| `durum_ozeti`, `ozet_tarihi` | Ajanın son özeti |
| `plan_onerildi_mi` | Kabuldeki arka plan işinin ikinci kez çalışmasını önler |

**`milestone`** (adım)

| Alan | Anlam |
|---|---|
| `baslik`, `aciklama` | Adım ve "ne olunca tamam sayılır" |
| `asama`, `oneri` | Şablondaki adım anahtarı (elle eklenen adımda boş) ve hazırlık önerisi |
| `sira`, `hedef_tarih` | Zaman çizelgesi |
| `genc_isaret`, `kurum_isaret` | İki tarafın "tamamlandı" işareti |
| `kanit_linki` | İsteğe bağlı; puanlanmaz |
| `durum` | `bekliyor` \| `tamamlandi` (iki işaret de varsa) |

- **Gecikme saklanmaz**, okuma anında hesaplanır: `hedef_tarih < bugün` ve tamamlanmadı.
  Zamanlayıcı yok.
- **Aktivite:** her Takip eylemi eşleşmenin `son_aktivite_tarihi`'ni günceller; Canlılık
  hareketsizliği buradan okur.

## 3. Durum makineleri

Kurallar saf fonksiyonlarda (`app/agents/takip_durumu.py`), tabloları testle sabit; uçlar
yalnızca uygular.

**Plan** (`plan_gecisi`):

| Şu an | Olay | Sonra | Yan etki |
|---|---|---|---|
| `plan_bekliyor` | adım ekle / düzenle / sil, yeni plan önerisi | `plan_bekliyor` | **İki onay da sıfırlanır** (herkes son hâli onaylasın); karşı tarafa bildirim |
| `plan_bekliyor` | planı onayla | kendi onayı yazılır; iki onay varsa `aktif` | Karşı tarafa bildirim; `aktif` olunca iki tarafa |
| `aktif` | plan düzenleme | **409** | Onaylanmış plan kilitli |
| `tamamlandi`, `sonlandi` | her şey | **409** | — |

En az bir adım yoksa plan onaylanamaz (409). Aynı tarafın onayı tekrarlanırsa 200, yan etkisiz.

**Adım işareti** (`isaret_gecisi`, yalnızca `aktif` iken):

| Şu an | Olay | Sonra |
|---|---|---|
| işaret yok | işaretle | Kendi işareti yazılır; karşı tarafa "onayını bekliyor" bildirimi |
| karşı taraf işaretlemiş | işaretle | `tamamlandi`; iki tarafa bildirim |
| kendi işareti var | işareti geri al | İşaret silinir |
| `tamamlandi` | işareti geri al | **409** (iki taraf onaylamış adım geri açılmaz) |

**Tamamlanma:** `aktif` iken son adım da tamamlanınca iş birliği kendiliğinden `tamamlandi`
olur (`isbirligi_tamamlandi_mi`). Her adım zaten iki taraflı onaylandı.

**Erken sonlanma** (`sonlanma_gecisi`): taraflardan biri `plan_bekliyor` ya da `aktif` iken
nedenle sonlandırır; `sonlandi` geri açılmaz, tamamlanmış sayılmaz (T2).

## 4. Plan önerisi

- **Adımlar kodda, kişiselleştirme ajanda** (T1). Eşleşmenin türü sabit bir süreç şablonu
  seçer (`app/agents/takip_surecleri.py` › `surec_sec`): genç ilanında müsaitliğe göre işe alım,
  staj ya da proje; ortak ilanında iş birliği türüne göre deneme işi, tedarik ya da genel iş
  birliği. Her şablon beş adım ve varsayılan hafta taşır; son adım ilanın başarı kriterine bağlanır.
- **Ajanın işi:** her adım için "ne olunca tamam sayılır" (`aciklama`) ve hazırlık önerisi
  (`oneri`), ilana ve adaya göre.
- **Geçerlilik kuralı (kodda):** model hata verirse, zaman aşımına uğrarsa ya da geçersiz çıktı
  dönerse (boş, çok uzun, tanınmayan adım anahtarı, "pilot" kelimesi) o adımda şablonun metni
  kalır. Plan hiçbir zaman boş kalmaz; "Plan önerisi al" 503 dönmez.
- **Ne zaman:** karşılıklı ilgiden sonra yanıt döndükten sonra arka planda
  (`plani_arka_planda_oner`) ve taraflar "Plan önerisi al" dediğinde (yalnızca `plan_bekliyor`'da;
  mevcut adımları siler, iki onayı sıfırlar).
- **Girdi:** ilan (problem, başarı kriteri, kısıtlar; genç ilanında müsaitlik ve çalışma modeli,
  ortak ilanında iş birliği türü) ve aday (yetenek kartı ya da firma kartı). Kullanıcı metni
  `<ilan>` / `<aday>` veri etiketlerinde (S1). İletişim bilgisi girmez.

## 5. Durum özeti

- **Ne zaman:** plan onaylanınca ve her adım tamamlandığında arka planda yeniden yazılır. Okuma
  anında LLM çağrılmaz.
- **Girdi (yalnızca sayılar ve başlıklar):** kaç adım var, kaçı tamamlandı, hangileri gecikmiş,
  hangisi karşı tarafın işaretini bekliyor, son hareketten beri kaç gün geçti.
- **Çıktı:** en fazla 2 cümle, nötr dil, suçlama yok.
- **Kesilebilir:** hiçbir kural özete bakmaz; çökerse döngü aynen çalışır.

## 6. Tamamlanan iş birliği sinyali ve Eşleştirme

- **Sinyal saklanmaz, hesaplanır:** bir kartın `tamamlandi` durumundaki iş birliği sayısı
  (`tamamlanan_pilot_sayilari`). Tek doğruluk kaynağı `isbirligi.durum`; ayrı sayaç yok, iki
  kaynak ayrışamaz. Kodda adı "pilot"tur; arayüzde "tamamlanan iş birliği" rozeti (T3).
- **Doğrulama bonusuna toplamsal girer:**

  ```
  dogrulama_bonus = min(1.0, guven_orani + 0.5 × [tamamlanan ≥ 1])
  skor            = 0.75 × benzerlik + 0.25 × dogrulama_bonus
  ```

  Tamamlanmış iş birliği olmayan kartın skoru değişmez; olan kart en çok +0.125 kazanır. Sinyal
  alakayı yaratmaz: benzerlik alt sınırı skordan önce uygulanır (`matching-algorithm.md` § 5).
- **Gerekçe istemi** kartın tamamlanmış iş birliği sayısını da alır.

## 7. Uç noktalar ve sahiplik

Sözleşme `kimlik-ve-dongu.md` § 3: 401 / 403 / 404. Taraflar eşleşmenin aday tarafı ve ilan
tarafıdır; GİRVAK yalnızca okur.

| Uç nokta | Taraflar | GİRVAK | Not |
|---|---|---|---|
| `GET /isbirligi/{id}` | ✓ | ✓ (e-postasız) | Plan, adımlar (gecikme hesaplı), onaylar, özet, `iletisim`; iki tarafa **aynı görünüm** |
| `POST /isbirligi/{id}/plan-oner` | ✓ | — | Yalnızca `plan_bekliyor` |
| `POST /isbirligi/{id}/milestone-ekle` | ✓ | — | |
| `PATCH /isbirligi/{id}/milestone/{mid}` | ✓ | — | Taslakta başlık / açıklama / tarih; `aktif`'te yalnızca `kanit_linki` |
| `DELETE /isbirligi/{id}/milestone/{mid}` | ✓ | — | Yalnızca `plan_bekliyor` |
| `POST /isbirligi/{id}/plan-onayla` | ✓ | — | Çağıranın tarafı hangi onayın yazılacağını belirler |
| `POST /isbirligi/{id}/milestone/{mid}/isaretle`, `…/isareti-geri-al` | ✓ | — | |
| `POST /isbirligi/{id}/sonlandir` | ✓ | — | Nedenle; karşı tarafa nedensiz bildirim |
| `GET /isbirliklerim` | ✓ | — | Satırda durum, ilerleme, geciken adım |

İşaretleme PATCH değil ayrı POST uçlarıdır: durum geçişi tek bir eyleme karşılık gelsin.

**Bildirimler:** plan önerildi (iki taraf), plan düzenlendi (karşı taraf), plan onayı ve plan
onaylandı, adım işaretlendi (karşı taraf), adım tamamlandı, iş birliği tamamlandı ve iş birliği
sonlandı. Tıklayınca iş birliği sayfasına gidilir. Aynı eylemin tekrarı bildirim yazmaz; metinde
e-posta yok.

## 8. Ekranlar

- **`/isbirligi/{id}`:** iki tarafa aynı sayfa.
  - Üstte taraflar, e-postalar ("E-posta yaz" taslaklı bağlantısı), durum özeti.
  - Altında süreç çizgisi: sıralı adımlar; her birinde hedef tarih, gecikme etiketi, iki tarafın
    işaret durumu ve açılır "Hazırlık önerisi".
  - `plan_bekliyor`: adımlar düzenlenebilir; "Plan önerisi al", "Planı onayla"; iki tarafın onay
    durumu görünür.
  - `aktif`: "Tamamlandı olarak işaretle" / işareti geri alma, isteğe bağlı kanıt linki,
    "Süreci sonlandır" (sayfa içi onayla, neden seçimi).
  - `tamamlandi` / `sonlandi`: kapanış bandı ve tarihi.
- **Paneller:** "İş birlikleri" satırları bu sayfaya gider; satırda durum ve ilerleme görünür.
- **Kart ve öneriler:** kart sayfasında ve öneri kartında "tamamlanan iş birliği" rozeti.
- **GİRVAK:** iş birlikleri duruma göre ve tamamlanan iş birliği sayısı program hedefiyle.

## 9. Kararlar

1. **Tamamlanma otomatiktir.** Son adım iki tarafça tamamlanınca iş birliği kendiliğinden
   `tamamlandi` olur. Seçilmeyen: iki tarafın ayrıca "bitti" demesi (her adım zaten iki taraflı
   onaylandı, fazladan tıklama).
2. **Bonus toplamsal ve tavanlıdır** (§ 6). Seçilmeyenler: sinyal varsa bonusu doğrudan 1.0 yapmak
   (kanıtlı kartları geçer); ağırlıklı karışım (sinyali olmayan kartların skoru düşerdi).
3. **Onaylanmış plan kilitlidir.** `aktif`'te yalnızca işaret ve kanıt linki değişir. Seçilmeyen:
   "planı yeniden aç" dalı.

## 10. Kapsam dışı

Onaylanmış planda değişiklik; adım kanıtının puanlanması; dosya yükleme; takvim entegrasyonu;
taraflar arası mesajlaşma; iş birliği sonunda karşılıklı değerlendirme formu; birden fazla
temsilciyle iş birliği.

## 11. Uygulama ayrıntıları

- **Bildirim tekilleştirme:** karşı tarafta okunmamış bir "plan düzenlendi" bildirimi varken
  yenisi yazılmaz; art arda beş düzenleme beş bildirim olmaz.
- **Bildirimden sayfaya:** `GET /bildirimler` satırı iş birliği varsa `isbirligi_id` taşır; Takip
  bildirimleri ve "kabul" doğrudan `/isbirligi/{id}`'ye gider.
- **Plan beklerken:** kabulden hemen sonra açılan sayfa, plan henüz gelmediyse 4 saniyede bir,
  en çok 8 kez yoklar; sonra "Plan önerisi al" düğmesi.
- **Satır kilidi:** yazan her uç iş birliği satırını `FOR UPDATE` ile okur; çift tıklama iki kez
  uygulanmaz. Plan önerisi LLM beklenirken de kilidi tutar.
- **Özet yalnız kendi alanlarını yazar** (`UPDATE … SET durum_ozeti, ozet_tarihi`); LLM beklenirken
  yapılan başka bir değişikliği ezmez.
- **Bildirim zamanı:** `olusturma_tarihi` INSERT anında `clock_timestamp()`; aynı işlemdeki
  bildirimlerin sırası kararlı.
- **Testlerde arka plan işleri:** plan önerisi ve özet `tests/conftest.py`'de sahteyle değişir;
  yeni bir arka plan işi eklenirse oraya da eklenir.

## Ek: Firma–firma iş birliği

Aynı tablo, aynı kurallar, aynı uçlar. Ortak (aday) firma takip kurallarında aday tarafının
yerindedir: `genc_plan_onayi`, `genc_isaret` onun alanlarıdır (F12). Plan önerisi için ayrı istem
(`app/agents/takip.py` › `firma_plan_oner`), geçerlilik kuralı aynı. `IsbirligiDetayi` ve
`IsbirligiOzeti` `aday_turu` ve `aday_adi` taşır. Tamamlanan firma–firma iş birliği aday firmanın
eşleştirme bonusuna girer (F13).
