# Yol Haritası

## Takvim

| Faz | Tarih | Odak |
|---|---|---|
| **Faz 0** | 19-21 Eylül | Mimari, veri şeması, sequence diyagramları, API sözleşmeleri, repo iskeleti — **tamamlandı** |
| **Faz 1** | 22-28 Eylül | Çekirdek altyapı, Keşif + Tanımlama ajanı (paylaşılan motor), frontend iskeleti |
| **Faz 2** | 29 Eylül - 3 Ekim | Eşleştirme ajanı (embedding + gerekçe), Doğrulama ajanı (rubrik), entegrasyon |
| **Faz 3** | 4-6 Ekim | Canlılık + Takip ajanları, UI/UX cilası, uçtan uca test |
| **Tampon** | 7-8 Ekim | Hata düzeltme, prova — 8'i geçmeyecek şekilde |
| **Hackathon** | 9-11 Ekim | Sadece sunum + son rötuş |

## Jüri Kriteri Eşlemesi (100 puan, eşit ağırlıklı %20)

| Kriter | Bu projede karşılığı |
|---|---|
| Problem–Çözüm Uyumu | 6 problemin hepsi ele alınıyor, tek bir paylaşılan veri katmanı üzerinden |
| Teknik Yetkinlik & Kod Kalitesi | Mimari kararların gerekçeli seçilmesi, temiz repo yapısı, açık kaynak standartları |
| Yapay Zeka Entegrasyonu | 6 ajan, LangGraph supervisor pattern, katmanlı model stratejisi |
| Kullanıcı Deneyimi (UI/UX) | Next.js + Tailwind + shadcn/ui, sade akışlar |
| Çalışan Demo & Tamamlanmışlık | **Kapsam disiplini** — az ama tam çalışan özellik, hiçbir ajan yarım bırakılmıyor |

**Stratejik ilke:** 5 kriter eşit ağırlıklı olduğu için "ne kadar çok özellik" değil "ne kadar sağlam ve bitmiş" belirleyici. Bu yüzden 6 ajanın hepsi gerçek ve çalışır, ancak teknik derinlik jüri kriterine göre kalibre edilmiş (bkz. `agent-specs.md`).

## Farklılaşma Noktaları

Rakip takımların muhtemelen atlayacağı üç nokta:

1. **"Neden eşleşti" açıklaması** — kara kutu skor yerine gerekçeli öneri.
2. **Kapalı döngü** — Doğrulama → Eşleştirme → Takip → tamamlanan iş birliği yeni bir referans sinyaline dönüşüyor; "canlı ağ" vizyonu gerçekten çalışıyor.
3. **Sektör-bağımsız taksonomi** — çoğu takım örtük olarak sadece teknik profilleri düşünecek; bu platform reklamcıdan üretim çalışanına kadar herkesi kapsıyor.
