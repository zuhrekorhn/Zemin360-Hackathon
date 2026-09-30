# Ajan Özellikleri

Her ajan için üç soru: **ne sağlayacak, ne sağlamayacak (sınırları), nasıl sağlayacak.** Teknik derinlik, jüri kriterlerine göre kalibre edilmiştir — hiçbir ajan atlanmamıştır, ancak karmaşıklık gerektiği kadardır (bkz. `roadmap.md`).

## 1. Keşif Ajanı

**Ne sağlayacak:** Gençle 5-7 sorudan oluşan bir sohbet; sohbeti yapılandırılmış bir yetenek kartına çevirme (rol/alan, somut çıktılar, araçlar, sektör ilgi alanı, müsaitlik). Sektör-nötr şema — yazılımcı da, pazarlamacı da aynı kartı doldurabilir.

**Ne sağlamayacak:** Doğruluk kontrolü yapmaz (Doğrulama Ajanı'nın işi). Otomatik puanlama/sıralama yapmaz (Eşleştirme Ajanı'nın işi). Statik bir CV/PDF üretmez — canlı bir profil.

**Nasıl sağlayacak:**
1. Açık uçlu sorularla başlar, LLM function-calling ile cevabı JSON alanlarına döker.
2. Boş alan kalırsa takip sorusu sorar. **Zorunlu alanlar** (rol, deneyim, sektör ilgisi, araçlar) için sormaya devam eder — en fazla 6 tur, o da yalnızca sonsuz döngüye karşı; tavana gelinirse alan boş kalır ve genç onu taslak ekranında doldurur (yer tutucu yazılmaz: "belirtilmedi" rolü ve deneyimi karta ve eşleştirme metnine giriyordu). Onay rol, geçerli bir deneyim seviyesi ve en az bir sektör ister (`OnayliKart`); taslak ekranında dört alan da düzenlenebilir. Sebebi sahada görüldü: 2 turluk sınır dolduğunda kart `sektor_ilgi_alani` boş kaydedilmişti ve o alan embedding metnine girdiği için eşleştirme skorunu doğrudan düşürüyor. **Zorunlu olmayan ayrıntılar** (çıktı başına ölçülebilir sonuç ve kişinin kendi payı) **kendi sayacıyla** sorulur (tavan ve sıra madde 6'da); her soru bir kez sorulur, kullanıcı bilmiyorsa ısrar edilmez, sıradaki eksiğe geçilir. Zorunlu alan fazında modelin önerdiği takip sorusu yalnızca konusu eksik bir zorunlu alansa kullanılır (model sorusunu `takip_konusu` ile etiketliyor); değilse o alanın sabit sorusu sorulur. Sebebi sahada görüldü: sektör eksikken model "projede rolün neydi" diye sordu, bir sonraki turda sistemin ek sorusu aynı konuyu tekrar sordu. (Önceden zorunlu alanlarla aynı sayacı paylaşıyordu: zorunlu alanlar 2 tur sürünce hiç sorulmuyordu, "bilmiyorum" diyene de aynı soru tekrar geliyordu.) Tanımlama Ajanı 2 turda kapanmaya devam eder.
3. Kart taslağını kullanıcıya gösterir, **onaylatır** (insan onayı zorunlu).
4. **Edge case — "hiç projem yok":** somut çıktı alanı zorunlu değildir. Fallback soru zinciri ("okulda bir ödev, gönüllü bir iş var mı?") kullanılır; hâlâ yoksa kart `deneyim_seviyesi: "potansiyel"` etiketiyle oluşturulur ve Doğrulama Ajanı'nı atlayarak doğrudan Eşleştirme'ye gider.
5. **Kayıt formundaki bilgiler sorulmaz** (genç akışı, `plans/genc-akisi.md` § 5.3): şehir, çalışma modeli, müsaitlik, durum, okul ve bölüm sohbetin başında ayrı bir sistem mesajıyla bağlam olarak gider. Modelin önerdiği soru yalnızca konusu eksik bir Keşif alanıysa kullanıldığı için form alanı sorulamaz; aradığı fırsat türü de sorulmaz (müsaitlik profilde). Seviye soyut sorulmaz, araçla ne yapıldığı anlattırılır.
6. **Çalışma başına kanıt ve referans:** sonuç ve kişinin payından sonra, kanıtı ya da referansı olmayan her çalışmaya tek soruda "gösteren bir link ya da doğrulayabilecek birinin e-postası" sorulur. Sonuç, pay ve kanıt ilk iki çalışmaya sorulur, sonraki çalışmalara yalnızca kanıt; ek soruların tavanı 8 (kendi sayacıyla, her soru bir kez). Referans e-postası onayda mevcut referans isteği mekanizmasıyla o çalışmaya bağlanır. Çalışma türü (proje, staj, iş, gönüllülük, yarışma), sonuç ve pay ayrı alanlarda saklanır; sertifika ve dil isteğe bağlı.
7. **Kart düzenlenebilir** (`plans/genc-akisi.md` § 6): genç kartını ve çalışmalarını formla düzenler; "Yeni iş ekle" sohbeti ertelendi (plan § 0, karar 16).
8. **Gizlilik:** iletişim bilgisi varsayılan olarak kuruma gösterilmez; kart ve gencin adı görünür, e-posta iki taraf da onaylayınca (kurum ilgilenir, genç kabul eder) açılır (`faz-b-kimlik-ve-dongu.md` § 5).
9. **Firma soru seti** (firma akışı, `plans/firma-akisi.md` § 5): aynı motorla ayrı bir `AjanTanimi` (`app/agents/firma_karti.py`) firmanın "biz ne yapıyoruz" kartını çıkarır. Kayıt formundaki bilgiler (ad, tür, sektör, şehir, tanıtım, web sitesi) bağlam olarak gider, sorulmaz. Zorunlu: ne yaptığı ve yetkinlikler (iki tur); ek sorular önceki işler ve aradığı ortak, her biri bir kez. Yer tutucu yazılmaz, eksik alan onay formunda tamamlanır. Firmaya "siz". Kart firma onaylamadan kaydedilmez, firma başına bir kart.

## 2. Tanımlama Ajanı

**Ne sağlayacak:** Kurum temsilcisiyle kısa bir sohbet; dağınık ihtiyacı yapılandırılmış bir ihtiyaç kartına (problem tanımı, başarı kriteri, kısıtlar) çevirme.

**Ne sağlamayacak:** Kurumun stratejik kararını vermez, sadece ifadesini netleştirir. Sektöre özel bir şablon dayatmaz — yapı sektör-nötr, sadece örnek sorular sektöre göre uyarlanır.

**Nasıl sağlayacak:** Keşif Ajanı ile **aynı sohbet motorunu paylaşır** (ayrı yazılmaz), sadece soru seti farklıdır. Sokratik sorularla belirsiz ifadeyi ("dijitalleşmek istiyoruz") ölçülebilir hale getirir ("tier-1 biletlerin %50'sini insan olmadan çöz" gibi). Her alan kurum temsilcisine onaylatılır.

**İki kapı** (firma akışı, `plans/firma-akisi.md` § 5): aynı motorda ikinci bir `AjanTanimi` (`TANIMLAMA_ORTAK`, `app/agents/tanimlama.py`) iş birliği ortağı arayan ilanı çıkarır. Çalışma modeli ve müsaitlik sorulmaz; iş birliği türü, aranan firma türleri ve varsa şehir şartı alınır. Firmanın kayıt bilgileri bağlam olarak gider, sorulmaz. Ortak tarifi ("bir yapay zekâ girişimi arıyoruz") problem sayılmaz; ortağın çözeceği sorun sorulur. Genç kapısının soru seti değişmedi.

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

**Ne zaman çalışır:** ihtiyaç kartı onaylanınca (o ihtiyaç için) ve yetenek kartı onaylanınca, düzenlenince ya da profildeki filtre alanı değişince (o kartla ilgili açık ihtiyaçlar için; `app/servisler/kart_hazirlama.py`). Sonradan gelen genç böylece mevcut ihtiyaçlarla eşleşir. Pipeline tek: `app/servisler/eslestirme.py`.

**İlgi iki taraflı** (`plans/genc-akisi.md` § 4): eşik üstü öneri gence "fırsat" olarak görünür; ilk ilgiyi firma da genç de gösterebilir, genç ilgi skoru değiştirmez. Karar verilmiş kayıtlar korunur: yeniden hesap yalnızca `onerildi` kayıtlarını siler; gencin ilgi gösterdiği kaydın skoru ve gerekçesi de değişmez (karar 14). Kapalı ihtiyaç için aday aranmaz.

**Bilinen sınırlamalar:** Cold start (havuz küçükken kalite düşük — jüriye açıkça belirtilmeli). Taksonomi tek zorunlu filtre değil, embedding serbest metni de temsil eder.

## 4. Doğrulama Ajanı

**Ne sağlayacak:** Her somut çıktı iddiasına dört bileşenli bir güven göstergesi (kanıt orijinalliği, sonuç ölçülebilirliği, rol netliği, üçüncü taraf onayı — her biri 0-3 puan, tek sayıya indirilmez).

**Ne sağlamayacak:** "Bu kişi yalan söylüyor" gibi kesin hüküm vermez — sadece sinyal toplar. Kod/commit geçmişi analiz etmez. Kanıtsız kartı sistemden dışlamaz, sadece "doğrulanmamış" etiketler. Üçüncü taraf onayını zorunlu kılmaz (akışı tıkamamak için).

**Nasıl sağlayacak:**
1. Kanıt kontrolü — **linkin yalnızca açılıp açılmadığına ve sayfanın başlığı ile kısa açıklamasına** bakılır (`<head>` içindeki `<title>`/`og:title` ve `meta description`/`og:description`, en çok 400 karakter). Sayfanın içeriği, reponun dili, README'si, dosyaları ya da commit geçmişi **okunmaz**. Dil modeli, iddiayı (başlık, açıklama, sonuç, pay) bu başlık ve açıklamayla karşılaştırarak üç bileşeni puanlar; link açılmıyorsa kanıt bileşeni kuralla 0'dır. Referans bileşeni dil modelinden değil, referansların 1-5 puanlarının ortalamasından kuralla hesaplanır. **SSRF engeli:** istek `app/core/guvenli_istek.py` üzerinden atılır: yalnızca `http`/`https` ve 80/443; alan adının çözüldüğü bütün IP'ler genel internette olmalı (yerel makine, özel ağ, link-local ve bulut kimlik servisi `169.254.169.254` dahil iç adresler ret); yönlendirmeler otomatik izlenmez, her adım (en çok 5) yeniden denetlenir; bağlantı denetlenen IP'ye kurulur (DNS yeniden bağlama kapalı), `Host` ve TLS sunucu adı özgün alan adıdır. Kurala uymayan link "açılmıyor" sayılır, istek hiç atılmaz.
2. Referans akışı — tek kullanımlık, girişsiz link; 3-5 soruluk yapılandırılmış form; **5-7 gün timeout, nötr durum** (bkz. `sequence-diagrams.md`).
3. Rubrik puanı — sabit kriterlere göre LLM puanlama + gerekçe metni.
4. **İtiraz hakkı:** kullanıcı skoru görebilmeli, yanlış değerlendirilen kanıtı yeniden gönderebilmeli.
5. **Önyargı riski:** rubrik kriterleri objektif/kontrol edilebilir tutulmalı ("ölçülebilir sonuç var mı — evet/hayır"), "ne kadar etkileyici yazılmış" gibi öznel kriterlerden kaçınılmalı.
6. **Otomatik puanlama** (genç akışı): linki olan çalışma, kart onaylanınca ve düzenlenince arka planda puanlanır; linksiz çalışma puanlanmaz, "doğrulanmamış" nötr durumda kalır.
7. **Düzenleme sıfırlar:** bir çalışmanın içeriği ya da linki değişirse o çalışmanın göstergesi sıfırlanır ve yeniden değerlendirilir; değişmeyenlerinki korunur. Değişiklikten önceki referans yanıtları silinmez, geçmiş olarak görünür ama puana girmez; genç referansı yeniden isteyebilir (`plans/genc-akisi.md` § 0, karar 8).

## 5. Canlılık Ajanı

**Ne sağlayacak:** Kurulan eşleşmeleri periyodik tarama; pasifleşen bağlantıları fark etme; LLM'in yazdığı kişiselleştirilmiş hatırlatma/öneri mesajı.

**Ne sağlamayacak:** Karmaşık bir davranışsal tahmin modeli kurmaz — kural tabanlı bir eşik (örn. "30 gündür etkileşim yok") yeterli. Toplu/jenerik spam göndermez.

**Genç akışı eki:** genç ilgi gösterdi ve firma 5 gündür yanıt vermediyse firmaya tek hatırlatma (`genc_ilgisi_yanitsiz`, yalnızca şablon, "siz" hitabı).

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

**Firma–firma iş birliği** (firma akışı, `plans/firma-akisi.md` § 9): aynı kurallar ve aynı ekran; ortak firma takipte aday tarafıdır (onay ve işaret alanları `genc_*`, karar 12). Plan önerisinin istemi ayrı (`SISTEM_TALIMATI_FIRMA`, `firma_plan_oner`): iki firmanın ekipleri, ilanın iş birliği türü ve ortak firmanın kartı; genç istemi değişmedi. Durum özetinde taraf "ortak firma" diye anılır. Tamamlanan iş birliği aday firmanın eşleştirme bonusuna girer.
