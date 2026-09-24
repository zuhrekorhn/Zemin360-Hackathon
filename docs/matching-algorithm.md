# Eşleştirme Algoritması

Bu doküman, `agent-specs.md`'deki 7 adımlı pipeline'ın uygulama düzeyinde detayıdır. Kapsam iki katmana ayrılmıştır: **MVP çekirdek** (Faz 2'de yazılacak, ESCO taksonomisi olmadan çalışır) ve **isteğe bağlı geliştirme** (zaman kalırsa eklenir). Bu ayrım bilinçli — projenin en riskli parçasını önce en sade haliyle çalışır kılmak, sonra zenginleştirmek.

```mermaid
flowchart TD
  A[Kartları oku] --> B[Sert filtreler - SQL WHERE]
  B --> C[Embedding benzerliği - pgvector]
  C --> D[Ağırlıklı skor hesapla]
  D --> E[Eşik / Top-N filtre]
  E --> F[LLM gerekçe üretimi]
```

## 1. Temsil Metni (embedding'e hazırlama)

Her kart, embedding'e verilmeden önce tek bir düz metne dönüştürülür.

**Yetenek kartı şablonu:**
```
Rol: {rol_alani}
Deneyim: {deneyim_seviyesi}
Sektör ilgisi: {sektor_ilgi_alani}
Araçlar: {araclar_teknolojiler}
Öne çıkan çıktılar: {somut_ciktilar[].baslik ve aciklama, birleştirilmiş}
```

**İhtiyaç kartı şablonu:**
```
Problem: {problem_tanimi}
Başarı kriteri: {basari_kriteri}
```

## 2. Embedding Üretimi

- Temsil metni, Voyage AI'nin `voyage-4` modeline gönderilir (1024 boyut) — Anthropic'in Claude ile kullanım için resmi önerdiği sağlayıcı, ilk 200M token ücretsiz.
- Sonuç vektör, kartın `embedding` kolonuna yazılır (pgvector).
- **Ne zaman yeniden hesaplanır:** kart onaylandığında (ilk oluşturma) ve her güncellemede (`versiyon` arttığında).

## 3. Sert Filtreler (embedding'den ÖNCE çalışır)

```sql
SELECT yk.* FROM yetenek_karti yk
JOIN kullanici k ON k.id = yk.kullanici_id
WHERE (ih.musaitlik_tercihi IS NULL OR k.musaitlik = ih.musaitlik_tercihi)
  AND (ih.sehir_tercihi IS NULL OR k.sehir = ih.sehir_tercihi)
```

Bu adım havuzu daralttıktan sonra benzerlik hesabı sadece bu alt kümede çalışır — hem doğru hem performanslı.

## 4. Skor Formülü (MVP — ESCO'suz)

```
skor = 0.75 * cosine_similarity(yetenek.embedding, ihtiyac.embedding)
     + 0.25 * dogrulama_bonus
```

`dogrulama_bonus` hesabı:
- `GUVEN_SKORU` kaydı varsa: `(kanit_orijinalligi + sonuc_olculebilirligi + rol_netligi + ucuncu_taraf_onayi) / 12` (0-1 arası normalize)
- Kayıt yoksa (henüz doğrulanmamış): `0` — **ceza değil**, sadece bonus yok. Doğrulanmamış kart elenmez, listede kalır.

## 5. Eşik ve Sıralama

Mutlak bir eşik yerine (havuz küçükken saçmalar) **Top-N** yaklaşımı: en yüksek skorlu **5 sonuç** gösterilir. Ek güvenlik: skor %40'ın altındaysa hiç gösterilmez (tamamen alakasız sonuçları filtrelemek için).

### Benzerlik alt sınırı: 0.45 (skordan önce uygulanır)

Skor eşiği tek başına yetmiyor. Formül gereği tam doğrulanmış bir kart, benzerliği sıfır olsa bile `0.25 × 1.0 = 0.25` taşıyor; 0.34 benzerlikli alakasız bir aday `0.75 × 0.34 + 0.25 × 0.75 ≈ 0.44` ile %40 eşiğini geçiyordu. Sonuç: konuyla ilgisi olmayan bir kart öneri listesine giriyor, üstüne LLM ona bir gerekçe yazmaya çalışıyordu.

**Kural:** doğrulama bonusu **alakalı adaylar arasında sıralamayı** etkiler; alakasız bir adayı alakalı yapmaz. Bu yüzden `benzerlik < 0.45` olan adaylar **skor hesaplanmadan** elenir (`BENZERLIK_ALT_SINIRI`, `app/agents/eslestirme.py`). İki sınır farklı şeyleri ölçüyor ve biri diğerinin yerine geçmiyor: 0.45 "bu aday konuyla ilgili mi", %40 "ilgili adaylar arasında gösterilmeye değer mi".

Değer mevcut kartların ham benzerlikleriyle kalibre edildi (Voyage `voyage-4`, Türkçe metin):

| Çift | Benzerlik |
|---|---|
| Destek bileti ihtiyacı ↔ bilet sınıflandırma botu (gerçekten alakalı) | 0.662 |
| Aynı ihtiyaç ↔ kütüphane takip sistemi | 0.340 / 0.336 |
| Aynı ihtiyaç ↔ veri analisti kartı | 0.342 |
| Zeytin budama takibi ↔ tüm kartlar (kasten alakasız) | 0.275 – 0.354 |

Alakasız küme 0.27–0.36 bandında toplanıyor, gerçek eşleşme 0.66'da duruyor. 0.45, gürültü bandının ~0.09 üstünde ve gerçek eşleşmenin ~0.21 altında — iki tarafa da pay bırakıyor. Kısmen alakalı adaylar (aynı beceri, farklı alan) bu bandın neresine düşer, havuz büyüyünce yeniden bakılmalı; dört kartlık bir örneklemle kalibre edildiğini unutma.

Alt sınır ayrıca SQL sorgusunda da uygulanıyor (havuz Python'a taşınmadan daralsın diye), ama kuralın tek doğruluk kaynağı `siralayip_ele`.

**Cold start:** havuzda az kart varken bu doğal bir sınırlama — arayüzde gizlenmez, açıkça belirtilir: *"Şu an sınırlı sayıda eşleşme var."*

## 6. Gerekçe Üretimi (LLM)

LLM'e verilenler: ihtiyaç kartı özeti, yetenek kartı özeti, doğrulama durumu. İstenen çıktı: 2-3 cümlelik, somut noktalara referans veren bir gerekçe — genel geçer ifadeler değil ("iyi bir aday" gibi), kartlardaki gerçek alanlara atıf yapan cümleler.

## İsteğe Bağlı Geliştirme — ESCO Taksonomi Eşleme

Zaman kalırsa (Faz 3 veya sonrası), skor formülüne bir bileşen daha eklenir:

```
skor = 0.55 * cosine_similarity
     + 0.20 * esco_orani
     + 0.25 * dogrulama_bonus
```

`esco_orani`: kartların serbest metnindeki beceri ifadelerinin, ESCO'nun Türkçe beceri listesiyle embedding benzerliği üzerinden eşlenen oranı (LLM çağrısı gerektirmeyen, daha ucuz bir yöntem — kart metni değil, tekil beceri ifadeleri ESCO terimleriyle karşılaştırılır).

**Bu adım MVP'yi bloklamaz** — cosine similarity zaten kartın tamamındaki serbest metni temsil ettiği için, ESCO olmadan da anlamlı eşleşmeler üretir.
