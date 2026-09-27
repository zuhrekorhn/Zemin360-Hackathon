# Ajan Özellikleri

Her ajan için üç soru: **ne sağlayacak, ne sağlamayacak (sınırları), nasıl sağlayacak.** Teknik derinlik, jüri kriterlerine göre kalibre edilmiştir — hiçbir ajan atlanmamıştır, ancak karmaşıklık gerektiği kadardır (bkz. `roadmap.md`).

## 1. Keşif Ajanı

**Ne sağlayacak:** Gençle 5-7 sorudan oluşan bir sohbet; sohbeti yapılandırılmış bir yetenek kartına çevirme (rol/alan, somut çıktılar, araçlar, sektör ilgi alanı, müsaitlik). Sektör-nötr şema — yazılımcı da, pazarlamacı da aynı kartı doldurabilir.

**Ne sağlamayacak:** Doğruluk kontrolü yapmaz (Doğrulama Ajanı'nın işi). Otomatik puanlama/sıralama yapmaz (Eşleştirme Ajanı'nın işi). Statik bir CV/PDF üretmez — canlı bir profil.

**Nasıl sağlayacak:**
1. Açık uçlu sorularla başlar, LLM function-calling ile cevabı JSON alanlarına döker.
2. Boş alan kalırsa takip sorusu sorar. **Zorunlu alanlar** (rol, deneyim, sektör ilgisi, araçlar) için sormaya devam eder — en fazla 6 tur, o da yalnızca sonsuz döngüye karşı; tavana gelinirse alanlar "belirtilmedi" ile doldurulur. Sebebi sahada görüldü: 2 turluk sınır dolduğunda kart `sektor_ilgi_alani` boş kaydedilmişti ve o alan embedding metnine girdiği için eşleştirme skorunu doğrudan düşürüyor. **Zorunlu olmayan ayrıntılar** (çıktı başına ölçülebilir sonuç ve kişinin kendi payı) **kendi sayacıyla** en fazla 2 soru; her soru bir kez sorulur, kullanıcı bilmiyorsa ısrar edilmez, sıradaki eksiğe geçilir. Zorunlu alan fazında modelin önerdiği takip sorusu yalnızca konusu eksik bir zorunlu alansa kullanılır (model sorusunu `takip_konusu` ile etiketliyor); değilse o alanın sabit sorusu sorulur. Sebebi sahada görüldü: sektör eksikken model "projede rolün neydi" diye sordu, bir sonraki turda sistemin ek sorusu aynı konuyu tekrar sordu. (Önceden zorunlu alanlarla aynı sayacı paylaşıyordu: zorunlu alanlar 2 tur sürünce hiç sorulmuyordu, "bilmiyorum" diyene de aynı soru tekrar geliyordu.) Tanımlama Ajanı 2 turda kapanmaya devam eder.
3. Kart taslağını kullanıcıya gösterir, **onaylatır** (insan onayı zorunlu).
4. **Edge case — "hiç projem yok":** somut çıktı alanı zorunlu değildir. Fallback soru zinciri ("okulda bir ödev, gönüllü bir iş var mı?") kullanılır; hâlâ yoksa kart `deneyim_seviyesi: "potansiyel"` etiketiyle oluşturulur ve Doğrulama Ajanı'nı atlayarak doğrudan Eşleştirme'ye gider.
5. **Gizlilik:** iletişim bilgisi varsayılan olarak kuruma gösterilmez; kart ve gencin adı görünür, e-posta iki taraf da onaylayınca (kurum ilgilenir, genç kabul eder) açılır (`faz-b-kimlik-ve-dongu.md` § 5).

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

**Ne sağlayacak:** Genç kabul edince açılan iş birliğinin milestone bazlı, iki tarafa da birebir aynı görünen takibi; tamamlanan iş birliğinin gencin kartına **"tamamlanmış pilot"** sinyali olarak geri dönmesi (geri besleme döngüsü).

**Ne sağlamayacak:** Karar vermez: planı onaylamaz, milestone'u işaretlemez, iş birliğini bitirmez; yalnızca plan ve özet **önerir**. Karmaşık bir proje yönetimi aracı değil — yapılandırılmış CRUD, üstüne iki ince LLM çağrısı. Kimseyi değerlendirmez, puanlamaz. Milestone kanıtını puanlamaz (Doğrulama'nın işi değil, kapsam dışı).

**Nasıl sağlayacak** (ayrıntı `faz-c-takip.md`):
1. **Plan önerisi** — genç kabul edince, yanıttan sonra arka planda: ihtiyaç kartının başarı kriterinden 3-5 adım, her biri "ne olunca tamam" tanımı ve hafta cinsinden hedefle (güçlü katman, yapılandırılmış çıktı). Kurala uymayan çıktı bir kez düzeltme notuyla yeniden istenir; yine uymazsa plan boş kalır, taraflar elle ekler ya da yeniden ister.
2. **İki taraflı onay** — taraflar planı düzenler; her düzenleme iki onayı sıfırlar; iki onayla iş birliği `aktif` olur ve plan kilitlenir.
3. **İki taraflı işaretleme** — her adım genç ve kurum ayrı ayrı "tamamlandı" deyince tamamlanır; gecikme okuma anında hesaplanır. Son adımla iş birliği kendiliğinden `tamamlandi` (kural).
4. **Durum özeti** — plan onaylanınca ve adım tamamlanınca, en fazla iki cümle, nötr dil (hızlı katman). **Kesilebilir:** döngü onsuz tam çalışır.
5. **Tamamlanmış pilot** — Eşleştirme'nin doğrulama bonusuna toplamsal girer (en çok +0.125); pilotsuz kartın skoru değişmez, alakayı yaratmaz.

Kurallar iki saf fonksiyonda (`app/agents/takip_durumu.py`), ajan `app/agents/takip.py`, uçlar `app/api/takip.py`. Sohbet ajanı değil; `sohbet_motoru.py`'yi kullanmaz.
