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
| Faz planı ve mevcut durum | `docs/roadmap.md` |

**Kural:** Bu dosyalarda yazan bir tasarım kararıyla çelişen bir yaklaşım önereceksen (örn. farklı bir kütüphane, farklı bir veri modeli), önce sor — sessizce değiştirme. Sebebi belgelenmiş kararlar var, gerekçesiz sapma kafa karışıklığı yaratır.

## Şu An Neredeyiz

Faz 0 (mimari + tasarım) tamamlandı. Faz 1'deyiz: backend iskeleti, frontend iskeleti, Keşif + Tanımlama ajanının ilk çalışan versiyonu. Detaylı takvim: `docs/roadmap.md`.

## Teknoloji Yığını (hızlı referans)

Backend: Python, FastAPI · Orkestrasyon: LangGraph (supervisor pattern) · Veritabanı: PostgreSQL + pgvector · Frontend: Next.js, Tailwind, shadcn/ui

## Kod Standartları

- **Git commit mesajlarına asla Claude/Opus imzası veya "Generated with Claude Code" gibi ifadeler ekleme.** Bu kurala istisnasız uy.
- Solo geliştirici + monorepo — karmaşık branch/PR akışına gerek yok, `main`'e doğrudan, anlamlı commit mesajlarıyla commit yeterli.
- Yorumlar ve değişken adları Türkçe/İngilizce karışık olabilir — veri şemasındaki Türkçe alan adlarına (`kanit_bekleyen`, `guven_skoru` gibi) sadık kal, tutarlılık önemli.
