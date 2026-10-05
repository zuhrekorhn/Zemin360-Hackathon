# İlan düzenleme ("Düzenle" düğmesi)

Durum: **onaylandı (5 Eki), uygulanmadı.** Tanımlama incelemesinin ertelenen maddesi
(`docs/roadmap.md` § Tanımlama incelemesi). Kod 7 Ekim akşamı donar; 6 Ekim akşamına
kadar bitmezse 3. adım (arayüz) atılmaz, uç zararsız kalır.

## Karar

İlan **yerinde** düzenlenir; kapatıp kopyalamak ve ilgileri yeni ilana taşımak YOK.
Sebep: eşleştirme pipeline'ı aynı ilan için yeniden çalışmaya zaten hazır, ilgiler
kendiliğinden korunur. Migration gerekmez.

Pipeline'ın davranışı (`backend/app/servisler/eslestirme.py` › `pipeline_calistir`):
- `temizlenecekler` (`app/agents/eslestirme.py`) yalnızca `onerildi` kayıtları siler;
  kurumun karar verdiği kayıtlar (ilgileniliyor/kabul/red) kalır.
- `genc_ilgilendi` kaydının skoru ve gerekçesi değişmez (karar 14).
- Gerekçe yalnızca `gerekce_metni is None` olan ve `genc_ilgilendi` olmayan kayıtlar
  için üretilir. **Bu yüzden düzenlemede eski gerekçeler sıfırlanmalı**, yoksa eski
  metne göre yazılmış "Neden uygun?" kalır.
- Pipeline `ihtiyac_kilidi` (advisory lock) alır; kapatma da aynı kilidi alır.

Örnek desen: gencin kart düzenlemesi `backend/app/api/kart_duzenleme.py` (kural
`app/agents/kart_duzenleme.py`, değişmeyen düzenleme hiçbir şeyi tetiklemez, değişince
arka planda yeniden hazırlama).

## Kurallar

| Durum | Sonuç |
|---|---|
| Değer değişmedi | 200, yan etkisiz (embedding, pipeline, bildirim yok) |
| İlan kapalı | 409 |
| İlanda `kabul_edildi` eşleşme var (iş birliği başladı) | 409 "Bu ihtiyaçla bir iş birliği başladı; düzenlenemez." |
| `aranan` (kapı) | Değiştirilemez; gövdede yok sayılır |
| Başkasının ilanı / genç-GİRVAK / token yok | 404 / 403 / 401 (`tests/test_sahiplik.py` deseni) |

Değişince:
1. Alanlar yazılır (onaydaki gibi: `sehir_kanonik`, ortak ilanında çalışma modeli ve
   müsaitlik `None`, `firma_turlerini_temizle`, `basari_olcutu.model_dump()`).
2. `durum in (onerildi, ilgileniliyor)` eşleşmelerin `gerekce_metni = None`.
   `genc_ilgilendi`, `kabul_edildi`, `reddedildi`, `kapandi`'ya dokunulmaz.
3. `genc_ilgilendi` ve `ilgileniliyor` eşleşmelerin aday tarafına nötr bildirim
   (`bildirim_ekle`, `app/api/bildirimler.py`), yeni tür `TUR_FIRSAT_GUNCELLENDI =
   "firsat_guncellendi"` (`app/models/bildirim.py`; `tur` kolonunda kısıt yok, migration
   yok). Metin: "İlgilendiğin bir fırsatın ayrıntıları güncellendi." Aday firma ise "siz"
   (`sahiplik.eslesmedeki_taraf`; hitap `useHitap`/rehber). Metinde e-posta yok.
4. Embedding yeniden (`embedding_hesapla`, `app/api/ihtiyac_kartlari.py`); başarılıysa
   `eslestirmeyi_arka_planda_calistir` arka planda. Başarısızsa kart yine kaydedilir,
   yanıtta `embedding_var: false` (arayüz "Eşleştirmeye hazırla" gösterir).

## Adımlar (her biri ayrı commit, testler yalnızca sonda bir kez)

1. **Saf kurallar** `backend/app/agents/ihtiyac_duzenleme.py`: `duzenlenebilir_mi(ilan_durumu,
   eslesme_durumlari)`, `degisen_alanlar(eski, yeni)`, `gerekcesi_sifirlanacak(durum)`,
   `bildirim_alacak(durum)`. Testleri LLM/DB'siz.
2. **Uç** `PATCH /ihtiyac-kartlari/{id}` (`app/api/ihtiyac_kartlari.py`), gövde
   `IhtiyacTaslagiGirdisi` (`app/schemas/tanimlama.py`: kırpma, uzunluk sınırı); zorunlu
   alan boşsa 422 `bos_alan_mesaji(..., IHTIYAC_ALAN_ADLARI, siz=True)` (onaydaki gibi,
   `app/api/tanimlama.py` › `kart_onayla`). Önce `ihtiyac_kilidi`, sonra `with_for_update`
   (kapatma ucundaki desen). Testler: sahiplik üçlüsü, kapalı 409, iş birliği 409, aynı
   değer yan etkisiz, `genc_ilgilendi` kaydı korunur, bildirim yazılır, gerekçe sıfırlanır.
   `tests/conftest.py`'de arka plan işleri sahteyle değişiyor mu kontrol et.
3. **Arayüz:** `frontend/src/app/tanimlama/page.tsx` › `TaslakBolumu` formu ortak bileşene
   ayrılır (`components/ihtiyac-formu.tsx`; onay ve düzenleme aynı formu kullanır).
   Düzenleme sayfası `/kurum/ilan/[id]/duzenle` (`<Sayfa>` + `<SayfaBasligi>`,
   `GirisKapisi roller={["kurum"]}`); panelde (`app/kurum/page.tsx`, `IlanKapatma`'nın
   yanında) açık ilan için "Düzenle". `lib/api.ts`'e `ihtiyacKartiDuzenle`. 409 cümlesi
   backend'den gösterilir.
4. **Belgeler:** api-contracts (yeni uç), agent-specs § 2 (düzenleme), roadmap'te maddeyi
   işaretle; içerik rehberine "Düzenle" / bildirim metni gerekiyorsa.

Sonda: etkilenen backend testleri + ruff (yalnızca değişen dosyalar), tsc, eslint, vitest.

## Dikkat (paralel oturum)

Aynı çalışma ağacında Doğrulama oturumu çalışıyor olabilir: `git stash` yok, `ruff format`
ve `git add` yalnızca kendi dosyalarına, migration gerekirse `alembic downgrade <rev>`
açık hedefle. Commit mesajında yapay zekâ imzası yok.
