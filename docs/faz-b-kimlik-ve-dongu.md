# Faz B — Kimlik ve iki taraflı döngü (özellik notu)

> Roadmap § Faz B'nin özellik notu. Kod bu not onaylandıktan sonra yazılır.
> **Kabul ölçütü:** iki ayrı tarayıcıda genç ve kurum olarak döngü, iletişim
> açılmasına kadar çıkmaz sokak olmadan yürür.

## 1. Kimlik

- **Giriş yöntemi:** E-posta + şifre.
- **Şifre:** `argon2id` ile hash'lenir (`argon2-cffi`; bcrypt'in 72 baytlık şifre sınırı yok). Kural: en az 8 karakter.
- **Token:** JWT, HS256, `PyJWT`.
  - Gizli anahtar `JWT_GIZLI_ANAHTAR` (`.env`); tanımlı değilse uygulama açılmaz.
  - Claim'ler: `sub` = hesap id, `rol` (`genc` | `kurum` | `girvak`), `iat`, `exp` (7 gün).
  - Refresh token yok.
- **İstemci:**
  - Token localStorage'da (`zemin360.token`) tutulur, her istekte `Authorization: Bearer <token>` ile gönderilir.
  - Çıkış istemci tarafındadır: token silinir. Sunucuda iptal listesi yok.
  - Herhangi bir istek 401 dönerse token silinir, kullanıcı girişe yönlenir.

**Yeni uç noktalar**

| Uç nokta | Ne yapar |
|---|---|
| `POST /auth/kayit` `{email, sifre, rol: genc\|kurum, ad}` | Hesap ve boş profil açar; 201 + token döner (kayıtla birlikte giriş yapılmış olur). E-posta kayıtlıysa 409. |
| `POST /auth/giris` `{email, sifre}` | Token döner. Yanlış e-posta da yanlış şifre de aynı 401 mesajını alır; hangisinin yanlış olduğu söylenmez. |
| `GET /me` | Hesap (id, e-posta, rol), profil özeti (ad; genç için kart listesi, kurum için kurum id ve ihtiyaç kartı listesi), okunmamış bildirim sayısı. |

### Hesap verisi nerede duracak?

| | **A) Ayrı `hesap` tablosu** | B) `kullanici` / `kurum`'a alan eklemek |
|---|---|---|
| Yapı | `hesap(id, email UNIQUE, sifre_hash, rol, olusturma_tarihi)`; `kullanici.hesap_id` ve `kurum.hesap_id` UNIQUE FK (1-1) | `sifre_hash` iki tabloya eklenir; rol, kaydın hangi tabloda olduğundan çıkar |
| Giriş | Tek tabloda tek sorgu | İki tabloda arama; aynı e-posta iki tabloda da olabilir, hangisi geçerli? |
| GİRVAK | Profilsiz bir hesap, doğal | Üçüncü bir tablo ya da sahte bir profil gerekir |
| Sorumluluk | Hesap = kimlik, profil = alan verisi | `kullanici` hem kimlik hem kart sahibi |
| Maliyet | Bir tablo, bir join, bir migration | Migration küçük, ama kimlik kodu her yerde iki dallı |

**Öneri: A.**
- Giriş tek yerde, roller tek biçimde.
- GİRVAK'ın profile ihtiyacı yok.
- Faz C/D'deki "hesaba bildirim, hesaba yetki" işleri tek bir kimliğe bağlanır.
- `kullanici.email` ve `kurum.iletisim_email` **iletişim bilgisi** olarak kalır: kayıtta hesap e-postasıyla doldurulur, kimlik artık onlarla bulunmaz.

## 2. Roller ve kayıt

- **Genç ve kurum:** `/kayit` ekranından kendileri kayıt olur; rol kayıtta seçilir.
  - Kayıt anında boş bir profil açılır: genç için `kullanici(ad)`, kurum için `kurum(ad)`.
  - Şehir, çalışma modeli, müsaitlik (kurumda sektör ve şehir) bugünkü gibi kart onay formunda doldurulur ve profili günceller.
- **GİRVAK:** Açık kayıtla hesap açılamaz; `/auth/kayit` `rol=girvak`'ı 422 ile reddeder.
  - Hesap `scripts/girvak_hesabi.py --email …` ile açılır. Şifre komut satırında sorulur, repoda şifre yok.
  - Demo tohumu da aynı fonksiyonu kullanır.

## 3. Sahiplik: kim neye erişir

**Hata kodları**
- **401:** Token yok ya da geçersiz.
- **403:** Rol uygun değil.
- **404:** Başkasının kaynağı. Kaynağın var olduğu sızmasın diye 403 değil 404.

GİRVAK okuma işlerinde her şeyi görür. Yazma işleri genç ve kurumun işidir.

| Uç nokta | Girişsiz | Genç | Kurum | GİRVAK |
|---|---|---|---|---|
| `GET /health` | ✓ | ✓ | ✓ | ✓ |
| `POST /auth/kayit`, `POST /auth/giris` | ✓ | — | — | — |
| `GET /me`, bildirim uç noktaları | — | kendi | kendi | kendi |
| `POST /kesif/sohbet/baslat` | — | ✓ | — | — |
| `POST /kesif/sohbet/cevap`, `POST /kesif/kart/onayla` | — | oturumu kendisi açtıysa ¹ | — | — |
| `POST /tanimlama/sohbet/baslat` | — | — | ✓ | — |
| `POST /tanimlama/sohbet/cevap`, `POST /tanimlama/kart/onayla` | — | — | oturumu kendisi açtıysa ¹ | — |
| `GET /yetenek-kartlari/{id}` | — | kendi kartı | kendisine önerilmiş kart (gencin adı görünür, e-postası yok) | ✓ |
| `POST /yetenek-kartlari/{id}/embedding` | — | kendi kartı | — | ✓ |
| `GET /ihtiyac-kartlari/{id}` | — | kendisine ilgi gösterilmiş ihtiyaç (durum `ilgileniliyor` ve sonrası) | kendi kartı | ✓ |
| `POST /ihtiyac-kartlari/{id}/embedding` | — | — | kendi kartı | ✓ |
| `POST /eslestirme/calistir` | — | — | kendi kurumu (gövdedeki `kurum_id` kalkar, token'dan alınır) | herhangi kurum (`kurum_id` ile) |
| `GET /eslestirme/oneriler/{kurum_id}` | — | — | yalnızca kendi `kurum_id`'si | ✓ |
| `POST /eslestirme/ilgileniyorum` | — | — | eşleşmenin ihtiyaç kartı kendisininse | — |
| `GET /eslestirme/bana-gelenler` (yeni) | — | kendi kartlarına gelen ilgiler | — | — |
| `POST /eslestirme/{id}/kabul`, `POST /eslestirme/{id}/red` (yeni) | — | eşleşmenin yetenek kartı kendisininse | — | — |
| `GET /isbirliklerim` (yeni) | — | kendi | kendi | — |
| `POST /dogrulama/kanit-ekle`, `POST /dogrulama/itiraz` | — | kendi kartının çıktısı | — | — |
| `GET /dogrulama/kanit/{somut_cikti_id}` | — | kendi kartının çıktısı | — ² | ✓ |
| `GET /dogrulama/referans/{token}`, `POST /dogrulama/referans-yaniti` | ✓ (token ile) | ✓ | ✓ | ✓ |

¹ Sohbet oturumu açılırken checkpoint durumuna `hesap_id` yazılır; sonraki her istekte token'daki hesapla karşılaştırılır, uymazsa 404.

² Kurum rubriği zaten yetenek kartı görünümündeki `guven_skoru`'dan görüyor. Referans e-postaları ve yanıt linkleri kuruma hiç gitmez. Faz A'da README'ye "`GET /dogrulama/kanit` henüz yetkisiz" diye yazılan sınırlama böylece kapanır.

## 4. Onay artık hesaba bağlı

- **Upsert kalkıyor:** Keşif ve Tanımlama onayındaki "e-postayla bul veya oluştur" mantığı kalkar. Kart, token'daki hesabın profiline bağlanır.
- **Onay isteği:** E-posta ve ad alanları çıkar.
  - Şehir, çalışma modeli ve müsaitlik (kurumda sektör ve şehir) profil güncellemesi olarak kalır.
  - Faz A'daki kural aynen işler: boş gelen alan kayıtlı değeri silmez.
- **`lib/yerel.ts` kalkar:** "En son oluşturduğun kart / kurum kimliği" artık `GET /me`'den gelir. Öneriler sayfasındaki `?kurum=` parametresi de kalkar; kurum kendi önerilerini token'la görür.
- **Testler:** Mevcut e-posta upsert testleri, hesaba bağlı profil güncellemesi testlerine dönüşür.

## 5. İki taraflı döngü: eşleşme durumları

| Şu an | Olay | Kim yapar | Sonra | Yan etki |
|---|---|---|---|---|
| — | Pipeline adayı seçer | sistem | `onerildi` | Yeni öneri eklendiyse kuruma bildirim |
| `onerildi` | "İlgileniyorum" | kurum (ihtiyacın sahibi) | `ilgileniliyor` | Gence bildirim |
| `ilgileniliyor` | "Kabul et" | genç (kartın sahibi) | `kabul_edildi` | İş birliği açılır; e-postalar iki tarafa görünür; kuruma bildirim |
| `ilgileniliyor` | "Reddet" | genç (kartın sahibi) | `reddedildi` | Kuruma bildirim (nötr dil) |
| `onerildi` | Yeniden hesapta artık uygun değil | sistem | kayıt silinir | Mevcut kural; karar verilmiş kayda dokunulmaz |

- **Geçersiz geçişler:** Tablo dışındaki her geçiş **409** döner ve mevcut durumu söyler. Örnekler:
  - `onerildi` iken kabul
  - `reddedildi` iken ilgileniyorum
  - `kabul_edildi` iken red
- **Aynı geçişin tekrarı** (çift tıklama; örneğin `ilgileniliyor` iken yeniden "ilgileniyorum") 200 ile mevcut durumu döner, yan etkiyi (bildirim, iş birliği) tekrarlamaz.
- **Aktivite tarihi:** Her geçişte `son_aktivite_tarihi` güncellenir; Canlılık Ajanı bunu okuyacak. `GET /isbirliklerim` de bu tarihe göre sıralanır (en yeni önce).
- **Kural tek yerde:** Geçiş kuralı tek bir saf fonksiyonda durur (`gecis(durum, olay, rol)`); yukarıdaki tablo testle birebir sabitlenir.
- **Ad baştan görünür, e-posta kabulle açılır:**
  - Gencin adı yetenek kartı görünümünde (öneriler, kart sayfası) kuruma her durumda görünür; kurumun adı da gence baştan görünür.
  - Kabulden önce gizli kalan yalnızca **e-postalar**: gencin e-postası ve kurumun iletişim e-postası.
  - Bunlar ayrı bir yanıt alanında (`iletisim`) taşınır, yalnızca `kabul_edildi` durumunda ve yalnızca iki taraftan birine döner; diğer durumlarda `null`.
  - Test: `kabul_edildi` öncesi hiçbir yanıtta e-posta yok; gencin adı ise var.
- **Bugünkü davranış değişiyor:** "İlgileniyorum" artık doğrudan iş birliği açmıyor; iş birliği gencin kabulüyle açılıyor.

## 6. Uygulama içi bildirimler

- **Tablo:** `bildirim(id, hesap_id FK, tur, metin, eslesme_id FK nullable, olusturma_tarihi, okundu_tarihi nullable)`. Gerçek e-posta gönderilmez.

| Olay | Kime | Metin (örnek) |
|---|---|---|
| Pipeline yeni öneri ekledi | kurum | "İhtiyaç kartın için 3 yeni öneri var." |
| Kurum ilgilendi | genç | "Kooperatif X kartınla ilgileniyor. Kabul edersen e-posta adresleriniz paylaşılır." |
| Genç kabul etti | kurum | "Elif ilgini kabul etti; iletişim bilgileri açıldı." (gencin adı kullanılabilir) |
| Genç reddetti | kurum | "Elif bu eşleşmeyi şu an kabul etmedi." |
| Referans yanıtladı | genç | "Bir referansın yanıt verdi; güven göstergen güncellendi." |

- **Uç noktalar:**
  - `GET /bildirimler` (en yeni önce)
  - `POST /bildirimler/{id}/okundu`
  - `POST /bildirimler/hepsini-oku`
- **Okunmamış sayacı:**
  - `GET /me` okunmamış bildirim sayısını döner.
  - Üst menüdeki rozet sayfa değişiminde ve açık sayfada 60 saniyede bir tazelenir. Canlı bağlantı (websocket) yok.
- **Faz C/D:** Canlılık ve Takip bildirimleri aynı tabloya yazılır.

## 7. Ekranlar

| Sayfa | İçerik |
|---|---|
| `/kayit` | Rol seçimi (Genç / Kurum), ad, e-posta, şifre |
| `/giris` | E-posta, şifre |
| `/genc` (Genç paneli) | Kartlarım (her biri `/kart/[id]`'ye gider) · Kanıt bekleyenler · Bana gelen ilgiler (Kabul et / Reddet) · İş birliklerim (e-postalarla) |
| `/kurum` (Kurum paneli) | İhtiyaç kartlarım (her biri önerilere gider) · Önerilerim (durumlarıyla, gencin adıyla) · İş birliklerim (e-postalarla) |
| `/bildirimler` | Liste, "hepsini okundu say" |
| `/girvak` | Faz B'de sayılar: hesap, kart, eşleşme, iş birliği. Faz D'de hedeflerle ve grafiklerle genişler. "Faz D'de gelecek" diyen bir ekran olmaz. |

**Üst menü (layout), role göre**
- **Girişsiz:** Giriş, Kayıt
- **Genç:** Panelim, Yeni kart (Keşif), Bildirimler (okunmamış rozeti), Çıkış
- **Kurum:** Panelim, Yeni ihtiyaç (Tanımlama), Bildirimler (rozet), Çıkış
- **GİRVAK:** Panel, Çıkış

**Yönlendirmeler**
- Giriş gerektiren bir sayfa girişsiz açılırsa `/giris?sonra=<yol>`'a gidilir; girişten sonra geri dönülür.
- Rolü uymayan sayfa (örneğin kurumun `/kesif`'i açması) kendi paneline yönlenir.
- Herkese açık kalanlar: `/`, `/giris`, `/kayit`, `/referans?token=…`.
- Ana sayfadaki "Genç olarak başla" `/kayit?rol=genc`'e, "Kurum olarak başla" `/kayit?rol=kurum`'a gider.

## 8. Mevcut yerel veritabanı

Bugünkü kayıtların hiçbiri gerçek kullanıcı değil:
- 12 kullanıcı (10'u test/demo e-postalı), 4 kurum, 12 yetenek kartı, 4 ihtiyaç kartı.
- 4 eşleşme; bunların 2'si eski akışla gencin onayı olmadan `kabul_edildi` olmuş.
- 2 iş birliği ve 246 sohbet checkpoint'i.

- **Migration veri silmez:** `hesap` tablosu eklenir; `kullanici.hesap_id` ve `kurum.hesap_id` **nullable** olur. Eski profiller için sahte hesap uydurulmaz.
- **Yeni kural:** Hesabı olmayan profilin kartı eşleştirmeye girmez. Önerilse bile kabul edecek kimse yok, çıkmaz sokak olurdu. Kural eşleştirmenin SQL filtresine eklenir.
- **Yeni geliştirme betiği:** `scripts/yerel_sifirla.py`.
  - Uygulama tablolarını ve LangGraph checkpoint'lerini boşaltır.
  - Onay sorar; `APP_ENV=production` ise çalışmayı reddeder.
- **Öneri:** Faz B migration'ından sonra yerelde bir kez çalıştırıp demo hesaplarıyla temiz başlamak. Eski `kabul_edildi` kayıtları yeni modele uymadığı için ayrıca da temizlenmeleri gerekiyor.
- **Canlı veritabanı** (Faz E) zaten boş başlıyor.

## 9. Kapsam dışı ve demo hesapları

**Faz B'de yapılmayacaklar**
- Şifre sıfırlama ve e-posta doğrulama (SMTP yok)
- Refresh token, httpOnly cookie (ürünleşme dönemi), OAuth
- Giriş denemesi sınırlaması (rate limit)
- Hesap silme, profil düzenleme sayfası
- Bir kurumda birden fazla temsilci hesabı
- Kurumun ilgisini ya da gencin kabulünü geri çekmesi
- Taraflar arası mesajlaşma
- GİRVAK'ın kullanıcı yönetimi (Faz D)

**Demo hesapları:** `scripts/demo_hesaplari.py`
- Üç hesap açar: `genc@demo.zemin360.example`, `kurum@demo.zemin360.example`, `girvak@demo.zemin360.example`. (İlk yazılan `@demo.zemin360` giriş formunun e-posta doğrulamasından geçmiyordu; `.example` belgeler için ayrılmış alan adı, hiçbir zaman gerçek bir posta kutusuna çözülmez.)
- Şifre `.env`'deki `DEMO_SIFRESI`'nden gelir; repoda şifre yok.
- Genç hesabına bir örnek yetenek kartı, kuruma bir örnek ihtiyaç kartı eklenir. Kartlar sohbetsiz, doğrudan yazılır; LLM çağrısı yok, yalnızca embedding. İki kart birbirine önerilecek şekilde seçildi: betik gerçek benzerliği ve skoru yazdırır, iki sınırdan birine takılırsa uyarır (kanıtsız kartın skoru 0.75 × benzerlik; eşiği geçmek için benzerlik ≥ 0.534).
- Tam demo havuzu (30-50 kart, pasifleşmiş iş birlikleri) Faz E'nin işi.

## 10. Uygulama sırası

Onaydan sonra, her adım ayrı commit ve testli:

1. `hesap` tablosu, kayıt / giriş / `me`, JWT, şifre hash'i, `get_current_hesap` bağımlılığı
2. Sahiplik: § 3 tablosunun uç noktalara uygulanması (uç nokta başına 401 / 403 / 404 testleri)
3. Onayın hesaba bağlanması; e-posta upsert'inin kalkması; `lib/yerel.ts` yerine `/me`
4. Eşleşme durum makinesi, kabul/red, iş birliği, kabulde açılan e-postalar; yetenek kartı görünümüne gencin adı
5. Bildirimler
6. Yerel sıfırlama ve demo hesabı betikleri (tarayıcı denemesi eski, gencin onayı olmadan `kabul_edildi` olmuş kayıtlarla değil, temiz veriyle başlasın diye öne alındı)
7. Frontend: kayıt, giriş, çıkış, rol menüsü, yönlendirmeler
8. Frontend: genç ve kurum panelleri, bildirim sayfası, GİRVAK sayı sayfası
9. README ve belgeler; iki tarayıcıda kabul denemesi
