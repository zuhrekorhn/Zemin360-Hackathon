# Zemin360 — Firma ve genç yetenek buluşma platformu

[![CI](https://github.com/zuhrekorhn/Zemin360-Hackathon/actions/workflows/ci.yml/badge.svg)](https://github.com/zuhrekorhn/Zemin360-Hackathon/actions/workflows/ci.yml)
[![Lisans: MIT](https://img.shields.io/badge/lisans-MIT-blue.svg)](LICENSE)

> Genç yeteneklerin keşfinden iş birliğinin tamamlanmasına kadar bütün döngüyü tek bir paylaşılan
> veri katmanında birleştiren, altı uzman yapay zekâ ajanından oluşan açık kaynak platform.
> Türkiye Girişimcilik Vakfı (GİRVAK) ve İstanbul Kalkınma Ajansı (İSTKA) desteğiyle yürütülen
> **Zemin360** programının hackathonu için geliştirildi.

## Problem ve çözüm

Zemin360'ın altı ihtiyaç alanının her birine bir ajan karşılık gelir; ajanlar aynı kartları,
eşleşmeleri ve iş birliklerini okuyup yazar, böylece biri diğerinin çıktısını besler.

| # | İhtiyaç alanı | Ajan | Ne yapar |
|---|---|---|---|
| 01 | Genç Yeteneklerin Keşfi | **Keşif** | Kısa bir sohbetle gencin yaptıklarını yapılandırılmış bir yetenek kartına çevirir; "hiç projem yok" diyen gence okul ödevi, gönüllü iş gibi çalışmaları sorar. Genç önerildiği fırsatı baştan görür. |
| 02 | Profil & Portfolyo Doğruluğu | **Doğrulama** | Her çalışmaya dört başlıklı bir güven göstergesi (Kanıt, Sonuç, Rol, Referans): kanıt sayfasını okur, kaynağı seviyelendirir (A–D), referansa e-posta gönderir, kötüye kullanımı GİRVAK'a işaretler. Puanı model değil kural verir. |
| 03 | Kurum–Kişi Eşleşmesi | **Eşleştirme** | Firmanın ilanıyla gencin kartını (ya da iki firmayı) anlamsal olarak eşler, her öneriye "Neden uygun?" gerekçesi yazar, alakasız adayı gizler. İlgi iki yönlü: önce firma da genç de ilgi gösterebilir. |
| 04 | Yaşayan Bir Ağ | **Canlılık** | Hareketsiz kalan bağlantıları fark eder, ilgili kişiye kısa ve kişiye özel bir hatırlatma bırakır; yeni ilanı eski kartlara fırsat olarak duyurur. GİRVAK, programın altı ihtiyaç alanını gerçek sayılarla izler. |
| 05 | İhtiyaçların Net Tanımı | **Tanımlama** | Firmanın dağınık ihtiyacını sorularla ölçülebilir bir ilana çevirir (problem, başarı ölçütü, hedef değer, kısıtlar). Genç yetenek ya da iş birliği ortağı için iki kapı. |
| 06 | Şeffaf İş Birliği Takibi | **Takip** | Eşleşmenin türüne uyan süreç planını (işe alım, staj, deneme işi, tedarik…) kişiselleştirir; iki taraf planı onaylar, her adımı birlikte işaretler; tamamlanma bir sonraki eşleşmeye sinyal olarak döner. |

### Döngü

1. Genç kısa bir kayıt formundan sonra sohbetle kartını oluşturur; firma ihtiyacını tanımlar.
2. Kart ya da ilan onaylanınca linkli çalışmalar değerlendirilir ve eşleştirme arka planda çalışır.
3. Genç fırsatlarını, firma önerilerini görür; biri ilgi gösterir, öteki de ilgilenince iletişim
   açılır ve "eşleştiniz" e-postası gider.
4. İş birliği iki taraflı onaylanan bir planla ilerler, adımlar iki tarafça tamamlanır.
5. Tamamlanan iş birliği adayın sonraki eşleşmelerine güven sinyali olarak geri döner.
6. Canlılık hareketsiz kalanları hatırlatır; GİRVAK programı tek panelden izler.

Üç rol var: **genç**, **firma** (girişim, KOBİ, kurumsal) ve **GİRVAK** (program yöneticisi).

## Yapay zekâ nerede, nasıl ölçüldü

İlke: **benzerlik aday bulur, yapay zekâ doğrular, puanı kod verir.** Dil modeli metni anlamak ve
yazmak için kullanılır; listeye girme, puan ve durum geçişi test edilebilir kurallardadır.
Hiçbir taslak kullanıcı onaylamadan kaydedilmez.

| Nerede | Yapay zekânın işi | Neden kural değil de model | Ölçüm ve güvence |
|---|---|---|---|
| Keşif, Tanımlama sohbetleri | Serbest cevabı yapılandırılmış alanlara çıkarmak, eksik alanı sormak | İnsanlar kendi cümleleriyle anlatıyor | Kayıt formundaki bilgi sorulmaz, yer tutucu yazılmaz; Tanımlama'da 42 kötü girdi senaryosunun 42'si geçti (istem son değişiklikten önceki ölçüm) |
| Doğrulama | Kanıt metninden gerçek çıkarmak; her desteği **birebir alıntıyla** bildirmek | Sayfaların içeriği yapılandırılmamış | Kod alıntıyı tam metinde arar, geçmeyen destek atılır. 45 etiketli vakada Kanıt doğruluğu **%56 → %96**; sahte vakada yanlış "3": **0** (`docs/dogrulama.md` § 10) |
| Eşleştirme | Her öneriye 2-3 cümlelik gerekçe; aday gerçekten uygun mu (`uygun / kismen / uygun_degil`) | Benzerlik "aynı konu mu"yu söyler, "ihtiyacı karşılar mı"yı söylemez | 171 gerçek model çağrısında güçlü aday yanlışlıkla elenmedi (**0/78**), alakasıza "uygun" denmedi (**0/39**) (`docs/matching-algorithm.md` § 8) |
| Takip | Şablon adımlarını ilana göre kişiselleştirmek ("ne olunca tamam", hazırlık önerisi) | Her ilanın başarı ölçütü farklı | Adımlar kodda sabit; model hata verirse şablon metni kalır, plan hiç boş kalmaz |
| Canlılık | Kişiye özel, nötr hatırlatma metni | Toplu, jenerik mesaj yerine bağlama uygun dil | Model yanıt vermezse şablon; hatırlatma kaybolmaz |
| Embedding (Voyage) | Kart ve ilanı vektöre çevirmek; uzun kanıtta ilgili parçayı seçmek | Anlamsal benzerlik | Alt sınırlar etiketli havuzla ölçülerek seçildi (genç–ilan 0.48, firma–firma 0.52) |

**Neden Gemini, neden iki katman:** tek sağlayıcının hızlı ve güçlü model katmanları aynı
arayüzle kullanılıyor; hangi işin hangi katmana düştüğü tek yerde (`app/core/llm.py`) ve model
adları `.env`'den, yani model kod değişmeden değişir. Sohbetlerin alan çıkarımı her turda
çağrılır, format zaten nettir: hızlı katman, düşünme `minimal`. Varsayılan düşünmede tur ~6 sn
sürüyordu ve model kullanıcının söylemediği bilgiyi taslağa ekliyordu; `minimal`'de ~2 sn ve
uydurma yok. Eşleştirme gerekçesi, Doğrulama'nın kanıt çıkarımı ve Takip planı tek seferlik
ama nüansa bağlıdır: güçlü katman.

**Sınırlar:** model yalnızca metni anlar ve yazar, karar vermez; puan, listeye girme ve durum
geçişi kuraldır. Çıkarılan her alan kullanıcı onayından geçer. Model ya da sağlayıcı hata
verirse yedek modele, o da olmazsa şablon metne düşülür; akış durmaz.

**Maliyet ve dayanıklılık:** iki model katmanı (çıkarım için hızlı, gerekçe ve rubrik için
güçlü), her katmanda yedek model; hız sınırı ya da arızada aynı istem yedeğe gider. Her çağrının
modeli, süresi ve token kullanımı günlüğe yazılır. Kullanıcı metni istemde veri etiketleri
içindedir (istem enjeksiyonuna karşı). Ayrıntı: `docs/architecture.md` § LLM katmanları.

## Mimari

```mermaid
flowchart TD
  U[Genç, firma, GİRVAK] --> W[Next.js]
  W -->|JWT| A[FastAPI uçları]
  A --> S[Servisler, orkestrasyon]
  A --> M[Sohbet motoru, LangGraph]
  S --> G[Ajan kuralları ve istemler]
  M --> G
  S --> D[(PostgreSQL + pgvector)]
  G --> L[Gemini · Voyage · dış servisler]
```

- **Sohbet ajanları** (Keşif, Tanımlama, firma kartı) tek bir LangGraph motorunu paylaşır; yeni
  sohbet ajanı bir `AjanTanimi` yazmaktır. **Tek seferlik hesaplar** (Eşleştirme, Doğrulama,
  Takip, Canlılık) olayla tetiklenir, ağır iş yanıttan sonra arka planda çalışır.
- **Durum makineleri** (eşleşme, takip, inceleme, referans) saf fonksiyonlardır ve tabloları
  testle sabittir. Sahiplik kuralları tek modülde; başkasının kaynağı 404.
- **Dış servisler** (e-posta, depo, yedek okuyucu, virüs taraması, görsel arama) bir arayüzün
  arkasında, `.env` bayrağıyla seçilir; hatası akışı durdurmaz.
- Kullanılan desenler (Strategy, Chain of Responsibility, Adapter, Null Object, State Machine…) ve
  bilinen borç: `docs/architecture.md`.

**Teknoloji seçimleri ve nedenleri** (ayrıntı: `docs/architecture.md` § Teknoloji Kararları):

| Seçim | Neden |
|---|---|
| FastAPI (Python) | Yapay zekâ orkestrasyonuyla aynı dil, async, otomatik OpenAPI belgesi. |
| LangGraph (yalnızca sohbetler) | Yerleşik durum kalıcılığı: model hata verse sohbet kaldığı yerden sürer. Tek seferlik hesaplar grafik kullanmaz. |
| PostgreSQL + pgvector | Yüzlerce–birkaç bin kartlık hacimde ayrı vektör veritabanı gereksiz yük; ilişkisel veri ve embedding tek yerde, tek işlemde. |
| Voyage AI embedding | Dil modelinden bağımsız, ucuz çağrı; ulaşılamazsa kart yine kaydedilir, embedding sonradan tamamlanır. |
| Gemini, iki katman | Yukarıda: hızlı çıkarım, güçlü gerekçe, yedek zincir. |
| Next.js + Tailwind + shadcn/ui | Erişilebilir hazır bileşenler; tema tek CSS değişkenleri kümesinden. |
| E-posta + şifre, JWT | Bilinçli düşük karmaşıklık; sahiplik kuralları tek modülde, başkasının kaynağı 404. |

Test ve kalite araçları: pytest, Vitest, Ruff, ESLint.

## Kurulum

Gereksinimler: Python 3.11+, Node.js 20.19+, PostgreSQL 13+ ve **pgvector** eklentisi.

### 1. Veritabanı

`zemin360` adında bir veritabanı oluşturun ve pgvector'ü kurun (migration `CREATE EXTENSION
vector` komutunu kendisi çalıştırır; eklenti dosyaları sunucuda kurulu olmalı).

- **macOS:** `brew install postgresql@17 pgvector`
- **Ubuntu / Debian:** `sudo apt install postgresql-16-pgvector` (sürüm numarası kurulu
  PostgreSQL'inkiyle aynı)

<details>
<summary>Windows: pgvector'ü kaynaktan derlemek</summary>

pgvector Windows için hazır ikili dağıtmıyor; Visual Studio derleyicisi ve Windows SDK ile derlenir:

```bash
git clone --branch v0.8.1 https://github.com/pgvector/pgvector.git
```

EDB'nin Windows derlemesinde `postgres.lib`, pgvector'ün ihtiyaç duyduğu
`float_to_shortest_decimal_*` sembollerini dışarı açmıyor; bağlama adımı hata verir. Çözüm: aynı
PostgreSQL sürümünün kaynağından (`postgresql-17.x/src/common/`) `f2s.c`, `ryu_common.h`,
`d2s_intrinsics.h`, `digit_table.h` dosyalarını pgvector'ün `src/` klasörüne kopyalayıp
`Makefile.win` içindeki `OBJS` listesine `src\f2s.obj` eklemek. Sonra VS geliştirici komut isteminde:

```
set PGROOT=C:\Program Files\PostgreSQL\17
nmake /F Makefile.win
nmake /F Makefile.win install      # yönetici gerekir
```
</details>

### 2. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate             # macOS / Linux: source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env               # Windows PowerShell: Copy-Item .env.example .env
```

`.env`'de doldurulması gerekenler (gerçek `.env` commit edilmez):

| Değişken | Ne için |
|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://kullanici:sifre@localhost:5432/zemin360` |
| `JWT_GIZLI_ANAHTAR` | En az 32 karakter; boşsa backend açılmaz. Üretmek için: `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `GOOGLE_API_KEY` | Gemini (ücretli katman): sohbet, gerekçe ve değerlendirme ([aistudio.google.com](https://aistudio.google.com/apikey)) |
| `VOYAGE_API_KEY` | Embedding ([dashboard.voyageai.com](https://dashboard.voyageai.com)) |
| `DEMO_SIFRESI` | Demo hesaplarının şifresi (en az 8 karakter) |

Diğer bütün ayarların varsayılanı yerelde çalışır: e-posta `log` kipinde (bağlantılar sunucu
günlüğüne yazılır; gerçek gönderim için `EPOSTA_SAGLAYICI=brevo`), dosyalar yerel diskte, virüs
taraması ve görsel arama kapalı. Tam liste ve açıklamalar `.env.example`'da.

```bash
alembic upgrade head                 # tablolar + pgvector eklentisi
python scripts/demo_hesaplari.py     # demo hesapları ve birer kart
python scripts/demo_zenginlestir.py  # demo havuzu: firma kartları, ilanlar, genç kartları (Voyage + Gemini ister)
python run.py --reload               # http://localhost:8000 · API belgesi: /docs
```

`run.py`, Windows'ta psycopg'nin gerektirdiği olay döngüsünü sabitler; `uvicorn app.main:app`
Windows'ta `--reload` olmadan çalışmaz.

İsteğe bağlı **yedek okuyucu** (JavaScript ile çizilen ya da bot engelli kanıt sayfaları için
gerçek tarayıcı): `pip install -e ".[yedek-okuyucu]"`, `python -m playwright install chromium`,
`python -m yedek_okuyucu` (`:8100`). Çalışmıyorsa okuma onsuz biter.

### 3. Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local     # NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev                          # http://localhost:3000
```

Tarayıcıda `localhost` kullanın: `npm run dev`'in yazdığı ağ adresinden (`192.168.x.x`) açılırsa
backend CORS'u isteği reddeder. Ana sayfanın altındaki gösterge yeşilse iki taraf konuşuyor.

### Demo hesapları

Şifreleri `.env`'deki `DEMO_SIFRESI`:

| Hesap | Rol |
|---|---|
| `genc@demo.zemin360.example` | Genç (kartı ve çalışmaları hazır) |
| `kurum@demo.zemin360.example` | Firma, KOBİ (genç yetenek arıyor) |
| `girisim@demo.zemin360.example` | Firma, girişim (kartlı, doğrulanmış) |
| `kurumsal@demo.zemin360.example` | Firma, kurumsal (iş birliği ortağı arıyor) |
| `girvak@demo.zemin360.example` | GİRVAK |

`.example` alan adı gerçek bir posta kutusuna çözülmez; bu adreslere e-posta gönderilmez.

Yararlı betikler (`backend/` içinde): `scripts/yerel_sifirla.py` (yerel veritabanını boşaltır,
onay sorar), `scripts/zamani_geri_al.py --gun N` (Canlılık'ı beklemeden göstermek için tarihleri
geri alır), `scripts/canlilik_taramasi.py` (taramayı elle çalıştırır), `scripts/girvak_hesabi.py`.

## Testler ve kalite

| | Komut | Kapsam |
|---|---|---|
| Backend | `pytest` | ~2.000 test: saf kurallar ve durum makinesi tabloları, her uç için 401 / 403 / 404, gerçek veritabanında geri alınan işlemler, Doğrulama'nın kasetli (çevrimdışı) değerlendirme seti. Gerçek LLM ya da Voyage çağrısı yapmaz |
| Frontend | `npm test` | Vitest: yönlendirme, durum etiketleri, form ve e-posta taslağı gibi saf karar fonksiyonları |
| Lint ve tür denetimi | `ruff check .` · `npm run lint` · `npm run typecheck` | |
| Migration | `alembic check` | Modeller ile migration'lar arasında fark yok |

Hepsi her push'ta CI'da çalışır. Ücretli canlı ölçümler ayrı betiklerdir:
`python -m scripts.canli_karne` (Doğrulama), `python -m scripts.uygunluk_olcumu` (Eşleştirme).

## Belgeler

| Belge | İçerik |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | Katmanlar, teknoloji kararları, LLM stratejisi, desenler, bilinen borç |
| [`docs/kararlar.md`](docs/kararlar.md) | Ürünü biçimlendiren kararlar ve gerekçeleri |
| [`docs/agent-specs.md`](docs/agent-specs.md) | Her ajan ne yapar, ne yapmaz, nasıl yapar |
| [`docs/data-schema.md`](docs/data-schema.md) | 25 tablonun ER diyagramı ve tasarım kararları |
| [`docs/api-contracts.md`](docs/api-contracts.md) | Uç noktalar, yetki ve hata sözleşmesi |
| [`docs/sequence-diagrams.md`](docs/sequence-diagrams.md) | Uçtan uca dört akış |
| [`docs/matching-algorithm.md`](docs/matching-algorithm.md) | Eşleştirme formülü, alt sınırların ölçümü, uygunluk kararı |
| [`docs/dogrulama.md`](docs/dogrulama.md) | Doğrulama: kaynak seviyeleri, okuma zinciri, puan kuralları, ölçüm |
| [`docs/takip.md`](docs/takip.md) · [`docs/canlilik.md`](docs/canlilik.md) · [`docs/kimlik-ve-dongu.md`](docs/kimlik-ve-dongu.md) | Takip, Canlılık, kimlik ve eşleşme durumları |
| [`docs/design-language.md`](docs/design-language.md) · [`docs/icerik-rehberi.md`](docs/icerik-rehberi.md) | Görsel dil; arayüz metinleri ve terim sözlüğü |
| [`docs/roadmap.md`](docs/roadmap.md) | Durum ve sonraki adımlar |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Kod kuralları ve "bitti" tanımı |

## Bilinen sınırlar

- **Soğuk başlangıç:** havuz küçükken öneri azdır; arayüz bunu söyler.
- **Kimlik:** gencin gerçekten o kişi olduğu doğrulanmaz; kaynak seviyeleri ve hesap bağlama riski
  daraltır, ortadan kaldırmaz.
- **Beceri taksonomisi (ESCO)** uygulanmadı; benzerlik serbest metinden.
- **Canlılık** firma–firma eşleşmelerini henüz taramaz; tarama bir uç noktadır, zamanlayıcı yok.
- KVKK metni taslaktır; GİRVAK ile kesinleşecek.

## Takım

- **Zühre Nur Korhan** — Teknik geliştirme, mimari
- **Pınar Vatansever** — Paydaş iletişimi, kurumsal koordinasyon

## Lisans

[MIT](LICENSE). *(GİRVAK ile imzalanacak hizmet sözleşmesindeki fikri mülkiyet şartlarına göre
güncellenebilir.)*
