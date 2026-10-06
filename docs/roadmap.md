# Yol Haritası — "Tam Uygulama" Sürümü

> Bu belge önceki faz planının yerini alır. Organizatörler kısa bir MVP değil,
> eksiksiz çalışan bir uygulama beklediklerini söyledi. Hedef çizgi buna göre
> yeniden çizildi.
>
> **Teknik iş 5 Ekim'de biter.** 6-7 Ekim tampon, 8 Ekim boş, 9-11 Ekim yalnızca
> sunum. Bu tarihten sonra yeni özellik girmez.

## "Tam" ne demek

Her iş aşağıdaki dört testten en az birini geçirmeye yaramalı. Yaramıyorsa bu
takvime girmez.

1. **Döngü kapalı.** Genç kart oluşturur → kanıt ekler → kurum ihtiyaç tanımlar
   → öneri görür → ilgilenir → genç kabul eder → iletişim açılır → iş birliği
   milestone'larla ilerler → tamamlanır → tamamlanma sisteme sinyal olarak
   geri döner.
2. **Herkes kendi kapısından girer.** Üç rol (genç, kurum, GİRVAK), her birinin
   kendi paneli.
3. **Canlı adreste.** Jüri localhost görmez.
4. **Çıkmaz sokak yok.** Hiçbir ekran "Faz 3'te gelecek" demez.

## Takvim

| Tarih | Faz | Çıktı |
|---|---|---|
| 25-26 Eyl | A — Sağlamlaştırma ✓ | İnceleme bulguları kapandı, Gemini ücretli anahtara geçildi |
| 26-27 Eyl | B — Kimlik ve iki taraflı döngü ✓ | JWT, üç rol, paneller, karşılıklı onay, bildirimler |
| 27 Eyl | C — Takip Ajanı ✓ | Milestone planı, ilerleme, tamamlanma sinyali |
| 1-2 Eki | D — Canlılık Ajanı + GİRVAK paneli | Tarama, hatırlatma, fırsat, KPI'lar |
| 3 Eki | Gözden geçirme ve düzeltme | Profil alanları, profil düzenleme sayfası, arayüz düzeltmeleri |
| 3 Eki akşam | **Özellik dondurma** | Bundan sonra yalnızca hata düzeltme |
| 4 Eki | E — Yayına alma + tohum veri | Canlı adres, gerçekçi havuz |
| 5 Eki | F — Uçtan uca prova | Demo senaryosu, belgeler, yedek video |

## Faz A — Sağlamlaştırma (25-26 Eyl)

İnceleme bulguları, önem sırasıyla:

- [x] `eslesme (ihtiyac_karti_id, yetenek_karti_id)` UNIQUE kısıtı; pipeline
      çakışmada `ON CONFLICT` ile dayanıklı. Arka plan işi ile `GET /oneriler`
      aynı anda çalışınca mükerrer satır ve çift LLM çağrısı olmamalı.
- [x] Onay tekrarlanabilir: aynı `oturum_id` ikinci kez onaylanınca yeni kart
      açılmaz, mevcut kart döner. Embedding hatası yakalanır, kart yine döner;
      embedding'i yeniden hesaplatan bir yol eklenir.
- [x] Referans gizliliği: girişsiz uç noktalar başka referansların e-postasını,
      puanını ve token'ını dönmez. (Faz B'deki yetkilendirme ile tamamen kapanır.)
- [x] `musaitlik_tercihi` `Literal` olur, onayda doğrulanır, formda düzeltilebilir.
- [x] 429 mesajı düzeltilir ("kota doldu", "yoğunluk" değil); üç kopya tek
      fonksiyonda (`lib/hata.ts`) toplanır.
- [x] Ek takip soruları ayrı sayaç kullanır; "bilmiyorum" cevabında aynı soru
      tekrarlanmaz.
- [x] Tüm çıktılar silinirse kart gerçekten "potansiyel" kaydedilir.
- [x] `email` ve `iletisim_email` UNIQUE; kayıtlı kullanıcı bilgisi güncellenebilir.

**LLM geçişi:** Sağlayıcı değişmez, Gemini'de kalınır; yalnızca ücretsiz
katmandan ücretli API anahtarına geçilir. Katmanlı model stratejisi korunur:
çıkarım işleri ucuz model, gerekçe ve rubrik güçlü model. Yedek model zinciri
Gemini içinde çalışmaya devam eder. Her çağrının token kullanımı log'a yazılır.

- [x] Yapıldı: iki katman (`GEMINI_HIZLI_*`, `GEMINI_GUCLU_*`, `.env`'den), yedek
      model arıza/zaman aşımı/hız sınırı/404 için, 30 sn zaman aşımı, token log'u,
      açılışta model adı kontrolü. Güçlü katman varsayılanı **geçici olarak**
      `gemini-3.8-flash` (yeni anahtarlara kararlı Pro açık değil); Pro'ya geçilip
      geçilmeyeceği karşılaştırma raporundan sonra kararlaştırılacak.

**Kabul:** Tüm testler geçer; her bulgu için en az bir yeni test var.

## Faz B — Kimlik ve iki taraflı döngü (26-27 Eyl) ✓

Özellik notu ve kararlar: [`faz-b-kimlik-ve-dongu.md`](faz-b-kimlik-ve-dongu.md).

**Kimlik kararı:** E-posta + şifre, JWT. Karmaşıklık bilinçli olarak düşük tutulur.

- Şifreler argon2 (ya da bcrypt) ile hash'lenir.
- JWT **localStorage**'da tutulur ve her istekte
  `Authorization: Bearer <token>` başlığıyla gönderilir.
- Tek access token, 7 gün ömür. Refresh token bu sürümde yok.
- Token'da `sub` (kullanıcı id) ve `rol` (`genc` | `kurum` | `girvak`).
- Rol yetmez, **sahiplik** kontrol edilir: genç yalnızca kendi kartını, kurum
  yalnızca kendi ihtiyaç kartını ve önerilerini görür/değiştirir.
- Referans yanıt sayfası girişsiz kalır (token bazlı, önceki karar).

**Döngü:**

- [x] Kayıt ve giriş sayfaları; rol seçimi kayıtta.
- [x] `Kullanici` / `Kurum` kayıtları hesaba bağlanır; onaydaki "e-postayla bul
      veya oluştur" mantığı kaldırılır.
- [x] Genç paneli: kartım, kanıtlarım, bana gelen ilgiler, iş birliklerim.
- [x] Kurum paneli: ihtiyaç kartlarım, önerilerim, iş birliklerim.
- [x] Karşılıklı onay: kurum "ilgileniyorum" der → eşleşme `ilgileniliyor` →
      genç kabul eder → `kabul_edildi` + iş birliği açılır → **iletişim bilgisi
      ancak şimdi iki tarafa görünür**. Genç reddederse `reddedildi`.
- [x] Uygulama içi bildirimler (tablo + panelde sayaç). Gerçek e-posta yok.

**Kabul:** İki ayrı tarayıcıda genç ve kurum olarak döngü, iletişim açılmasına
kadar çıkmaz sokak olmadan yürür. ✓ Tarayıcıda doğrulandı (27 Eyl), demo
hesaplarıyla (`scripts/yerel_sifirla.py` + `scripts/demo_hesaplari.py`).

**Not:** Sayfa `localhost` yerine makinenin ağ adresinden (ör. `192.168.x.x:3000`)
açılırsa Next.js 16 geliştirme dosyalarını engeller ve backend CORS'u isteği
reddeder; sayfa görünür ama düğmeler çalışmaz. Yerel denemede `http://localhost:3000`.

## Faz C — Takip Ajanı (27 Eyl) ✓

Özellik notu ve kararlar: [`faz-c-takip.md`](faz-c-takip.md). Durum özeti
(Kesim çizgisi (3)) kesilebilir; döngü onsuz tam çalışır.

- [x] İş birliği açılınca ajan ihtiyaç kartının başarı kriterinden 3-5
      milestone'luk plan önerir (LLM, yapılandırılmış çıktı).
- [x] İki taraf planı onaylar ya da düzenler.
- [x] Her milestone iki tarafça işaretlenir; iki taraf da aynı zaman çizelgesini görür.
- [x] Ajan kısa durum özeti yazar; tarihi geçen milestone'u işaretler.
- [x] İş birliği tamamlanınca gencin kartına "tamamlanmış pilot" sinyali yazılır
      ve Eşleştirme'nin doğrulama bonusuna girer. **Geri besleme döngüsü burada kapanır.**

**Sınır:** Ajan karar vermez, milestone'u kendisi kapatmaz; öneri ve özet üretir.

**Kabul:** ✓ Tarayıcıda iki pencereyle doğrulandı (27 Eyl): plan önerisi, düzenleme ve iki taraflı onay, gecikme etiketi, iki taraflı işaretleme, otomatik tamamlanma; pilot rozeti kartta görünüyor, yeniden hesaplamada skor %44'ten %56'ya çıktı.

## Faz D — Canlılık Ajanı + GİRVAK paneli (1-2 Eki)

Özellik notu ve kararlar: [`faz-d-canlilik.md`](faz-d-canlilik.md).

**Canlılık:**

- [x] Periyodik tarama (uygulama içi zamanlayıcı ya da platform cron'u) +
      GİRVAK panelinde "taramayı şimdi çalıştır" butonu.
- [x] Belirli süredir hareketsiz eşleşme/iş birliği → kişiye özel hatırlatma (LLM).
- [x] Yeni ihtiyaç kartı → eski yetenek kartları yeniden taranır → "sana uygun
      yeni ihtiyaç" fırsatı.
- [x] Her olay `canlilik_olayi` tablosuna yazılır.

**GİRVAK paneli:**

- [x] Program hedefleri gerçek sayılarla: başvuru (80), kurum (20), eşleşme (10),
      pilot (5).
- [x] Pasifleşen bağlantılar listesi, son Canlılık olayları.

**Demo notu:** Tohum verinin bir kısmının `son_aktivite_tarihi` geriye çekilir;
pasifleşme günlerce beklemeden gösterilebilir.

## Genç akışı (28-29 Eyl) ✓

Plan ve kararlar: [`plans/genc-akisi.md`](plans/genc-akisi.md); elle deneme: [`plans/genc-akisi-deneme.md`](plans/genc-akisi-deneme.md).

- [x] Kayıt formu (profil alanları, KVKK onayı), profil düzenleme, eski hesaplara bant
- [x] Müsaitlik çoklu seçim (staj dahil)
- [x] Kart onayında otomatik puanlama ve yeniden eşleştirme (sonradan gelen genç açığı kapandı)
- [x] Keşif form bilgilerini sormaz; çalışma başına kanıt ve referans
- [x] Kart ve çalışma düzenleme; değişen çalışmanın göstergesi sıfırlanır
- [ ] "Yeni iş ekle" sohbeti: **dondurma sonrasına ertelendi** (karar 16)
- [x] Gençten ilgi, karşılıklı ilgi, "şimdilik değil", ihtiyaç kapanma kuralı; ilgi gösterilmiş kayıt korunur
- [x] Genç ana sayfası (fırsatlar, kartını güçlendir, ilgilerim) ve firma tarafında ilgi gösterenler
- [x] Canlılık: yanıtsız genç ilgisi (firmaya, 5 gün)
- [x] Toplu metin denetimi (`plans/genc-akisi-metinler.md`, `icerik-rehberi.md`): 30 Eyl, genç ve firma ekranları birlikte; son onay Zühre'de

## Firma akışı (29 Eyl →)

Plan ve kararlar: [`plans/firma-akisi.md`](plans/firma-akisi.md). Özellik dondurma tarihi bu görev için kayabilir (29 Eyl kararı).

- [x] Taraf kavramı (davranış değişmez)
- [x] Firma kayıt formu ve profil
- [x] İlan kapatma (nedenli)
- [x] Firma doğrulaması (alan adı ipucu + GİRVAK onayı)
- [x] Firma kartı (sohbet + düzenleme)
- [x] Ortak ilanı ve iki kapı
- [x] Firma–firma eşleştirme
- [x] Firmalar arası ilgi ve iş birliği
- [x] GİRVAK sayıları, Canlılık süzgeci, demo verisi
- [x] Belgeler ve deneme senaryosu (elle deneme: `plans/firma-akisi-deneme.md`)

## Güvenlik: SSRF engeli (30 Eyl) ✓

- [x] Kanıt linki kontrolü iç ağa istek atmaz (`backend/app/core/guvenli_istek.py`): şema/port sınırı, bütün çözülen IP'ler genel internette, yönlendirme adımları denetlenir, bağlantı denetlenen IP'ye sabitlenir (DNS yeniden bağlama kapalı).

## Gözden geçirme ve düzeltme günü (3 Eki)

Yeni özellik değil; Faz B'de bilinçli olarak dışarıda bırakılan ve denemede
eksikliği görülen profil işleri ile arayüz düzeltmeleri. Akşam özellik dondurma.

- [ ] Profil alanları (kayıttan sonra doldurulan şehir, çalışma modeli, müsaitlik,
      sektör) gözden geçirilir. *Genç tarafı genç akışında yapıldı; firma tarafı kaldı.*
- [ ] Profil düzenleme sayfası (genç ve kurum). *Genç `/profil` hazır; firma kaldı.*
- [ ] Arayüz düzeltmeleri (C ve D'den biriken küçük işler).

## Tanımlama incelemesi (5 Eki)

Ajan inceleme sırasının 3. adımı. Kötü girdi senaryo seti
(`backend/scripts/tanimlama_senaryolari.py`, gerçek modelle): mevcut durum 19/23, düzeltmeler sonrası 42/42
(`backend/tests/tanimlama_senaryolari/karne_*.json`). Kod 7 Ekim akşamı donar, 8 Ekim prova.

- [x] Senaryo seti: 10 kötü girdi (tek cümle, rol tarifi, ölçülemez kriter, "yarıya insin",
      hep "bilmiyorum", alakasız yıl, İngilizce, ortak tarifi, istem enjeksiyonu, uzun metin).
- [x] A: zorunlu alan tavanı 2 → 4; "belirtilmedi" yer tutucusu yok; onay boş alanı reddeder;
      taslakta problem / kriter / kısıtlar düzenlenebilir; çalışma modeli ve müsaitlik zorunlu
      seçim ("Fark etmez" = filtre yok).
- [x] B: yapılandırılmış başarı ölçütü (`ihtiyac_karti.basari_olcutu`), hedef yoksa bir ek soru,
      "ölçüm yöntemi belirlenecek" işareti.
- [x] D: sayfa yenilenince sohbet geri gelir (`GET /tanimlama/sohbet/{id}`, `sessionStorage`).
- [x] C: kapatma nedeni `hatali_girildi`; GİRVAK sayılarında ayrı.
- [x] **"Düzenle" düğmesi** (5 Eki, `plans/ilan-duzenleme.md`): açık ilan yerinde düzenlenir
      (`PATCH /ihtiyac-kartlari/{id}`, onaydaki form); kopyalama ve ilgi aktarımı gerekmedi,
      ilgiler kendiliğinden korunur. İş birliği başlamış ya da kapalı ilan 409.
- [x] Genç kapısında firmanın kayıt bilgileri bağlam olarak gitmiyor (bulgu 5): örnek sorular
      sektöre uyarlanamıyor. Firma kartı sohbetinde de örnekler sektöre uyarlanmıyor.
      *6 Eki: iki kapıya da bağlam gider; kullanım kuralı `PROFIL_BASLIGI`'nda.*
- [x] Sohbet ilk mesajda kapanabiliyor; kısıtlar ve şehir sohbette sorulmuyor (bulgu 6'nın
      kalanı; çalışma modeli ve müsaitlik onay formunda zorunlu yapıldı). *6 Eki: kısıt ve
      şehir boşsa bir kez koşul sorusu (`kosul_eksigi`).*
- [x] Küçükler (bulgu 7): kayıtlı kartta "kart no" satırı teknik; talimatlarda "kurum" kelimesi.
- [x] İlan metni "Neden uygun?" isteminde veri olarak işaretlenmiyor (istem enjeksiyonuna karşı
      sınır işareti); senaryo setinde sohbet tarafı temiz çıktı, gerekçe tarafı denenmedi.
      *6 Eki: `<ilan>`/`<aday>` etiketleri, kural `app/core/istem_guvenligi.py`. Doğrulama'nın
      `<kanit_metni>` kuralı aynı modüle taşınabilir (borç).*
- [x] "Bilmiyorum" diyen firma 7 tura kadar soru görüyor: açıklama turları tur hakkından
      düşmüyor. *6 Eki: `SohbetCikarimi.cevap_veremiyor`; "bilmiyorum" açıklama turu açmaz.*
- [ ] Elle deneme (kullanıcı): "Düzenle", koşul sorusu, sektöre uyarlanan örnekler. Senaryo
      karnesi istem değiştiği için eskidi; ücretli canlı koşu isteğe bağlı.
- [ ] Mimari borç: `servisler/kart_hazirlama` API katmanından (`api.yetenek_kartlari`) import
      ediyor; döngü edevlet'te tembel importla kırıldı, `embedding_hesapla` servis katmanına
      taşınmalı.

## Doğrulama incelemesi (1-5 Eki) ✓

Ajan inceleme sırasının 2. adımı. Plan ve adım adım durum: `plans/dogrulama-iyilestirme.md`
(14 adım). Ölçüm: 45 vakalı değerlendirme seti ve karneler
(`backend/tests/degerlendirme_seti/karneler/`); son karne Kanıt %96, Sonuç %84, Rol %84,
sahte vakada yanlış 3: 0.

- [x] Ölçüm altyapısı, katmanlama, "—" ve tek kanıt servisi, puan çekirdeği (1-4).
- [x] Link, dosya ve görsel okuma; yedek okuyucu (5, 9, 10).
- [x] Kimlik, e-posta ve inceleme kuyruğu; referans; hesap bağlama (6-8).
- [x] Kötüye kullanım işaretleri (11).
- [x] Link çürümesi yoklaması, GİRVAK gözlem paneli, adalet raporu, haftalık canlı karne (12).
- [x] Eşleştirme incelemesine hazırlık: kart bonusu iki seçeneği `matching-algorithm.md` § 4.1'de (13). **Karar bekliyor, formül değişmedi.**
- [x] Son belge denetimi (14).
- [ ] Kullanıcıya kalan hesap ve anahtar işleri: `plans/dogrulama-iyilestirme.md` sonundaki Adım 12 durum bloğu.

## Faz E — Yayına alma + tohum veri (4 Eki)

- [ ] Frontend: Vercel. Backend: Railway ya da Render. Postgres: pgvector
      destekleyen yönetilen servis (Neon ya da Supabase).
- [ ] Canlı frontend adresi backend'in CORS_ORIGINS ayarına eklenecek.
- [ ] **Railway cron'u ve `TARAMA_ANAHTARI`:** canlıda zamanlanmış görev günde iki
      kez (09:00, 18:00 İstanbul) `POST /canlilik/tarama`'yı `X-Tarama-Anahtari`
      başlığıyla çağırır; anahtar `.env`'de, kullanıcı token'ı değil (Faz D notu § 4).
- [ ] Migration'lar canlı veritabanında sıfırdan çalışır. *Yerelde boş veritabanında doğrulandı (30 Eyl): `upgrade head`, `alembic check` (model ile şema aynı) ve `downgrade base` temiz.*
- [ ] Tohum veri: 30-50 yetenek kartı, 8-10 kurum, birkaç tamamlanmış ve
      pasifleşmiş iş birliği. Demo senaryosuyla aynı hikâyeden beslenir.
- [ ] Tohum veriye **son adımı kalmış ve bir adımı gecikmiş** hazır bir iş birliği
      eklenir: demoda gecikme etiketi ve tamamlanma (→ tamamlanmış pilot sinyali)
      beklemeden gösterilebilsin (Faz C notu).
- [ ] Tohum veride **aynı ihtiyaca uyan iki benzer genç kartı**: birinin tamamlanmış
      pilotu var, diğerinin yok. Demoda yeni bir kurumun öneri listesinde pilotlu
      kartın öne geçtiği gösterilir (pilot bonusu en çok +0.125; iki kartın
      benzerliği yakın seçilmeli ki fark sıralamayı çevirsin).
- [ ] Demo hesapları (genç, kurum, GİRVAK) hazır.

## Faz F — Uçtan uca prova (5 Eki)

- [ ] Demo senaryosu canlı adreste baştan sona en az iki kez.
- [ ] README güncel: proje adı, canlı adres, ekran görüntüleri, "Sırada" bölümü.
- [x] LICENSE dosyası (MIT).
- [ ] `architecture.md`, `agent-specs.md`, `data-schema.md` koddaki gerçek durumla uyumlu. *Orkestrasyon ("supervisor") ifadesi README, CLAUDE.md ve architecture'da düzeltildi (30 Eyl).*
- [ ] Yedek demo videosu (canlı demoda LLM gecikmesine karşı).

## Kesim çizgisi

Kayma olursa sırayla tampona gider: (1) GİRVAK panelinin grafik kısmı (sayılar
kalır), (2) Canlılık'ın "yeni fırsat" dalı (hatırlatma kalır), (3) Takip'in durum özeti.

**Asla kesilmez:** döngünün kapanması (Faz B + Takip tamamlanma sinyali) ve
yayına alma.

## Kapsam dışı

Mobil uygulama, taraflar arası mesajlaşma, e-posta bildirimi (gerçek e-posta yalnızca
kayıt doğrulaması ve referans isteği için gider), ESCO
taksonomisi, çoklu dil, refresh token / OAuth, httpOnly cookie'ye geçiş
(ürünleşme dönemi).

## Çalışma kuralları

- Her faz önce kısa bir özellik notuyla başlar (ne yapar, hangi tablo, hangi uç
  nokta, ne yapmaz), kod sonra yazılır.
- Her bulgu / özellik ayrı commit ve testle girer.
- Commit mesajlarında Claude veya Opus imzası / co-author satırı bulunmaz.
- Faz sonunda `CLAUDE.md` ve bu belge güncellenir.
