# [Proje Adı] — Zemin360 Hackathon

> Kurum–girişim ekosisteminde keşif, doğrulama, eşleşme ve iş birliği takibini tek bir paylaşılan veri katmanında birleştiren, altı uzman yapay zeka ajanından oluşan açık kaynak platform.

*(Proje adı henüz kesinleşmedi — repo'yu oluştururken bu başlığı güncelle.)*

## Bağlam

Bu proje, Türkiye Girişimcilik Vakfı (GİRVAK) tarafından İstanbul Kalkınma Ajansı (İSTKA) desteğiyle yürütülen **Zemin360** programının hackathonu için geliştirilmektedir. Program, kurumsal şirketler ile teknoloji tabanlı girişimler arasındaki iş birliklerini sistematik hale getirmeyi hedefliyor.

## Çözülen Problemler

Zemin360'ın tanımladığı altı problem alanının hepsine, tek bir paylaşılan profil–ihtiyaç grafiği üzerinden çalışan altı uzman ajanla çözüm üretiyoruz:

| # | Problem | Ajan |
|---|---|---|
| 1 | Genç Yeteneklerin Keşfi | Keşif Ajanı |
| 2 | Profil & Portfolyo Doğruluğu | Doğrulama Ajanı |
| 3 | Kurum–Kişi Akıllı Eşleşmesi | Eşleştirme Ajanı |
| 4 | Yaşayan Bir Ağ | Canlılık Ajanı |
| 5 | İhtiyaçların Net Tanımı | Tanımlama Ajanı |
| 6 | Şeffaf İş Birliği Takibi | Takip Ajanı |

Detaylı özellik tanımları için bkz. [`docs/agent-specs.md`](docs/agent-specs.md).

## Mimari

```mermaid
flowchart TD
  U[Kullanıcılar] --> W[Web arayüzü - Next.js]
  W --> A[API katmanı - FastAPI]
  A --> O[Ajan orkestrasyonu - LangGraph]
  O --> D[(Veri katmanı - Postgres + pgvector)]
  O --> L[LLM API]
```

Detaylı mimari ve teknoloji kararları için bkz. [`docs/architecture.md`](docs/architecture.md).
Veri şeması için bkz. [`docs/data-schema.md`](docs/data-schema.md).
Uçtan uca akışlar için bkz. [`docs/sequence-diagrams.md`](docs/sequence-diagrams.md).
API yüzeyi için bkz. [`docs/api-contracts.md`](docs/api-contracts.md).
Eşleştirme algoritmasının detayı için bkz. [`docs/matching-algorithm.md`](docs/matching-algorithm.md).

## Teknoloji Yığını

- **Backend:** Python, FastAPI
- **Ajan orkestrasyonu:** Sohbet ajanları (Keşif, Tanımlama, firma kartı) tek bir LangGraph motorunu paylaşır; sohbet durumu Postgres checkpointer'da durur. Eşleştirme, Doğrulama, Takip ve Canlılık tek seferlik hesaplardır; aralarındaki akışı `app/servisler/` yürütür. Hiçbir taslak kullanıcı onaylamadan kaydedilmez.
- **Veritabanı:** PostgreSQL + pgvector
- **Frontend:** Next.js, Tailwind, shadcn/ui
- **Embedding:** Voyage AI (voyage-4, 1024 boyut) — Anthropic'in Claude ile kullanım için resmi önerdiği sağlayıcı
- **LLM:** Katmanlı model stratejisi — yapılandırma/çıkarma görevleri için hafif model, gerekçeli akıl yürütme için güçlü model

## Backend'i Çalıştırma

Gereksinimler: Python 3.11+ ve **pgvector eklentisi kurulu** bir PostgreSQL (13+).

**1. Veritabanı.** pgvector'lu hazır bir Postgres'i Docker ile ayağa kaldırabilirsin:

```bash
docker run -d --name zemin360-db -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=zemin360 \
  -p 5432:5432 pgvector/pgvector:pg16
```

Kendi Postgres'ini kullanıyorsan `zemin360` veritabanını oluştur ve pgvector'ü kur (migration `CREATE EXTENSION vector` komutunu kendisi çalıştırır, ama eklenti dosyaları sunucuda kurulu olmalı).

<details>
<summary>Windows'a doğrudan kurulu Postgres'te pgvector (Docker kullanmıyorsan)</summary>

pgvector Windows için hazır ikili dağıtmıyor; Visual Studio derleyicisi ve Windows SDK ile kaynaktan derlemek gerekiyor:

```bash
git clone --branch v0.8.1 https://github.com/pgvector/pgvector.git
```

EDB'nin Windows derlemesinde `postgres.lib`, pgvector'ün ihtiyaç duyduğu `float_to_shortest_decimal_*` sembollerini dışarı açmıyor; bu yüzden bağlama adımı hata verir. Çözüm: aynı sürümün kaynağından (`postgresql-17.x/src/common/`) `f2s.c`, `ryu_common.h`, `d2s_intrinsics.h`, `digit_table.h` dosyalarını pgvector'ün `src/` klasörüne kopyalayıp `Makefile.win` içindeki `OBJS` listesine `src\f2s.obj` eklemek. Sonra VS geliştirici komut isteminde:

```
set PGROOT=C:\Program Files\PostgreSQL\17
nmake /F Makefile.win
nmake /F Makefile.win install      # yönetici gerekir
```

Bu kurulum **Faz 1 geliştirme makinesinde böyle yapıldı**; Docker kullanabiliyorsan yukarıdaki yol daha kısa.
</details>

**2. Bağımlılıklar ve ortam.**

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -e ".[dev]"
cp .env.example .env            # Windows PowerShell: Copy-Item .env.example .env
```

`.env` içindeki `DATABASE_URL`'i kendi bağlantına göre düzenle (async sürücü: `postgresql+asyncpg://...`). Gerçek `.env` commit edilmez.

**Oturum anahtarı (zorunlu).** `JWT_GIZLI_ANAHTAR` boşsa ya da 32 karakterden kısaysa backend açılmaz. Bir kez üretip `.env`'e yaz:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

**API anahtarları.** Ajanlar iki dış servise gidiyor, ikisinin anahtarı da `.env`'de olmalı — yoksa sohbet, kart onayı, eşleştirme gerekçesi ve kanıt değerlendirmesi çalışmaz:

| Değişken | Ne için | Nereden |
|---|---|---|
| `GOOGLE_API_KEY` | Tüm LLM çağrıları (Gemini, **ücretli katman** — faturalandırması açık projenin anahtarı) | <https://aistudio.google.com/apikey> |
| `VOYAGE_API_KEY` | Kart onaylanınca embedding üretimi (voyage-4) | <https://dashboard.voyageai.com> |

LLM çağrıları iki katmana ayrılıyor ve model adları `.env`'den okunuyor: **hızlı** katman Keşif ve Tanımlama'nın çıkarımı (`GEMINI_HIZLI_MODEL`, varsayılan `gemini-3.6-flash`, düşünme seviyesi `GEMINI_HIZLI_DUSUNME=minimal`), **güçlü** katman eşleştirme gerekçesi ve doğrulama rubriği (`GEMINI_GUCLU_MODEL`, varsayılan `gemini-3.8-flash`). Her katmanın bir yedek modeli var; sağlayıcı arızasında (5xx, 30 sn'yi aşan zaman aşımı), anlık hız sınırında (429) ya da model kullanılamadığında (404) aynı çağrı yedeğe düşer. Açılışta dört model adı sağlayıcının listesiyle karşılaştırılır; bulunamayan varsa sunucu log'unda uyarı çıkar. İkisi de yanıt veremezse uç nokta `503` (arıza) ya da `429` (hız sınırı) döner; sohbet checkpointer'da durduğu için aynı `oturum_id` ile kaldığın yerden devam edebilirsin. Her çağrının modeli, süresi ve token kullanımı sunucu günlüğüne yazılır (`LLM yanıtladı [iş] model: … token`). Değişkenlerin tamamı `.env.example`'da.

**3. Migration ve sunucu.**

```bash
alembic upgrade head            # tüm tabloları + pgvector eklentisini oluşturur
python run.py --reload          # http://localhost:8000
```

**Demo hesaplarıyla temiz başlangıç.** `.env`'e `DEMO_SIFRESI` (en az 8 karakter) ekle, sonra:

```bash
python scripts/yerel_sifirla.py      # yerel DB'yi boşaltır; onay için veritabanı adını sorar
python scripts/demo_hesaplari.py     # genc@ / kurum@ / girvak@demo.zemin360.example + birer kart
python scripts/demo_zenginlestir.py  # demo havuzunu büyütür: 3 firma kartı, 2 ilan, 9 genç kartı
```

Demo genç kartı ile kurumun ihtiyaç kartı birbirine önerilecek şekilde seçildi; betik benzerliği ve skoru yazdırır. Üç hesabın şifresi `DEMO_SIFRESI`. `demo_zenginlestir.py` yalnızca ekler (yeniden çalıştırmak güvenli), `demo_hesaplari.py`'den sonra çalışır, Voyage ve Gemini anahtarı ister; sonunda üç ilan için eşleştirme çalıştırır. Adlar kurgusal, e-postalar `.example` alan adında.

`run.py` yerine `uvicorn app.main:app` da çalışır — ama **Windows'ta `--reload` olmadan çalışmaz**: LangGraph'ın checkpointer'ı psycopg kullanıyor, psycopg de Windows'un varsayılan ProactorEventLoop'uyla uyumsuz. `run.py` döngüyü doğru olanla sabitliyor, sebebini de dosyanın başında anlatıyor.

- Sağlık kontrolü: <http://localhost:8000/health> → `{"status": "ok"}`
- Etkileşimli API dokümanı: <http://localhost:8000/docs>

**Yararlı komutlar** (`backend/` içinde):

```bash
pytest                                        # testler (API anahtarı gerektirmez; yerel DB yoksa DB testleri atlanır)
python scripts/kesif_e2e.py                   # Keşif Ajanı uçtan uca (sunucu + gerçek API'ler)
python scripts/kesif_e2e.py b                 # sadece "hiç projem yok" senaryosu
python scripts/eslestirme_e2e.py <kurum_id> --tohum   # Eşleştirme pipeline'i uçtan uca
python scripts/yerel_sifirla.py              # yerel DB'yi boşaltır (onay sorar; production'da çalışmaz)
python scripts/demo_hesaplari.py             # genç/kurum/GİRVAK demo hesapları + birer kart (.env: DEMO_SIFRESI)
python scripts/demo_zenginlestir.py          # demo havuzuna firma, ilan ve genç kartları ekler (yalnızca ekler)
python scripts/girvak_hesabi.py --email …    # GİRVAK hesabı açar (açık kayıtla açılamaz)
python -m yedek_okuyucu                      # yedek okuyucu (Playwright) servisi, :8100 (kurulum: yedek_okuyucu/README.md)
ruff check . && ruff format .                 # lint + format
alembic revision --autogenerate -m "mesaj"    # model değişikliğinden yeni migration
alembic check                                 # modeller ile migration arasında fark var mı?
```

**Kimlik (Faz B):** `POST /auth/kayit`, `POST /auth/giris`, `GET /me`. `/health`, kayıt/giriş ve token'lı referans uçları dışında her uç `Authorization: Bearer <token>` ister; 401 token yok/geçersiz, 403 rol uygun değil, 404 başkasının kaynağı. Bildirimler `GET /bildirimler`, `POST /bildirimler/{id}/okundu`, `POST /bildirimler/hepsini-oku`; GİRVAK `GET /girvak/sayilar`.

**Takip (Faz C):** `GET /isbirligi/{id}`, `POST /isbirligi/{id}/plan-oner`, `POST /isbirligi/{id}/milestone-ekle`, `PATCH|DELETE /isbirligi/{id}/milestone/{mid}`, `POST /isbirligi/{id}/plan-onayla`, `POST /isbirligi/{id}/milestone/{mid}/isaretle|isareti-geri-al`.

**Ajan uç noktaları:** Doğrulama `POST /dogrulama/kalem/{id}/kanit` (kanıt parçası ekler ve değerlendirir; kalem uçları `api-contracts.md`'de), `POST /dogrulama/referans-yaniti` (girişsiz, token ile), `POST /dogrulama/kalem/{id}/itiraz`, `GET /dogrulama/kalem/{id}` · Keşif `/kesif/sohbet/baslat|cevap`, `/kesif/kart/onayla`, `GET /yetenek-kartlari/{id}` · Tanımlama `/tanimlama/sohbet/baslat|cevap`, `/tanimlama/kart/onayla`, `GET /ihtiyac-kartlari/{id}` · Eşleştirme `POST /eslestirme/calistir`, `GET /eslestirme/oneriler/{kurum_id}`, `POST /eslestirme/ilgileniyorum`, `POST /eslestirme/{id}/kabul|red`, `GET /eslestirme/bana-gelenler`, `GET /eslestirme/onerilerim`, `GET /isbirliklerim`. Tam liste: [`docs/api-contracts.md`](docs/api-contracts.md).

**Klasör yapısı:** `app/models/` (SQLAlchemy modelleri, tablo başına bir dosya) · `app/api/` (FastAPI router'ları) · `app/agents/` (`sohbet_motoru.py` ortak sohbet motoru + `kesif.py`, `tanimlama.py`, `eslestirme.py`, `dogrulama.py`, `takip.py`; `eslesme_durumu.py` ve `takip_durumu.py` durum makineleri) · `scripts/` (elle çalıştırılan denemeler) · `app/schemas/` (Pydantic şemaları) · `app/core/` (ayarlar) · `app/db/` (engine/session) · `alembic/` (migration'lar).

## Frontend'i Çalıştırma

Gereksinimler: Node.js 20.19+ (Next.js 16 en az 20.9 istiyor; shadcn CLI ve ESLint 20.19+ bekliyor).

```bash
cd frontend
npm install
cp .env.local.example .env.local   # Windows PowerShell: Copy-Item .env.local.example .env.local
npm run dev
```

Arayüz: <http://localhost:3000>

**Adres çubuğunda `localhost` kullan.** `npm run dev` bir de "Network" adresi (`http://192.168.x.x:3000`) yazar; sayfa o adresten açılırsa Next.js 16 geliştirme dosyalarını engeller ve backend CORS'u (`CORS_ORIGINS=http://localhost:3000`) isteği reddeder. Sayfa görünür ama düğmeler çalışmaz, giriş ilerlemez.

`.env.local` içindeki `NEXT_PUBLIC_API_URL`, backend'in adresidir (varsayılan `http://localhost:8000`). Ana sayfanın altındaki gösterge bu adrese `/health` isteği atar — **yeşilse** iki taraf konuşuyor, **kırmızıysa** backend kapalı ya da CORS ayarı eksik demektir. Backend'i de çalıştırmayı unutma.

**Yararlı komutlar** (`frontend/` içinde):

```bash
npm run dev       # geliştirme sunucusu
npm run build     # üretim derlemesi + tip kontrolü
npm run lint      # ESLint
npm test          # Vitest birim testleri (src/**/*.test.ts)
npx shadcn@latest add <bilesen>   # yeni shadcn/ui bileşeni ekle
```

**Klasör yapısı:** `src/app/` (App Router sayfaları) · `src/components/ui/` (shadcn/ui bileşenleri — elle düzenlenebilir) · `src/components/` (kendi bileşenlerimiz) · `src/lib/api.ts` (backend fetch sarmalayıcısı).

**Notlar:**
- **Tema** [`docs/design-language.md`](docs/design-language.md)'den geliyor: palet `src/app/globals.css` içindeki CSS değişkenlerinde, fontlar (Fraunces + IBM Plex Sans) `src/app/layout.tsx` içinde tanımlı. Renk veya font değiştireceksen önce o belgeye bak.
- shadcn/ui, **Radix** tabanlı kurulumla (`nova` preset, Lucide ikonları) eklendi — `components.json` bunu kaydeder. Şu an sadece `button`, `input`, `card` kurulu. Yeni bileşenler shadcn'in varsayılan renkleriyle değil, paletteki değişkenlerle gelir.
- **Kimlik:** `/giris` ve `/kayit` (rol kayıtta seçilir). Token tarayıcıda (`src/lib/token.ts`), her istekte `Authorization: Bearer` ile gidiyor. Oturumun tek kaynağı `GET /me` (`src/lib/oturum.tsx`): token değişince, sayfa değişince ve 60 sn'de bir tazelenir, üst menüdeki bildirim rozeti de buradan. Giriş gerektiren sayfalar `GirisKapisi`'yle sarılı (`src/components/giris-kapisi.tsx`): girişsizse `/giris?sonra=…`, rolü uymuyorsa kendi paneli. Yönlendirme kuralları `src/lib/yonlendirme.ts`'de (testli).
- **Paneller:** `/genc` (kartlarım, kanıt bekleyenler, bana gelen ilgiler — Kabul et / Reddet, iş birliklerim), `/kurum` (ihtiyaç kartlarım, önerilerim, iş birliklerim), `/girvak` (sayılar), `/bildirimler`. Ortak parçalar `src/components/panel.tsx`.
- **İş birliği (Faz C):** `/isbirligi/{id}` iki tarafa aynı sayfa — taslak planda ajanın önerisi, düzenleme ve iki taraflı onay; sonra zaman çizelgesi (gecikme etiketi, iki taraflı işaret, kanıt linki); tamamlanınca bant ve gencin kartında "tamamlanmış pilot" rozeti (`PilotRozeti`, `src/components/kart.tsx`). Görünüm cümleleri `src/lib/takip.ts`'de (testli).
- `/kesif` ve `/tanimlama` sayfaları çalışan sohbet arayüzleri: sohbet → taslak → onay formu → kaydedilen kart. Ortak görsel parçalar `src/components/sohbet.tsx` içinde.
- `/kart/{id}` yetenek kartı ve Doğrulama ekranı: kartın sahibi genç için çıktı başına dört bileşenli güven göstergesi, kanıt ekleme, referans isteği ve itiraz (`src/components/kanit.tsx`); kurum ve GİRVAK kartı salt okunur görür.
- `/kurum/oneriler?ihtiyac=<id>` eşleştirme önerileri: skor, gerekçe, gencin adı ve "İlgileniyorum". Eşik ve "az sonuç" uyarısı backend yanıtından geliyor, arayüzde sabit değil.
- `/referans?token=…` referans kişinin girişsiz yanıt sayfası: iddia formun üstünde gösterilir, harcanmış ya da süresi geçmiş link form açmaz.
- Kart ve gerekçe görünümünün paylaşılan parçaları `src/components/kart.tsx` içinde; ana sayfadaki örnek blok da bunları kullanıyor (statik veriyle, backend kapalıyken de çizilsin diye).

## Proje Durumu

🟢 **Faz A-D, genç akışı ve firma akışı tamamlandı; altı ajan da çalışıyor.** Üç rol (genç, firma, GİRVAK) kendi paneliyle giriyor. Firma iki kapıdan girer: genç yetenek ya da iş birliği ortağı (girişim, KOBİ, kurumsal) arar; firmalar arası eşleşme, ilgi ve iş birliği genç tarafıyla aynı döngüden geçer. Döngü kapalı:

1. Genç kısa bir kayıt formundan sonra sohbetle yetenek kartını oluşturur.
2. Kart onaylanınca linkli çalışmalar değerlendirilir ve kart açık ihtiyaçlarla eşleşir.
3. Genç eşleştiği fırsatları görür ve ilgi gösterebilir; firma da ilgi gösterebilir. İki taraf da ilgilenince iletişim açılır ve iş birliği başlar.
4. Plan iki tarafça onaylanır, adımlar iki taraflı tamamlanır.
5. Tamamlanan iş birliği gencin kartına ve eşleşme skoruna geri döner.
6. Canlılık, hareketsiz kalan bağlantıları hatırlatır; GİRVAK programı panelden izler.

| Ajan | Durum |
|---|---|
| **Keşif** | Çalışıyor. Kayıt formunun bilgilerini sormaz; çalışma başına kanıt ve referans da sorulur. Arayüz: `/kesif` |
| **Tanımlama** | Çalışıyor. Sokratik sohbet → ihtiyaç kartı. Arayüz: `/tanimlama` |
| **Eşleştirme** | Çalışıyor. Sert filtre → benzerlik alt sınırı → skor → gerekçe. İhtiyaç ve yetenek kartı onayında/düzenlemesinde arka planda. İlgi iki taraflı. Arayüz: `/kurum/oneriler`, `/genc` |
| **Doğrulama** | Çalışıyor. Link, dosya ve görsel okuma (platform okuyucuları, yedek okuyucu), hesap bağlama, referans e-postası, kötüye kullanım işaretleri, link çürümesi yoklaması, itiraz. Linkli çalışma otomatik puanlanır, düzenlenince sıfırlanır. Arayüz: `/kart/{id}`, `/referans`, GİRVAK'ta gözlem paneli |
| **Takip** | Çalışıyor. Plan önerisi, iki taraflı onay ve işaretleme, tamamlanma sinyali. Arayüz: `/isbirligi/{id}` |
| **Canlılık** | Çalışıyor. Hareketsizlik hatırlatmaları (yanıtsız genç ilgisi dahil), yeni fırsat, GİRVAK paneli. Arayüz: `/girvak` |

Genç akışının kararları ve bilinen sınırları: [`docs/plans/genc-akisi.md`](docs/plans/genc-akisi.md), firma akışınınki: [`docs/plans/firma-akisi.md`](docs/plans/firma-akisi.md). Elle deneme senaryoları: [`genc-akisi-deneme.md`](docs/plans/genc-akisi-deneme.md), [`firma-akisi-deneme.md`](docs/plans/firma-akisi-deneme.md). Arayüz metinleri [`docs/icerik-rehberi.md`](docs/icerik-rehberi.md)'ye uyar.

**Doğrulama kapsamı:** referans e-postası referans kişiye doğrudan gider (`EPOSTA_SAGLAYICI`: varsayılan `log` kipinde bağlantı sunucu günlüğüne yazılır, `resend` için anahtar ve doğrulanmış alan adı gerekir); token ve yanıt linki hiçbir API yanıtında yer almaz. Referans yanıt uç noktası yalnızca iddianın başlığını ve durumu döner; kanıt durumu yalnızca çıktının sahibi gence ve GİRVAK'a açıktır. Zaman aşımı (7 gün) ve link çürümesi için ayrı zamanlayıcı yok: geçişi okuma anı ya da Canlılık taraması (`POST /canlilik/tarama`) yapar. Puan kuralı (seviye tavanları, "—" ceza değil) ve ölçüm: `docs/plans/dogrulama-iyilestirme.md`; değerlendirme seti ve karneler `backend/tests/degerlendirme_seti/`. Canlı karne: `python -m scripts.canli_karne` (ücretli, elle ya da platform cron'uyla). Kart bonusunun kart düzeyi formülü Eşleştirme incelemesinde karara bağlanacak, bugünkü kural değişmedi (`docs/matching-algorithm.md` § 4.1).

**Eşleştirme döngüsü:** kurum "ilgileniyorum" der (`ilgileniliyor`), genç kabul ederse iş birliği açılır ve e-postalar iki tarafa görünür; reddederse `reddedildi`. Gencin adı baştan görünür, yalnızca e-postalar kabulle açılır. Öneri listesi iki sınırla eleniyor ve ikisi farklı şeyi ölçüyor: benzerlik alt sınırı 0.45 ("bu aday konuyla ilgili mi", skordan önce) ve skor eşiği %40 ("ilgili adaylar arasında gösterilmeye değer mi"). Gerekçe LLM'den gelmiyorsa öneri gerekçesiz gösterilir, skor yine de geçerlidir. Her geçişte ilgili tarafa uygulama içi bildirim gider (gerçek e-posta yok). Skor formülünün ESCO taksonomi bileşeni de MVP dışında (bkz. `docs/matching-algorithm.md`).

İki sohbet ajanı aynı motoru paylaşıyor (`backend/app/agents/sohbet_motoru.py`): grafik iskeleti, taslak birleştirme ve yedek modele düşen LLM zinciri orada; soru seti, çıkarım şeması ve ajana özel dallar ajan dosyasında.

**Takip kapsamı:** ajan plan ve özet önerir, karar vermez; tamamlanma bir kuraldır (son adım iki tarafça tamamlanınca). Onaylanan plan kilitlidir. Tamamlanmış pilot, Eşleştirme'nin doğrulama bonusuna toplamsal girer (en çok +0.125; pilotsuz kartın skoru değişmez, alakayı yaratmaz). Durum özeti kesilebilir iş: çökerse ya da kesilirse döngü aynen çalışır.

Kanıt linki kontrolü iç ağa istek atmaz (SSRF engeli, `backend/app/core/guvenli_istek.py`). Sırada: elle deneme, toplu metin denetimi ve yayına alma.
Yol haritası ve faz planı için bkz. [`docs/roadmap.md`](docs/roadmap.md).

## Takım

- **Zühre Nur Korhan** — Teknik geliştirme, mimari
- **Pınar Vatansever** — Paydaş iletişimi, kurumsal koordinasyon

## Lisans

Bu proje [MIT Lisansı](LICENSE) ile açık kaynak olarak paylaşılmaktadır. *(GİRVAK ile imzalanacak hizmet sözleşmesindeki fikri mülkiyet şartlarına göre bu lisans güncellenebilir.)*
