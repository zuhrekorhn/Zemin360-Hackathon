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
| 25-26 Eyl | A — Sağlamlaştırma | İnceleme bulguları kapandı, Gemini ücretli anahtara geçildi |
| 27-29 Eyl | B — Kimlik ve iki taraflı döngü | JWT, üç rol, genç paneli, karşılıklı onay |
| 30 Eyl-1 Eki | C — Takip Ajanı | Milestone planı, ilerleme, tamamlanma sinyali |
| 2-3 Eki | D — Canlılık Ajanı + GİRVAK paneli | Tarama, hatırlatma, fırsat, KPI'lar |
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

## Faz B — Kimlik ve iki taraflı döngü (27-29 Eyl)

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
- [ ] Genç paneli: kartım, kanıtlarım, bana gelen ilgiler, iş birliklerim.
- [ ] Kurum paneli: ihtiyaç kartlarım, önerilerim, iş birliklerim.
- [x] Karşılıklı onay: kurum "ilgileniyorum" der → eşleşme `ilgileniliyor` →
      genç kabul eder → `kabul_edildi` + iş birliği açılır → **iletişim bilgisi
      ancak şimdi iki tarafa görünür**. Genç reddederse `reddedildi`.
- [ ] Uygulama içi bildirimler (tablo + panelde sayaç). Gerçek e-posta yok.

**Kabul:** İki ayrı tarayıcıda genç ve kurum olarak döngü, iletişim açılmasına
kadar çıkmaz sokak olmadan yürür.

## Faz C — Takip Ajanı (30 Eyl-1 Eki)

- [ ] İş birliği açılınca ajan ihtiyaç kartının başarı kriterinden 3-5
      milestone'luk plan önerir (LLM, yapılandırılmış çıktı).
- [ ] İki taraf planı onaylar ya da düzenler.
- [ ] Her milestone iki tarafça işaretlenir; iki taraf da aynı zaman çizelgesini görür.
- [ ] Ajan kısa durum özeti yazar; tarihi geçen milestone'u işaretler.
- [ ] İş birliği tamamlanınca gencin kartına "tamamlanmış pilot" sinyali yazılır
      ve Eşleştirme'nin doğrulama bonusuna girer. **Geri besleme döngüsü burada kapanır.**

**Sınır:** Ajan karar vermez, milestone'u kendisi kapatmaz; öneri ve özet üretir.

## Faz D — Canlılık Ajanı + GİRVAK paneli (2-3 Eki)

**Canlılık:**

- [ ] Periyodik tarama (uygulama içi zamanlayıcı ya da platform cron'u) +
      GİRVAK panelinde "taramayı şimdi çalıştır" butonu.
- [ ] Belirli süredir hareketsiz eşleşme/iş birliği → kişiye özel hatırlatma (LLM).
- [ ] Yeni ihtiyaç kartı → eski yetenek kartları yeniden taranır → "sana uygun
      yeni ihtiyaç" fırsatı.
- [ ] Her olay `canlilik_olayi` tablosuna yazılır.

**GİRVAK paneli:**

- [ ] Program hedefleri gerçek sayılarla: başvuru (80), kurum (20), eşleşme (10),
      pilot (5).
- [ ] Pasifleşen bağlantılar listesi, son Canlılık olayları.

**Demo notu:** Tohum verinin bir kısmının `son_aktivite_tarihi` geriye çekilir;
pasifleşme günlerce beklemeden gösterilebilir.

## Faz E — Yayına alma + tohum veri (4 Eki)

- [ ] Frontend: Vercel. Backend: Railway ya da Render. Postgres: pgvector
      destekleyen yönetilen servis (Neon ya da Supabase).
- [ ] Canlı frontend adresi backend'in CORS_ORIGINS ayarına eklenecek.
- [ ] Migration'lar canlı veritabanında sıfırdan çalışır.
- [ ] Tohum veri: 30-50 yetenek kartı, 8-10 kurum, birkaç tamamlanmış ve
      pasifleşmiş iş birliği. Demo senaryosuyla aynı hikâyeden beslenir.
- [ ] Demo hesapları (genç, kurum, GİRVAK) hazır.

## Faz F — Uçtan uca prova (5 Eki)

- [ ] Demo senaryosu canlı adreste baştan sona en az iki kez.
- [ ] README güncel: proje adı, canlı adres, ekran görüntüleri, "Sırada" bölümü.
- [ ] LICENSE dosyası (MIT).
- [ ] `architecture.md`, `agent-specs.md`, `data-schema.md` koddaki gerçek durumla uyumlu.
- [ ] Yedek demo videosu (canlı demoda LLM gecikmesine karşı).

## Kesim çizgisi

Kayma olursa sırayla tampona gider: (1) GİRVAK panelinin grafik kısmı (sayılar
kalır), (2) Canlılık'ın "yeni fırsat" dalı (hatırlatma kalır), (3) Takip'in durum özeti.

**Asla kesilmez:** döngünün kapanması (Faz B + Takip tamamlanma sinyali) ve
yayına alma.

## Kapsam dışı

Mobil uygulama, taraflar arası mesajlaşma, gerçek e-posta gönderimi, ESCO
taksonomisi, çoklu dil, refresh token / OAuth, httpOnly cookie'ye geçiş
(ürünleşme dönemi).

## Çalışma kuralları

- Her faz önce kısa bir özellik notuyla başlar (ne yapar, hangi tablo, hangi uç
  nokta, ne yapmaz), kod sonra yazılır.
- Her bulgu / özellik ayrı commit ve testle girer.
- Commit mesajlarında Claude veya Opus imzası / co-author satırı bulunmaz.
- Faz sonunda `CLAUDE.md` ve bu belge güncellenir.
