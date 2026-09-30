# Mimari

## Genel Bakış

Sistem, ortak bir veri katmanı üzerinde çalışan altı uzman ajandan oluşuyor. Hiçbir ajan diğerinin işini bloklamıyor — Keşif/Tanımlama akışları kullanıcı etkileşimine bağlı senkron çalışırken, Eşleştirme ve Canlılık ajanları arka plan işleri (background jobs) olarak tasarlanıyor.

```mermaid
flowchart TD
  U[Kullanıcılar - Genç yetenekler ve kurumlar] --> W[Web arayüzü - Next.js]
  W --> A[API katmanı - FastAPI]
  A --> O[Ajan orkestrasyonu - LangGraph]
  O --> D[(Veri katmanı - Postgres + pgvector)]
  O --> L[LLM API - Katmanlı model stratejisi]
```

## Teknoloji Kararları

| Katman | Seçim | Gerekçe |
|---|---|---|
| Ajan orkestrasyonu | **LangGraph** | Durum kalıcılığını (checkpointing) native destekliyor; CrewAI/AutoGen'e göre bu ihtiyaca en uygun olanı. **Kodda nasıl kullanılıyor (30 Eyl):** yalnızca çok turlu sohbet ajanları (Keşif, Tanımlama, firma kartı) bir `StateGraph` olarak derlenir ve aynı motoru paylaşır (`app/agents/sohbet_motoru.py`); sohbet Postgres checkpointer'da durur, LLM hatasında kaldığı yerden sürer. Eşleştirme, Doğrulama, Takip ve Canlılık tek seferlik hesaplardır, grafik kullanmaz; aralarındaki akışı `app/servisler/` yürütür. Supervisor ajanı ve LangGraph `interrupt` kullanılmıyor: insan onayı uç noktalarla sağlanır (taslak onaylanmadan kaydedilmez, güven göstergesine itiraz edilir, eşleşmede karar insanındır). |
| Backend | **FastAPI (Python)** | Orkestrasyon katmanıyla aynı dilde, async destekli; bu sınıf ürünlerde sektörün en yaygın kombinasyonu. |
| Veritabanı | **PostgreSQL + pgvector** | Ayrı bir vektör veritabanı (Qdrant/Pinecone) bu veri hacminde (yüzlerce–birkaç bin kayıt) gereksiz altyapı yükü. Tek veritabanında hem ilişkisel veri hem embedding tutuluyor. |
| Frontend | **Next.js + Tailwind + shadcn/ui** | Güncel, hızlı ve profesyonel görünümlü bir arayüz için sektör standardı — UI/UX değerlendirme kriterini doğrudan destekliyor. |
| Embedding | **Voyage AI (voyage-4, 1024 boyut)** | Anthropic'in Claude ile kullanım için resmi önerdiği sağlayıcı — ilk 200M token ücretsiz, ön ödeme istemiyor (hackathon için pratikte sıfır maliyet). Ödeme yöntemi eklenmemiş hesapta dakikada 3 istek sınırı var: art arda kart onaylarında embedding 429'a düşebilir; kart yine kaydedilir, "eşleştirmeye hazırla" ile yeniden hesaplanır. |
| Kimlik (Faz B) | **E-posta + şifre, JWT (HS256, 7 gün), Bearer + localStorage** | Karmaşıklık bilinçli düşük: refresh token, OAuth ve httpOnly cookie yok (ürünleşme dönemi). Şifre argon2id (`argon2-cffi`). Kimlik ayrı `hesap` tablosunda, profil `kullanici`/`kurum`'da (1-1) — giriş tek tabloda, GİRVAK'ın profile ihtiyacı yok, bildirim ve yetki tek kimliğe bağlanıyor. Sahiplik kuralları tek dosyada (`app/api/sahiplik.py`); başkasının kaynağı 404 (varlık sızmasın). Gerekçeler ve seçenek karşılaştırması: `faz-b-kimlik-ve-dongu.md` § 1. |
| LLM | **Gemini, ücretli katman, iki model katmanı** | Sağlayıcı Faz 1'den beri Gemini: Anthropic ön ödeme istiyordu, Gemini istemiyordu. Faz A'da ücretsiz katmandan ücretli anahtara geçildi (günde 20 istek demo için yetmiyordu); sağlayıcı değişmedi. **Katmanlar** (`app/core/llm.py`): *hızlı* — Keşif ve Tanımlama'nın yapılandırılmış çıkarımı (varsayılan `gemini-3.6-flash`, yedek `gemini-3.1-flash-lite`, düşünme seviyesi `minimal` — `GEMINI_HIZLI_DUSUNME`; modelin varsayılanında tur ~6 sn sürüyor ve çıktının %70-90'ı düşünmeydi, üstelik kullanıcının söylemediği bir bilgiyi taslağa ekledi; `minimal`'de tur ~2 sn, uydurma yok); *güçlü* — eşleştirme gerekçesi ve doğrulama rubriği (varsayılan `gemini-3.8-flash`, yedek `gemini-3.6-flash`). Model adları `.env`'den okunur (`GEMINI_HIZLI_MODEL`, `GEMINI_GUCLU_MODEL` ve yedekleri), kod değişmeden değişir. Güçlü katmanın varsayılanı bilerek kararlı (preview olmayan) bir model: demo 9-11 Ekim'de, preview modellerin hız sınırı ve kararlılığı belirsiz. Yeni anahtarlara kararlı bir Pro açık değil: `gemini-2.5-pro` model listesinde görünüyor ama çağrıda 404 dönüyor, `gemini-pro-latest` ise `gemini-3.1-pro-preview`'a gidiyor. Bu yüzden şimdilik en yeni kararlı Flash; Pro'ya gerek olup olmadığı aynı girdiyle Pro/Flash karşılaştırılarak kararlaştırılacak. **Yedek model** LangChain `with_fallbacks` ile aynı prompt ve şemayı ikinci modele gönderir. Amacı sağlayıcı arızası: 5xx (`GoogleAPIError`), zaman aşımı (`httpx.TimeoutException`, `GEMINI_ZAMAN_ASIMI_SN`, varsayılan 30 sn) ve anlık hız sınırı (429, `GoogleRateLimitError` — ücretli katmanda dakikalık sınır; ücretsiz katmanda günlük kotaydı) ve kullanılamayan model (404, `GoogleModelNotFoundError` — log'a `MODEL KULLANILAMIYOR` hatası ve düzeltilecek `.env` değişkeni yazılır). Hepsi model başına oluşuyor, yedek model o an genellikle çalışır. **Diğer 4xx listede yok:** hatalı istek (400) ya da yetki (401/403) ikinci modelde de aynı şekilde başarısız olur. Açılışta `.env`'deki dört model adı sağlayıcının model listesiyle karşılaştırılır; bulunamayan uyarılır, uygulama durmaz, kontrol başarısızsa sessizce geçilir. İki model de yanıt veremezse istek 503 (arıza, zaman aşımı) ya da 429 (hız sınırı) olarak döner — ayrıntı `app/core/hatalar.py`. SDK'nın kendi tekrar sayısı 6'dan **2'ye** indirildi (`MAKS_TEKRAR`): asıl tekrar stratejisi yedek model, aynı modeli üstel beklemeyle tekrar tekrar denemek dakikalar kaybettiriyordu. **Gözlemlenebilirlik:** her çağrı sunucu günlüğüne tek satır yazar: iş adı, model, süre, deneme sırası ve token kullanımı (girdi, çıktı, düşünme, toplam). |

## LLM Maliyet/Performans Stratejisi

Görevler üç kategoriye ayrılıyor, her biri farklı model gerektiriyor:

| Kategori | İşler | Katman | Varsayılan model (yedek) |
|---|---|---|---|
| **Yapılandırma/çıkarma** | Keşif ve Tanımlama sohbetlerinin alan çıkarımı | hızlı | `gemini-3.6-flash` (`gemini-3.1-flash-lite`) |
| **Gerekçeli akıl yürütme** | Eşleştirme'nin "neden eşleşti" gerekçesi, Doğrulama'nın rubrik puanlaması | güçlü | `gemini-3.8-flash` (`gemini-3.6-flash`) |
| **Embedding** | Kart temsil metni → vektör | — | Voyage `voyage-4` (LLM'den bağımsız, ayrı ve ucuz çağrı) |

Çıkarımda format zaten net, ince akıl yürütme gerekmiyor; sohbetin her turunda çağrıldığı için hız ve maliyet belirleyici. Gerekçe ve rubrik tek seferlik ama nüans önemli: kartlardaki somut noktalara atıf, kurallara uyum (itiraz notu beyandır, sayı uydurma yok). Bu katmanlama maliyetin büyük kısmını ucuz modelde tutarken kalite gereken yerde güçlü modeli devreye sokuyor. Güçlü modelin gerçekten gerekli olup olmadığı, aynı girdiyle Pro ve Flash karşılaştırılarak ölçülüyor; model `.env`'den değiştirilebildiği için karar kod değişikliği gerektirmiyor.

## Katmanlar (backend)

| Katman | Ne durur | Kural |
|---|---|---|
| `app/agents/` | Saf kurallar (durum makineleri, eşikler, skor, düzenleme ve güçlendirme hesapları) ve dil modeli çağrıları | Veritabanı yok; testle sabitlenmiş tablolar. Yapay zekâ öneri ve metin üretir, karar kuraldadır |
| `app/servisler/` | Birden fazla uç ve arka plan işinin paylaştığı orkestrasyon: eşleştirme pipeline'ı, kart hazırlama (embedding → otomatik puanlama → yeniden eşleştirme), kart düzenleme, doğrulama rubriğinin yazılması, ilgi akışının yan etkileri (iş birliği açma, ihtiyacı kapatma) | Genç akışında açıldı (`plans/genc-akisi.md` § 11) |
| `app/api/` | Uçlar: yetki (401/403/404), istek/yanıt şeması, servisi çağırma, bildirim | İnce kalır; aynı iş iki uçta yazılmaz |

Arka plan işleri `BackgroundTasks` ile yanıttan sonra çalışır, kendi oturumunu açar, hatayı yutar ve idempotenttir (danışma kilidi, `ON CONFLICT`, versiyon kontrolü, satır kilidi). Testler hepsini `tests/conftest.py`'de sahteyle değiştirir.

## İlgi akışı (iki kapı)

Eşleşme durumu tek alanda (`eslesme.durum`), geçiş kuralı tek fonksiyonda (`app/agents/eslesme_durumu.py › gecis`):

```
onerildi ──firma "ilgileniyorum"──▶ ilgileniliyor ──genç kabul──▶ kabul_edildi
   │                                              └──genç red────▶ reddedildi
   └──genç ilgi (iletişim onayıyla)──▶ genc_ilgilendi ──firma "ilgileniyorum"──▶ kabul_edildi (karşılıklı ilgi)
                                         ├──firma "şimdilik değil"──▶ kapandi
                                         └──genç geri çeker──────────▶ onerildi
   onerildi | genc_ilgilendi | ilgileniliyor ──ihtiyaç kapandı──▶ kapandi
```

- Genç eşik üstü önerileri "fırsat" olarak görür; ilgisi skoru değiştirmez.
- `kabul_edildi` iş birliğini açar, e-postaları yalnızca iki tarafa gösterir ve plan önerisini başlatır.
- Karar verilmiş kayıtlar yeniden hesapta korunur: pipeline yalnızca `onerildi` siler, `genc_ilgilendi`'nin skorunu ve gerekçesini de değiştirmez.
- Ayrıntı: `plans/genc-akisi.md` § 4, `faz-b-kimlik-ve-dongu.md` § 5.

**Firma–firma (firma akışı, `plans/firma-akisi.md` § 3-4):** aynı tablo, aynı makine, aynı pipeline. Eşleşmenin adayı yetenek kartı ya da firma kartıdır (tam biri dolu); aday kaynağını ilanın `aranan`'ı seçer. Makinedeki "genç" rolü **aday tarafı** demektir: ortak firma o taraftadır. Ortak firmanın hesabı da firma rolünde olduğu için taraf hesabın rolünden değil eşleşmeden okunur (`sahiplik.eslesmedeki_taraf`); aday firmanın uçları ayrı ve incedir (`/firma-ilgi`, `/firma-kabul`…). İş birliği ve takip değişmeden iki firmaya açılır.

## Repo Yapısı

```
/docs               — bu klasör: mimari, şema, API sözleşmeleri, yol haritası
/backend            — FastAPI + LangGraph: app/{api,agents,models,schemas,core,db}, alembic/, scripts/, tests/
/frontend           — Next.js (App Router): src/{app,components,lib}
```

Klasörlerin ayrıntısı README'nin "Klasör yapısı" satırlarında.

Monorepo tercih edildi — solo geliştirici + 3 haftalık sprint için ayrı repolar arası senkronizasyon yükü gereksiz.
