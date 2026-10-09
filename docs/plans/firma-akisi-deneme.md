# Firma akışı: tarayıcıda elle deneme senaryosu

Firma kaydından firmalar arası iş birliğine kadar. Yaklaşık 20 dakika sürer.
Üç ayrı tarayıcı penceresi (ya da profil) kullan: **A** yeni firma, **B**
kurumsal demo firma, **C** girişim demo firma. GİRVAK adımları için herhangi
birinde çıkış yapıp GİRVAK ile gir. Adres her zaman `http://localhost:3000`.

## Hazırlık (bir kez)

`backend/` içinde:

1. `.env`'de `GOOGLE_API_KEY`, `VOYAGE_API_KEY` ve `DEMO_SIFRESI` (en az 8 karakter) dolu.
2. `alembic upgrade head`
3. `python scripts/yerel_sifirla.py` (yerel veritabanını boşaltır; onay için adını sorar)
4. `python scripts/demo_hesaplari.py`. Sonunda "Firma–firma: … benzerliği …" satırı
   yazar; "UYARI" görürsen demo kartları birbirine önerilmez, bana haber ver.
5. `python run.py --reload`

`frontend/` içinde: `npm run dev`

**Demo hesapları** (hepsinin şifresi `DEMO_SIFRESI`):

| Hesap | Kim | Ne var |
|---|---|---|
| `kurumsal@demo.zemin360.example` | Anadolu Market Zinciri A.Ş. (kurumsal) | Açık ortak ilanı: şubelerde meyve-sebze firesi; yalnızca **girişim** arıyor, şehir fark etmez |
| `girisim@demo.zemin360.example` | Tazele Analitik (girişim) | Doğrulanmış firma; talep tahmini üzerine firma kartı |
| `kurum@demo.zemin360.example` | Moda Dayanışma Kooperatifi (KOBİ) | Genç ilanı (genç akışının demosu); firma kartı yok |
| `girvak@demo.zemin360.example` | GİRVAK | Onay bekleyen firmalar, sayılar |
| `genc@demo.zemin360.example` | Elif Demir (genç) | Bu senaryoda yok |

## Senaryo

### 1. Firma kaydı (A)

`/kayit`'ta "Kurum adına"yı seç. Firma adı, e-posta ve şifre, sonra:

- Firma türü **Girişim**, sektör "lojistik", şehir **İzmir**.
- İsteğe bağlı alanlardan web sitesi olarak e-postanın alan adını yaz (ör. e-posta
  `ayse@soguklojistik.example` ise site `soguklojistik.example`).
- KVKK kutusu işaretli.

**Beklenen:**
- Kayıttan sonra firma paneli (`/kurum`) açılır. Üstte iki kapı var: "Genç yetenek
  bul" ve "İş birliği ortağı bul".
- "Firma kartınızı oluşturun, diğer firmalar sizi bulabilsin." bandı görünür.
- "Profilinizi tamamlayın" bandı **görünmez**.

**Kontrol:** KVKK kutusu işaretlenmeden ya da tür seçilmeden kayıt gönderilmez.

### 2. Firma profili (A)

Menüden "Firma profili"ne git.

**Beklenen:** Bilgiler dolu; "Doğrulama bekleniyor…" satırı var. Tanıtım ekle, kaydet: "Firma profiliniz kaydedildi."

### 3. Firma kartı sohbeti (A)

Menüden "Firma kartı".

**Beklenen:** "Bu sohbet yapay zekâ desteğiyle ilerler…" notu. Sohbet firmanın ne yaptığını sorar; **adını, türünü, sektörünü ya da şehrini sormaz**.

Örnek cevaplar:

- "Gıda perakendecileri için soğuk zincir lojistiği yapıyoruz; şubelere günlük taze ürün dağıtımı."
- Yetkinlikler sorulursa: "soğuk zincir, rota optimizasyonu, depo yönetimi".
- Önceki işler ve aradığınız ortak sorulursa bir cümle yaz ya da "bilmiyorum" de: soru tekrarlanmaz.

Taslak gelince formda bir yetkinlik ekle, "Kartı onayla".

**Beklenen:** Kart görünür. Kısa süre "Kartınız eşleştirmeye hazırlanıyor…" notu çıkabilir; sayfayı yenileyince kaybolur. Paneldeki kart bandı gider.

### 4. Firma doğrulaması (GİRVAK)

`girvak@…` ile gir.

**Beklenen:**
- "Onay bekleyen firmalar"da A'nın firması görünür.
- İpucu "E-posta uzantısı (…) web sitesiyle uyuşuyor."
- Tam e-posta görünmez, yalnızca uzantısı.

"Onayla"ya bas.

**Beklenen:**
- Firma listeden çıkar.
- A'nın bildirimlerinde "Firmanız doğrulandı…" yazar.
- A'nın profilinde "Doğrulanmış firma" işareti görünür.

**İsteğe bağlı:** A profilinde web sitesini başka bir adresle değiştirirse doğrulama yeniden "bekleniyor"a döner ve GİRVAK listesine geri gelir.

### 5. Ortak ilanında firma önerileri (B)

`kurumsal@…` ile gir. Panelde ilan "İş birliği ortağı" etiketiyle görünür. "Önerileri gör".

**Beklenen:**
- Başlık "İlanınıza uyan firmalar…".
- **Tazele Analitik** öneriliyor: "Doğrulanmış firma" işareti, "%… uyum", "Neden uygun?", ne yaptığı, yetkinlikleri.
- A'nın firması (girişim, İzmir) konu yakınsa önerilebilir; ilan yalnızca girişim aradığı ve şehir şartı olmadığı için elenmez.
- Kooperatif (KOBİ, kartsız) hiç görünmez.

### 6. Aday firma ilgi gösterir (C)

`girisim@…` ile gir. Panelde **"Size uygun iş birliği fırsatları"** bölümü var: Anadolu Market Zinciri'nin ilanı, uyum ve "Neden uygun?" ile.

"İlgileniyoruz"a bas.

**Beklenen:**
- Onay alanı açılır: "İlanı açan firma da ilgilenirse e-posta adresiniz… paylaşılır."
- Kutu işaretlenmeden "İlgimizi ilet" çalışmaz.

İşaretle, ilet.

**Beklenen:** İlan "İlgilerimiz"e geçer, "İlginiz iletildi" etiketiyle ve "İlgimizi geri çek" düğmesiyle.

### 7. Karşılıklı ilgi (B)

**Beklenen:**
- Bildirim: "Tazele Analitik iş birliği ilanınızla ilgileniyor. Siz de ilgilenirseniz…"
- Öneriler sayfasında Tazele Analitik "İlgi gösterenler" altında.

"İlgileniyorum"a bas.

**Beklenen:**
- Durum "Karşılıklı ilgi" olur.
- "Ortak firmanın e-postası" görünür.
- "İş birliğine gidin" bağlantısı çıkar.

**C'de:**
- Bildirim: "Anadolu Market Zinciri A.Ş. ilginize karşılık verdi…"
- "İlgilerimiz"de "Karşılıklı ilgi" ve e-posta görünür.

### 8. İş birliği (B ve C)

İş birliği sayfasını iki pencerede aç.

**Beklenen:**
- Başlıkta "Anadolu Market Zinciri A.Ş. · Tazele Analitik" ve "İş birliği ortağı".
- Birkaç saniye içinde plan önerisi gelir; gelmezse sayfayı yenile ya da "plan iste".

İki taraf planı onaylar, bir adımı iki taraf da işaretler.

**Beklenen:**
- Onay düğmeleri her iki pencerede **kendi tarafı** için çalışır; C, ilan sahibi gibi görünmez.
- Adım "tamamlandı" olur.

### 9. Ters yön ve kapatma (B ve C, isteğe bağlı)

- **İlk ilgiyi ilan sahibi gösterir:**
  1. B, öneriler sayfasında (başka bir ilanda ya da yeni kayıtta) bir firma adayına "İlgileniyorum" der.
  2. Aday firmanın panelinde "Size gelen ilgiler" altında **Kabul et / Şimdilik değil** çıkar.
  3. Kabul ederse iş birliği açılır.
- **İlan kapatma:**
  1. B, panelde "İhtiyacı kapat"a basar, bir neden seçer ve "Kapat" der.
  2. İlan "Kapandı" etiketiyle listenin sonuna iner.
  3. Bekleyen aday firmaya "… tarafındaki fırsat kapandı." bildirimi gider; neden yazmaz.
- **GİRVAK:**
  - "Kapanan ihtiyaçlar"da neden sayısı görünür.
  - "Genç–firma ve firma–firma" bölümünde firma–firma karşılıklı ilgi ve iş birliği sayıları artar.

### 10. Genç kapısı değişmedi (kurum@…)

`kurum@…` ile gir, "Genç yetenek bul". Sohbet çalışma modeli ve müsaitlik sorabilir; onay formunda firmanın şehri/sektörü **sorulmaz** (profilde dolu). Genç akışı senaryosu (`genc-akisi-deneme.md`) aynen geçerli.

## Bilinen sınırlar

- **Canlılık** firma–firma eşleşmelerine hatırlatma göndermez (karar 18).
- **Profil değişikliği:** Firma profili (tür, şehir, doğrulama) değişince mevcut öneriler kendiliğinden yeniden hesaplanmaz. Öneriler sayfasındaki "Adayları yenile" günceller.
- **Bekleme:** Sayfalar arka plan işleri bitince kendiliğinden yenilenmez (kart hazırlama, plan önerisi).
- **Metinler:** Tanımlama sayfasının başlığı ve sohbet adı hâlâ "Tanımlama Ajanı"; toplu metin denetiminde.
