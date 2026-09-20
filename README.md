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
- **Ajan orkestrasyonu:** LangGraph (supervisor pattern, insan-onaylı durak noktaları)
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

**2. Bağımlılıklar ve ortam.**

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -e ".[dev]"
cp .env.example .env            # Windows PowerShell: Copy-Item .env.example .env
```

`.env` içindeki `DATABASE_URL`'i kendi bağlantına göre düzenle (async sürücü: `postgresql+asyncpg://...`). Gerçek `.env` commit edilmez.

**3. Migration ve sunucu.**

```bash
alembic upgrade head            # 11 tabloyu + pgvector eklentisini oluşturur
uvicorn app.main:app --reload
```

- Sağlık kontrolü: <http://localhost:8000/health> → `{"status": "ok"}`
- Etkileşimli API dokümanı: <http://localhost:8000/docs>

**Yararlı komutlar** (`backend/` içinde):

```bash
pytest                                        # testler (DB gerektirmez)
ruff check . && ruff format .                 # lint + format
alembic revision --autogenerate -m "mesaj"    # model değişikliğinden yeni migration
alembic check                                 # modeller ile migration arasında fark var mı?
```

**Klasör yapısı:** `app/models/` (SQLAlchemy modelleri, tablo başına bir dosya) · `app/api/` (FastAPI router'ları) · `app/agents/` (LangGraph ajan kodu — Faz 1'de dolacak) · `app/schemas/` (Pydantic şemaları) · `app/core/` (ayarlar) · `app/db/` (engine/session) · `alembic/` (migration'lar).

## Frontend'i Çalıştırma

Gereksinimler: Node.js 20.19+ (Next.js 16 en az 20.9 istiyor; shadcn CLI ve ESLint 20.19+ bekliyor).

```bash
cd frontend
npm install
cp .env.local.example .env.local   # Windows PowerShell: Copy-Item .env.local.example .env.local
npm run dev
```

Arayüz: <http://localhost:3000>

`.env.local` içindeki `NEXT_PUBLIC_API_URL`, backend'in adresidir (varsayılan `http://localhost:8000`). Ana sayfanın altındaki gösterge bu adrese `/health` isteği atar — **yeşilse** iki taraf konuşuyor, **kırmızıysa** backend kapalı ya da CORS ayarı eksik demektir. Backend'i de çalıştırmayı unutma.

**Yararlı komutlar** (`frontend/` içinde):

```bash
npm run dev       # geliştirme sunucusu
npm run build     # üretim derlemesi + tip kontrolü
npm run lint      # ESLint
npx shadcn@latest add <bilesen>   # yeni shadcn/ui bileşeni ekle
```

**Klasör yapısı:** `src/app/` (App Router sayfaları) · `src/components/ui/` (shadcn/ui bileşenleri — elle düzenlenebilir) · `src/components/` (kendi bileşenlerimiz) · `src/lib/api.ts` (backend fetch sarmalayıcısı).

**Notlar:**
- shadcn/ui, **Radix** tabanlı kurulumla (`nova` preset, Lucide ikonları) eklendi — `components.json` bunu kaydeder. Şu an sadece `button`, `input`, `card` kurulu.
- `/kesif` ve `/tanimlama` sayfaları henüz boş iskelet; ana sayfadaki yönlendirmeler kırık link olmasın diye duruyor. Ajan sohbet arayüzleri Faz 1'de buraya gelecek.

## Proje Durumu

🟡 **Tasarım aşaması** — mimari, veri şeması ve API sözleşmeleri tamamlandı; geliştirme Faz 1'de başlıyor.
Yol haritası ve faz planı için bkz. [`docs/roadmap.md`](docs/roadmap.md).

## Takım

- **Zühre Nur Korhan** — Teknik geliştirme, mimari
- **Pınar Vatansever** — Paydaş iletişimi, kurumsal koordinasyon

## Lisans

Bu proje [MIT Lisansı](LICENSE) ile açık kaynak olarak paylaşılmaktadır. *(GİRVAK ile imzalanacak hizmet sözleşmesindeki fikri mülkiyet şartlarına göre bu lisans güncellenebilir.)*
