# Ajan Özellikleri

Her ajan için üç soru: **ne sağlayacak, ne sağlamayacak (sınırları), nasıl sağlayacak.** Teknik derinlik, jüri kriterlerine göre kalibre edilmiştir — hiçbir ajan atlanmamıştır, ancak karmaşıklık gerektiği kadardır (bkz. `roadmap.md`).

## 1. Keşif Ajanı

**Ne sağlayacak:** Gençle 5-7 sorudan oluşan bir sohbet; sohbeti yapılandırılmış bir yetenek kartına çevirme (rol/alan, somut çıktılar, araçlar, sektör ilgi alanı, müsaitlik). Sektör-nötr şema — yazılımcı da, pazarlamacı da aynı kartı doldurabilir.

**Ne sağlamayacak:** Doğruluk kontrolü yapmaz (Doğrulama Ajanı'nın işi). Otomatik puanlama/sıralama yapmaz (Eşleştirme Ajanı'nın işi). Statik bir CV/PDF üretmez — canlı bir profil.

**Nasıl sağlayacak:**
1. Açık uçlu sorularla başlar, LLM function-calling ile cevabı JSON alanlarına döker.
2. Boş alan kalırsa en fazla 2 tur takip sorusu sorar.
3. Kart taslağını kullanıcıya gösterir, **onaylatır** (insan onayı zorunlu).
4. **Edge case — "hiç projem yok":** somut çıktı alanı zorunlu değildir. Fallback soru zinciri ("okulda bir ödev, gönüllü bir iş var mı?") kullanılır; hâlâ yoksa kart `deneyim_seviyesi: "potansiyel"` etiketiyle oluşturulur ve Doğrulama Ajanı'nı atlayarak doğrudan Eşleştirme'ye gider.
5. **Gizlilik:** iletişim bilgisi varsayılan olarak kuruma gösterilmez; sadece kart görünür, iki taraf da onaylayınca açılır.

## 2. Tanımlama Ajanı

**Ne sağlayacak:** Kurum temsilcisiyle kısa bir sohbet; dağınık ihtiyacı yapılandırılmış bir ihtiyaç kartına (problem tanımı, başarı kriteri, kısıtlar) çevirme.

**Ne sağlamayacak:** Kurumun stratejik kararını vermez, sadece ifadesini netleştirir. Sektöre özel bir şablon dayatmaz — yapı sektör-nötr, sadece örnek sorular sektöre göre uyarlanır.

**Nasıl sağlayacak:** Keşif Ajanı ile **aynı sohbet motorunu paylaşır** (ayrı yazılmaz), sadece soru seti farklıdır. Sokratik sorularla belirsiz ifadeyi ("dijitalleşmek istiyoruz") ölçülebilir hale getirir ("tier-1 biletlerin %50'sini insan olmadan çöz" gibi). Her alan kurum temsilcisine onaylatılır.

## 3. Eşleştirme Ajanı

**Ne sağlayacak:** İhtiyaç kartı ile yetenek kartını semantik olarak karşılaştırma; her öneri için "neden eşleşti" gerekçesi; doğrulama durumunu sıralamaya dahil etme.

**Ne sağlamayacak:** Kesin işe alım kararı vermez — sadece öneri listesi sunar. Tek bir embedding skoruna göre sıralamaz (yanlış eşleşme riski). Sektöre özel bir taksonomiyle sınırlı kalmaz.

**Nasıl sağlayacak (7 adımlı pipeline):**
1. Taksonomi eşleme (Türkçe ESCO etiketleri) — farklı ifadeleri aynı beceri düğümüne bağlar.
2. Embedding üretimi — kartın tamamı tek bir vektöre dönüştürülür.
3. **Sert filtreler önce çalışır** (embedding'den önce) — şehir, müsaitlik gibi olmazsa-olmazlar.
4. Cosine similarity ile sıralama.
5. Ağırlıklandırma — doğrulama rozeti olanlara küçük bonus.
6. Eşik altı sonuçlar gösterilmez.
7. LLM ile gerekçe metni üretimi (en çok katkı sağlayan taksonomi düğümleri + doğrulama durumu).

**Bilinen sınırlamalar:** Cold start (havuz küçükken kalite düşük — jüriye açıkça belirtilmeli). Taksonomi tek zorunlu filtre değil, embedding serbest metni de temsil eder.

## 4. Doğrulama Ajanı

**Ne sağlayacak:** Her somut çıktı iddiasına dört bileşenli bir güven göstergesi (kanıt orijinalliği, sonuç ölçülebilirliği, rol netliği, üçüncü taraf onayı — her biri 0-3 puan, tek sayıya indirilmez).

**Ne sağlamayacak:** "Bu kişi yalan söylüyor" gibi kesin hüküm vermez — sadece sinyal toplar. Kod/commit geçmişi analiz etmez. Kanıtsız kartı sistemden dışlamaz, sadece "doğrulanmamış" etiketler. Üçüncü taraf onayını zorunlu kılmaz (akışı tıkamamak için).

**Nasıl sağlayacak:**
1. Kanıt kontrolü — link erişilebilirlik + LLM ile tutarlılık karşılaştırması.
2. Referans akışı — tek kullanımlık, girişsiz link; 3-5 soruluk yapılandırılmış form; **5-7 gün timeout, nötr durum** (bkz. `sequence-diagrams.md`).
3. Rubrik puanı — sabit kriterlere göre LLM puanlama + gerekçe metni.
4. **İtiraz hakkı:** kullanıcı skoru görebilmeli, yanlış değerlendirilen kanıtı yeniden gönderebilmeli.
5. **Önyargı riski:** rubrik kriterleri objektif/kontrol edilebilir tutulmalı ("ölçülebilir sonuç var mı — evet/hayır"), "ne kadar etkileyici yazılmış" gibi öznel kriterlerden kaçınılmalı.

## 5. Canlılık Ajanı

**Ne sağlayacak:** Kurulan eşleşmeleri periyodik tarama; pasifleşen bağlantıları fark etme; LLM'in yazdığı kişiselleştirilmiş hatırlatma/öneri mesajı.

**Ne sağlamayacak:** Karmaşık bir davranışsal tahmin modeli kurmaz — kural tabanlı bir eşik (örn. "30 gündür etkileşim yok") yeterli. Toplu/jenerik spam göndermez.

**Nasıl sağlayacak:** Günlük bir arka plan işi, `ESLESME` kayıtlarının `son_aktivite_tarihi`nı tarar, eşik altına düşenler için LLM'e bağlama dayalı bir hatırlatma mesajı yazdırır (`CANLILIK_OLAYI` tablosuna yazılır).

## 6. Takip Ajanı

**Ne sağlayacak:** Eşleşme kabul edilince oluşan iş birliğinin milestone bazlı, iki tarafa da görünür takibi.

**Ne sağlamayacak:** Karmaşık bir proje yönetimi aracı değil — çoğunlukla yapılandırılmış CRUD, üstüne ince bir LLM katmanı (durum özeti üretimi).

**Nasıl sağlayacak:** Eşleşme kabul edilince `ISBIRLIGI` kaydı otomatik oluşur; milestone'lar iki taraflı onay + kanıt ekiyle işaretlenir; LLM periyodik olarak kısa bir durum özeti üretir ("bu iş birliği şu an sağlıklı ilerliyor, X milestone'ı geçti").
