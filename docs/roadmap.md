# Yol Haritası

> **Durum (10 Eki 2026):** altı ajan, üç rol ve iki kapılı eşleşme döngüsü çalışıyor; kod, belgeler
> ve testler birbiriyle tutarlı, repo GitHub'da ve CI yeşil. Hackathon 9–11 Ekim (Kolektif House
> Levent): kod ve repo 10 Ekim'de jüriye gitti, sunum 11 Ekim'de (5 dakika demo + 3 dakika soru).
> Demo yerelde yapılır; canlıya alma hackathon kapsamında yok. Kalan işler yalnızca sunuma hazırlık.

## "Tam" ne demek

Her iş aşağıdaki dört testten en az birini geçirmeye yaramalı. Yaramıyorsa takvime girmez.

1. **Döngü kapalı.** Genç kart oluşturur → kanıt ekler → firma ihtiyaç tanımlar → öneri görür →
   ilgilenir → karşılıklı ilgi → iletişim açılır → iş birliği adımlarla ilerler → tamamlanır →
   tamamlanma sisteme sinyal olarak geri döner.
2. **Herkes kendi kapısından girer.** Üç rol (genç, firma, GİRVAK), her birinin kendi paneli.
3. **Kurulabilir ve doğrulanabilir.** Jüri repoyu README'yle kurabilir; testler ve CI yeşil.
4. **Çıkmaz sokak yok.** Hiçbir ekran "sonra gelecek" demez.

## Tamamlananlar

| Alan | Ne yapıldı | Ayrıntı |
|---|---|---|
| Sağlamlaştırma | Gemini ücretli katman, iki model katmanı ve yedek zincir, hata sözleşmesi | `architecture.md` § LLM katmanları |
| Kimlik ve iki taraflı döngü | JWT, üç rol, paneller, karşılıklı onay, bildirimler | `kimlik-ve-dongu.md` |
| Takip | Süreç şablonları, iki taraflı onay ve işaret, erken sonlanma, tamamlanma sinyali | `takip.md`, `kararlar.md` T1-T3 |
| Canlılık + GİRVAK paneli | Kontrol, hatırlatma, yeni fırsat; GİRVAK paneli brifteki altı ihtiyaç alanına göre (Özet, Kararlar, İş birlikleri, Takılan süreçler, Sayılar) | `canlilik.md` |
| Genç akışı | Kayıt formu, tek kart, otomatik değerlendirme, gençten ilgi | `kararlar.md` G1-G17 |
| Firma akışı | Firma kaydı ve profili, firma kartı, iki kapı, firma–firma eşleşme, firma doğrulaması | `kararlar.md` F1-F20 |
| Doğrulama | Link / dosya / görsel okuma, hesap bağlama, referans, kötüye kullanım işaretleri, gözlem, ölçüm (Kanıt %56 → %96) | `dogrulama.md` |
| Tanımlama | Başarı ölçütü, ilan düzenleme, koşul sorusu, istem güvenliği | `kararlar.md` D1, S1-S5 |
| Eşleştirme | Skor eşiği kaldırıldı, ölçülmüş alt sınırlar (0.48 / 0.52), uygunluk kararı | `matching-algorithm.md` § 5, § 8 |
| Güvenlik | SSRF engeli, sahiplik üçlüsü (401 / 403 / 404), istem enjeksiyonuna karşı veri etiketleri; 8 Eki incelemesi: kart onayı ve sohbet girdi sınırları, referans bekleme süresi ve kalem başına sınır, ad tek satır, kanıt metni etiketi süzülür, bildirim tekrarı, Keşif sohbeti geri yükleme | `agent-specs.md` § 4, `kimlik-ve-dongu.md` § 3 |
| Arayüz (8 Eki) | Genç tarafı yeniden: Fırsatlar, Kartım, Hesabım, İş birliklerim, Keşif; Güçlendir paneli, kartın durumu sayımla, birincil düğme koyu yeşil | `kararlar.md` G9, G18, `design-language.md` |
| Arayüz (9 Eki) | Firma tarafı gencin diliyle, 1. tur: Panelim iki sütun, ihtiyaç kartı ve "⋯" menüsü, aday listesi ve kartları `KUTU` yüzeyinde, uyum kelimeyle, menüde tek etkin sayfa. 2. tur: ihtiyaç düzenleme yan panelde, ihtiyaç ve firma kartı sohbetleri canlı önizlemeli, firma kartı ve profili Hesabım kalıbında; iş birliği ve GİRVAK yüzeyleri `KUTU`ya çekildi | `kararlar.md` F21 |
| GİRVAK paneli (10 Eki) | Menü brifteki altı ihtiyaç alanına göre: Özet (`GET /girvak/ozet`), Karar bekleyenler + geçmiş kararlar, İş birlikleri (`GET /girvak/isbirlikleri`, e-postasız), Takılan süreçler, Sayılar; uydurma program hedefleri kaldırıldı; sistem durumu hesap menüsünde | `canlilik.md` § 7–9, `api-contracts.md` |
| Demo verisi (10 Eki) | `demo_hesaplari.py` + `demo_zenginlestir.py` kendi kendine yeter: Soğuk Lojistik hesabı betikte açılır, üç iş birliği (tamamlanan genç–firma ve firma–firma, gecikmiş adımlı süren), ölçülebilir hedefli ilanlar, bonus sahnesi (Selin 0,72 > Burak 0,65); betik testi | `demo-test-rehberi.md` § 9 |
| Metin denetimi | Hitap, sayfa içi onaylar, LLM istem dili | `icerik-rehberi.md` § 10 |
| E-posta | Brevo / Resend gönderici, "eşleştiniz" e-postası, "E-posta yaz" | `architecture.md` |
| Toparlama (7–10 Eki) | Katman düzeltmeleri, belgeler koda göre yeniden, karar kaydı, CI, katkı rehberi; plan belgeleri ve yayına alma kalıntıları silindi; README'ye teknoloji seçimleri ve model katmanı gerekçesi | `architecture.md`, `kararlar.md`, `CONTRIBUTING.md` |

## Kalan işler

**Sunuma kadar (11 Eki):**

- [ ] Sunum ve konuşma metnini gözden geçirmek; demo akışını yerelde en az iki kez prova etmek
      (her provadan önce `yerel_sifirla.py` + `demo_hesaplari` + `demo_zenginlestir`).
- [ ] Yedek demo videosu (LLM gecikmesine karşı); çekilince README'ye bağlantı.
- [ ] Sunumu PDF ya da PPTX olarak dışa aktarıp yedeklemek.
- [ ] Elle deneme: Takip'te "Süreci sonlandır", e-postada Brevo ile gerçek gönderim.

**Açık kararlar:**

- [ ] Kart bonusunun kart düzeyi formülü (`matching-algorithm.md` § 4.1, iki seçenek).
- [ ] Güçlü katmanda Pro'ya geçilip geçilmeyeceği (aynı girdiyle karşılaştırma; model `.env`'den).

**Hackathon sonrası (bilinen borç):**

- [ ] `api/canlilik.py` ve `api/takip.py`'deki orkestrasyon `app/servisler/`'e.
- [ ] `agents/eslestirme.py`: aday sorguları servise; genç ve firma adayı ikiz fonksiyonları tek
      bir aday türü stratejisinde.
- [ ] `hesap_id` NOT NULL migration'ı ve hesapsız profil dallarının kaldırılması.
- [ ] `genc_*` kolonlarının "aday" adıyla yeniden adlandırılması (`kararlar.md` F12).
- [ ] **İstek hız sınırı** (8 Eki incelemesi): hiçbir uçta yok; Keşif sohbeti, `/auth/giris`,
      doğrulama ve embedding uçları hesap ve IP başına sınırlanmalı (maliyet, kaba kuvvet). Ürünleşmeden önce şart.
- [ ] Referans istemeyi e-postası doğrulanmış hesaba bağlamak (demo hesapları doğrulanmamış; prova sonrası).
- [ ] Aynı gencin farklı çalışmalarında aynı kanıt adresi (`github.com/kullanici` gibi profil kökü):
      tekrar işareti ve profil kökü için puan tavanı (`dogrulama.md`).
- [ ] İlan düzenlenince karar verilmiş kayıtlarda adaya yazılan metin (`aday_gerekce_metni`) yeniden üretilmiyor.
- [ ] Liste uçlarında N+1 sorgu (`api/eslestirme.py` › `ihtiyac_karti_yaniti`, `kart_yaniti`).
- [ ] Referans token'ı veritabanında açık metin (e-posta doğrulama token'ı özetli); JWT 7 gün ve geri alınamaz;
      dosya yüklemede gövde sınırı uvicorn düzeyinde yok.
- [ ] Frontend: `lib/api.ts` alana göre bölünür, türler OpenAPI'den üretilir; "yükleniyor / hata"
      kalıbı ortak bir hook'a; büyük sayfalar (`isbirligi`, `kurum/oneriler`, `kanit.tsx`) bölünür.
- [ ] Canlılık'ın firma–firma eşleşmelerini taraması (`kararlar.md` F18).
- [ ] "Yeni iş ekle" sohbeti (`kararlar.md` G16).
- [ ] Doğrulama değerlendirme setini 45'ten 120 vakaya çıkarmak; alanlar arası adalet.
- [ ] **Terim tutarlılığı: "pilot uygulama".** Hackathon brifi (GİRVAK) "pilot uygulama" ve "iş birliği ve pilot
süreçleri" diyor; firma kartında "Pilot uygulama" yazıyor ama firma–firma iş birliği planında "Deneme işi"
(`takip_surecleri.py`, `takip.py` istemleri, `icerik-rehberi.md` § 4, `kararlar.md` T1). Tek terime çekmek
istemlerdeki "pilot yazma" kuralını ve onu koruyan testleri de değiştirir; jüri sonrası.
- [ ] GİRVAK paneli: zaman serisi grafikleri (rapor şimdilik tarayıcıdan yazdırılır).
- [ ] Ürünleşme: canlıya alma, zamanlanmış tarama, KVKK metninin kesinleşmesi.

## Kapsam dışı

Mobil uygulama, taraflar arası mesajlaşma, bildirimlerin e-postayla gönderilmesi (yalnızca kayıt
doğrulaması, referans isteği ve "eşleştiniz" e-postası gider), ESCO taksonomisi, çoklu dil, refresh
token, OAuth ile giriş (OAuth yalnızca hesap bağlamada), httpOnly cookie, hackathonda canlıya alma.

## Çalışma kuralları

`CONTRIBUTING.md`: her iş önce kısa bir not ya da planla başlar; her değişiklik ayrı commit ve
testle girer; iş bitince ilgili belge ve bu dosya güncellenir.
