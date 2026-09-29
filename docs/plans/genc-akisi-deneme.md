# Genç akışı: tarayıcıda elle deneme senaryosu

Kayıttan iş birliğine kadar genç akışının tamamı. Yaklaşık 15 dakika sürer.
İki ayrı tarayıcı penceresi kullan (biri gizli pencere olabilir): **A** gençler
için, **B** firma için. Adres her zaman `http://localhost:3000` olmalı; ağ
adresinden (`192.168.…`) açılırsa düğmeler çalışmaz.

## Hazırlık (bir kez)

`backend/` içinde:

1. `.env`'de şu değişkenler dolu olmalı:
   - `GOOGLE_API_KEY` ve `VOYAGE_API_KEY`: sohbet, eşleştirme ve plan önerisi için.
   - `DEMO_SIFRESI`: en az 8 karakter.
2. `alembic upgrade head`
3. `python scripts/yerel_sifirla.py`: yerel veritabanını boşaltır; onay için veritabanı adını sorar.
4. `python scripts/demo_hesaplari.py`: üç demo hesabı açar ve kartlarını yazar.
5. `python run.py --reload`

`frontend/` içinde: `npm run dev`

**Demo hesapları** (üçünün şifresi de `DEMO_SIFRESI`):

| Hesap | Rol | Ne var |
|---|---|---|
| `genc@demo.zemin360.example` | genç (Elif Demir) | Hazır yetenek kartı, kanıtsız iki çalışma. Bu senaryoda yalnızca rakip aday olarak var. |
| `kurum@demo.zemin360.example` | firma (Moda Dayanışma Kooperatifi) | Hazır ihtiyaç: gıda bankasının bağış ve dağıtım kayıtları için web uygulaması. İstanbul, hibrit, yarı zamanlı. |
| `girvak@demo.zemin360.example` | GİRVAK | İsteğe bağlı: 10. adımdan sonra sayıları görmek için. |

## Senaryo

### 1. Genç kaydı (A)

`/kayit` sayfasında "Gencim"i seç ve formu şöyle doldur:

- Kendi adın ve yeni bir e-posta.
- Şehir: **İstanbul**.
- Çalışma modeli: **Hibrit** işaretli.
- Müsaitlik: **Yarı zamanlı** işaretli.
- Durum: Öğrenci.
- KVKK kutusu işaretli.

Demo ihtiyacı bu üç koşulu arıyor; biri uymazsa fırsat hiç görünmez.

- **Beklenen:** Kayıttan sonra doğrudan Keşif sohbeti açılır. Başlıkta "Şimdilik atla" bağlantısı görünür.
- **Kontrol:** Sohbet şehri, çalışma modelini ya da müsaitliği sormaz.

### 2. Yetenek kartı (A)

Sohbette demo ihtiyacına benzeyen bir işi anlat. Örnek cevaplar:

- "Bir yardım derneği için bağışları ve ailelere yapılan dağıtımları kaydeden bir web uygulaması yaptım. Python ve FastAPI kullandım; aylık raporu otomatik çıkarıyor."
- Sektör sorulursa: "sivil toplum". Sonuç sorulursa: "300 aileyi takip ediyor". Pay sorulursa: "backend'i ben yazdım".
- Kanıt ve referans sorulursa: bir GitHub linki yaz ya da "yok" de.

Taslak gelince "Kartı onayla"ya bas.

- **Beklenen:** Kart kaydedilir. Arka planda eşleştirme çalışır ve 10-30 saniye sürebilir.
- **Linkini verdiysen:** Kart sayfasında (`/kart/…`) biraz sonra güven göstergesi dolar.

### 3. Fırsatı görme (A)

`/genc`'e git; gerekirse birkaç saniye sonra sayfayı yenile.

- **Beklenen:** "Sana uygun fırsatlar" bölümünde **Moda Dayanışma Kooperatifi** görünür. Kartta "%… uyum" rozeti ve "Neden uygun?" açıklaması var.
- **Kanıtsız çalışman varsa:** "Kartını güçlendir" bölümünde "Bu çalışmaya kanıt eklersen … fırsatta öne çıkabilirsin" satırı çıkar.
- **Fırsat yoksa:** Anlattığın iş ihtiyaçtan uzak kalmıştır. Kart sayfasında "Kartı düzenle" ya da "İş ekle" ile daha yakın bir çalışma ekle; eşleştirme yeniden çalışır.

### 4. İlgi gösterme (A)

Fırsatta "İlgileniyorum"a bas.

- **Beklenen:** Bir onay alanı açılır: "Firma da ilgilenirse e-posta adresin, sana ayrıca sorulmadan firmayla paylaşılır." "Bunu onaylıyorum" kutusu işaretlenmeden "İlgimi ilet" düğmesi çalışmaz.

Kutuyu işaretle ve "İlgimi ilet"e bas.

- **Beklenen:** Fırsat listeden çıkar. "İlgilerim" bölümünde **İlgin iletildi** etiketiyle ve "İlgimi geri çek" düğmesiyle görünür. E-posta hiçbir yerde görünmez.

### 4b. (İsteğe bağlı) Yanıtsız ilgi hatırlatması

Genç ilgi gösterdi, firma 5 gündür yanıt vermedi: firmaya bir kez hatırlatma
gider. Beş gün beklememek için zamanları geri çek. Bunu 5. adımdan **önce** yap:
karşılıklı ilgi oluşunca hatırlatma gitmez.

1. `backend/` içinde:

   ```bash
   python scripts/zamani_geri_al.py --gun 6   # yerel veritabanındaki bütün zamanları 6 gün geri çeker (onay sorar)
   python scripts/canlilik_taramasi.py        # taramayı çalıştırır
   ```

   Tarama betiği yerine `girvak@demo.zemin360.example` ile girip GİRVAK panelindeki "Taramayı şimdi çalıştır" düğmesine de basabilirsin.
2. **Beklenen:**
   - Firmanın (`kurum@…`) bildirimlerinde: "{genç adı} 6 gündür ihtiyacınızla ilgili yanıtınızı bekliyor. İlgileniyorsanız karşılıklı ilgiyi başlatabilir ya da “Şimdilik değil” diyebilirsiniz."
   - Gence bu türde bildirim gitmez.
   - GİRVAK panelinde "Son olaylar"da **Yanıtsız genç ilgisi** satırı görünür.
3. Taramayı ikinci kez çalıştır.
   - **Beklenen:** Yeni bildirim yok; aynı dönemde bir kez gider.
4. **Not:**
   - 6 günlük kaydırma Elif Demir'in önerisini de 6 gün eskitir; eşiği 7 gün olduğu için "bakılmayan öneri" hatırlatması çıkmaz.
   - `--gun 8` verirsen o da çıkar; bu beklenen bir davranış.

### 5. Firma tarafında görme (B)

`kurum@demo.zemin360.example` ile giriş yap.

- **Beklenen:** Bildirimlerde "{senin adın} ihtiyacınızla ilgileniyor. Siz de ilgilenirseniz iletişim bilgileriniz karşılıklı paylaşılır." yazar.

`/kurum` sayfasında ihtiyaç kartından önerilere git.

- **Beklenen:**
  - Sayfanın üstünde **"İlgi gösterenler"** bölümü var. Yeni genç orada, **İlgi gösterdi** rozetiyle; "İlgileniyorum" ve "Şimdilik değil" düğmeleri çıkıyor.
  - Elif Demir "Adaylar" altında.
  - Açıklama başlığı "Neden uygun?".
  - Gencin e-postası henüz görünmüyor.

### 6. Karşılıklı ilgi (B)

İlgi gösteren genç için "İlgileniyorum"a bas.

- **Beklenen:** Durum **Karşılıklı ilgi** olur, gencin e-postası görünür ve "İş birliğine gidin" bağlantısı çıkar.

### 7. İş birliği (A ve B)

**A (genç):** Bildirimde "Moda Dayanışma Kooperatifi ilgine karşılık verdi. İletişim bilgileriniz paylaşıldı ve iş birliği başladı." yazar.

- **Beklenen:** `/genc`'te "İlgilerim" altında **Karşılıklı ilgi** etiketi, firmanın e-postası ve "İş birliğine git" bağlantısı görünür.

İş birliği sayfasını aç.

- **Beklenen:** Birkaç saniye içinde plan önerisi gelir; gelmezse sayfayı yenile.

**A ve B:** Planı iki taraf da onaylar.

- **Beklenen:** İş birliği başlar; adımlar iki tarafça işaretlenebilir hâle gelir.

## Ek kontroller (isteğe bağlı)

- **Geri çekme:**
    1. Başka bir genç hesabıyla 1-4. adımları tekrarla.
    2. "İlgimi geri çek"e bas. Fırsat tekrar "Sana uygun fırsatlar"a döner.
    3. Firma sayfayı yenilerse "İlgi gösterenler"de bu genç artık yok.
- **Şimdilik değil:**
    1. Genç ilgi gösterir.
    2. Firma "Şimdilik değil" der ve onaylar.
    3. Gençte bildirim "Moda Dayanışma Kooperatifi tarafındaki fırsat kapandı." olur. "İlgilerim"de etiket **Kapandı**; ret ifadesi yok.
- **Firmanın başlattığı eski akış:**
    1. Firma, "Adaylar" altındaki Elif Demir için "İlgileniyorum" der.
    2. `genc@demo…` ile girilince "Bana gelen ilgiler"de "Kabul et / Reddet" düğmeleri çıkar.
    3. Kabul edilirse etiket **Karşılıklı ilgi** olur.
- **Eski hesap bandı:**
    1. `genc@demo…` ile gir.
    2. Paneldeki "Profilini tamamla" bandı görünmemeli; demo profili yeni alanlarla dolu.

## Bilinen sınırlar

- **Bekleme süreleri:** Eşleştirme ve plan önerisi arka planda çalışıyor; sayfalar kendiliğinden yenilenmiyor.
- **Onay pencereleri:** Tarayıcının kendi "Tamam/İptal" düğmelerini gösteriyor. Rehber eylem adı istiyor ("Sil / Vazgeç"); toplu metin denetiminde ele alınacak.
- **Canlılık hatırlatması şablonla gidiyor.** Yanıtsız genç ilgisi hatırlatması kişiselleştirilmiyor, çünkü kişiselleştirme istemi "sen" diye hitap ettiriyor; firmaya "siz" gitmesi gerekiyor. Diğer firma hatırlatmaları hâlâ "sen" diyor, toplu metin denetiminde düzeltilecek.
