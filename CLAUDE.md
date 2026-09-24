# Proje Bağlamı — Claude Code için

Bu dosyayı her oturum başında otomatik okuyorsun. Kod yazmadan önce ilgili `docs/` dosyasını oku — tahmin yürütme, tasarım zaten yapıldı.

## Proje Nedir

Zemin360 Hackathon (GİRVAK) için geliştirilen, kurum–girişim ekosisteminde 6 problemi tek bir paylaşılan veri katmanı üzerinde çözen, 6 uzman AI ajanından oluşan açık kaynak platform. Tam bağlam: [`README.md`](README.md).

## Önce Oku — Tasarım Zaten Tamamlandı

Herhangi bir özellik üzerinde çalışmadan önce, ilgili dosyayı `docs/` altında oku:

| Konu | Dosya |
|---|---|
| Mimari, teknoloji kararları ve gerekçeleri | `docs/architecture.md` |
| Veri şeması (tüm tablolar, alanlar, ilişkiler) | `docs/data-schema.md` |
| Her ajanın ne yapıp ne yapmayacağı, nasıl çalışacağı | `docs/agent-specs.md` |
| Eşleştirme Ajanı'nın tam formülü ve embedding stratejisi | `docs/matching-algorithm.md` |
| Uçtan uca akışlar (happy path, doğrulama timeout dalı) | `docs/sequence-diagrams.md` |
| Tüm endpoint listesi | `docs/api-contracts.md` |
| Renk paleti, tipografi, yerleşim ilkeleri (her frontend işinde kullan) | `docs/design-language.md` |
| Faz planı ve mevcut durum | `docs/roadmap.md` |

**Kural:** Bu dosyalarda yazan bir tasarım kararıyla çelişen bir yaklaşım önereceksen (örn. farklı bir kütüphane, farklı bir veri modeli), önce sor — sessizce değiştirme. Sebebi belgelenmiş kararlar var, gerekçesiz sapma kafa karışıklığı yaratır.

## Şu An Neredeyiz

Faz 0 ve Faz 1 tamamlandı, **Faz 2 sürüyor**: Keşif, Tanımlama, Eşleştirme ve Doğrulama ajanları çalışıyor ve dördünün de arayüzü bağlı (`/kesif`, `/tanimlama`, `/kurum/oneriler`, `/kart/{id}`, `/referans`). Eşleştirme'de sadece kurum tarafı var (öneri + "ilgileniyorum"), Genç'in bildirimi Faz 3+. Giriş/kayıt akışı da Faz 3: kimlikler şimdilik tarayıcıda tutuluyor. Sırada Canlılık ve Takip ajanları. Detaylı takvim: `docs/roadmap.md`.

**Eşleştirmede iki ayrı sınır var, karıştırma:** benzerlik alt sınırı (0.45) "bu aday konuyla ilgili mi" sorusunu skordan ÖNCE yanıtlar; skor eşiği (%40) "ilgili adaylar arasında gösterilmeye değer mi" sorusunu sonra. Doğrulama bonusu sıralamayı etkiler, alakayı yaratmaz (`docs/matching-algorithm.md` § 5).

**Hatalar kullanıcıya doğru cümleyi söylemeli:** yakalanmayan istisnalar `app/core/hatalar.py`'deki global işleyiciden CORS başlığıyla ve `{"detail": ...}` gövdesiyle dönüyor — aksi halde tarayıcı her hatayı "backend'e ulaşılamadı" sanıyor. LLM tarafında kota 429, sağlayıcı arızası 503; ikisi de önce yedek modele düşürülür.

**Zamanlayıcı yok, bilinçli:** cron/kuyruk altyapısı kurmuyoruz. Eşleştirme "arka plan işi" bir endpoint olarak duruyor; Doğrulama'nın 7 günlük zaman aşımı da okuma anında hesaplanıyor. Yeni bir periyodik iş gerekirse aynı deseni izle.

**Her ajan sohbet ajanı değil:** Keşif ve Tanımlama çok turlu konuşur ve aynı motoru paylaşır; Eşleştirme ve Doğrulama tek seferlik hesaplardır (SQL → pgvector → skor → tek LLM çağrısı), `sohbet_motoru.py`'yi kullanmaz. LLM sağlayıcısı ve yedek model zinciri ikisinde de ortak: `app/core/llm.py`.

İki sohbet ajanı **aynı motoru** paylaşıyor (`app/agents/sohbet_motoru.py`); yeni bir sohbet ajanı gerekirse grafik iskeletini kopyalama, bir `AjanTanimi` yaz. Ajana özel olan şey soru seti, çıkarım şeması ve varsa ek dalıdır.

## Teknoloji Yığını (hızlı referans)

Backend: Python, FastAPI · Orkestrasyon: LangGraph (supervisor pattern) · Veritabanı: PostgreSQL + pgvector · Frontend: Next.js, Tailwind, shadcn/ui

## Kod Standartları

- **Git commit mesajlarına asla Claude/Opus imzası veya "Generated with Claude Code" gibi ifadeler ekleme.** Bu kurala istisnasız uy.
- Solo geliştirici + monorepo — karmaşık branch/PR akışına gerek yok, `main`'e doğrudan, anlamlı commit mesajlarıyla commit yeterli.
- Yorumlar ve değişken adları Türkçe/İngilizce karışık olabilir — veri şemasındaki Türkçe alan adlarına (`kanit_bekleyen`, `guven_skoru` gibi) sadık kal, tutarlılık önemli.
