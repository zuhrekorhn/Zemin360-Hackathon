# Genç akışı — yeni arayüz metinleri (toplu denetim listesi)

Plan § 0, karar 15: 7. adımdan itibaren yazılan kullanıcıya görünen her metin
burada. Hitap: gence "sen", kuruma "siz". Teknik terim yok ("ajan", "pipeline",
"embedding", "rubrik", "skor eşiği"…). İçerik rehberi gelince
(`docs/icerik-rehberi.md`) bu liste onunla denetlenecek.

Sütunlar: **Dosya** · **Bileşen / yer** · **Metin** · **Kime** (genç / kurum / herkes).

## Denetime not: mevcut ekranlarda düzeltilecekler

Karar 15 gereği şimdi değiştirilmiyor; toplu denetimde ele alınacak.

| Dosya | Yer | Sorun |
|---|---|---|
| `frontend/src/app/kurum/page.tsx` | Boş durum: "Henüz ihtiyaç kartın yok. Tanımlama Ajanı'yla kısa bir sohbet yap…" | Kuruma "sen"; "Ajan" terimi |
| `frontend/src/app/kurum/oneriler/page.tsx` | "Henüz bir ihtiyaç kartın yok. Eşleştirme, Tanımlama Ajanı'yla…" | Kuruma "sen"; "Ajan" terimi |
| `frontend/src/app/tanimlama/page.tsx` | Sayfa geneli | Kuruma "sen"/"siz" karışık olabilir; taranmalı |
| `frontend/src/app/genc/page.tsx` | Boş durum: "…Keşif Ajanı'yla kısa bir sohbet yap…" | "Ajan" terimi |
| `frontend/src/app/kesif/page.tsx` | Başlık ve sohbet adı "Keşif Ajanı" | "Ajan" terimi |
| `frontend/src/app/kart/[id]/page.tsx` | "Doğrulama Ajanı kanıtı dört ayrı başlıkta puanlar…" | "Ajan" terimi |
| `frontend/src/app/isbirligi/[id]/page.tsx` | "Takip Ajanı'nın özeti", "Ajandan plan iste", "Ajandan yeniden öner", "Ajan yeni bir plan önerecek…" | "Ajan" terimi |
| `frontend/src/app/girvak/page.tsx` | "…Canlılık Ajanı'nın son hatırlatmaları…" | "Ajan" terimi (GİRVAK paneli; belki kalabilir) |
| `frontend/src/app/page.tsx` | "Altı problem, altı ajan", "Keşif Ajanı", "Tanımlama Ajanı'yla…" | "Ajan" terimi (tanıtım sayfası; jüri için bilinçli olabilir) |
| `frontend/src/app/kurum/page.tsx` | "· eşleştirmeye hazır değil" | Terim yok ama nedeni söylemiyor; denetimde bakılsın |

## 7. adım — Kart düzenleme

| Dosya | Bileşen / yer | Metin | Kime |
|---|---|---|---|
