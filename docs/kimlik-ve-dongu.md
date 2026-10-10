# Kimlik, sahiplik ve iki taraflı döngü

Hesaplar, roller, kim neyi görebilir, eşleşmenin durumları ve bildirimler. Bölüm numaraları
sabittir; kod yorumları onlara gönderme yapar.

## 1. Kimlik

- **Giriş:** e-posta + şifre. Şifre `argon2id` ile hash'lenir (`argon2-cffi`; bcrypt'in 72
  baytlık sınırı yok), en az 8 karakter.
- **Token:** JWT, HS256 (`PyJWT`). Gizli anahtar `JWT_GIZLI_ANAHTAR`; boşsa ya da 32
  karakterden kısaysa uygulama açılmaz. Claim'ler: `sub` = hesap id, `rol`, `iat`, `exp` (7 gün).
  Refresh token yok.
- **İstemci:** token `localStorage`'da, her istekte `Authorization: Bearer <token>`. Çıkış
  istemci tarafında (token silinir). Herhangi bir istek 401 dönerse token silinir, kullanıcı
  girişe yönlenir. Oturumun tek kaynağı `GET /me` (`frontend/src/lib/oturum.tsx`).
- **E-posta doğrulama:** kayıttan sonra doğrulama bağlantısı gider (`eposta_dogrulama` tablosu,
  token'ın yalnızca SHA-256 özeti saklanır, 24 saat). Doğrulanmamış hesap her şeyi kullanır;
  gencin adı doğrulanınca kilitlenir, sonra yalnızca GİRVAK onayıyla değişir.

| Uç nokta | Ne yapar |
|---|---|
| `POST /auth/kayit` | Hesap ve profil açar, 201 + token. Gövde rolün profil alanlarını ve KVKK onayını taşır (G2, F2). E-posta kayıtlıysa 409. |
| `POST /auth/giris` | Token döner. Yanlış e-posta da yanlış şifre de aynı 401'i alır. |
| `GET /me` | Hesap, profil özeti (genç için tek `yetenek_karti`, firma için ihtiyaç kartları), okunmamış bildirim sayısı. |

### Hesap verisi nerede duruyor?

Kimlik ayrı `hesap` tablosunda, profil `kullanici` / `kurum`'da (1-1, `hesap_id` UNIQUE FK).

| | **Seçilen: ayrı `hesap` tablosu** | Seçilmeyen: profillere şifre eklemek |
|---|---|---|
| Giriş | Tek tabloda tek sorgu | İki tabloda arama; aynı e-posta iki tabloda olabilir |
| GİRVAK | Profilsiz bir hesap, doğal | Üçüncü tablo ya da sahte profil gerekir |
| Sorumluluk | Hesap = kimlik, profil = alan verisi | `kullanici` hem kimlik hem kart sahibi |

Bildirim ve yetki tek kimliğe bağlanır. `kullanici.email` ve `kurum.iletisim_email` iletişim
bilgisidir; kimlik onlarla bulunmaz.

## 2. Roller ve kayıt

| Rol | Arayüzdeki adı | Nasıl açılır |
|---|---|---|
| `genc` | Genç | `/kayit` formu: ad, e-posta, şifre, şehir, çalışma modeli, müsaitlik, kariyer durumu (isteğe bağlı okul, bölüm, bağlantılar), KVKK onayı |
| `kurum` | Firma | `/kayit` formu: firma adı, tür, sektör, şehir, KVKK onayı (isteğe bağlı alanlar F2'de) |
| `girvak` | GİRVAK | Açık kayıtla açılamaz (422). `scripts/girvak_hesabi.py --email …`; şifre komut satırında sorulur |

Formdaki bilgi sohbette tekrar sorulmaz; sohbete bağlam olarak gider (S4). Fotoğraf, yaş,
cinsiyet, TC kimlik no, adres ve ücret beklentisi bilinçli olarak toplanmaz.

## 3. Sahiplik: kim neye erişir

Kurallar tek modülde: `backend/app/servisler/sahiplik.py`. HTTP'den bağımsızdır; uç nokta
"göremez" kararını `app/api/kimlik.py` › `bulunamadi` ile 404'e çevirir.

**Hata sözleşmesi**
- **401:** token yok ya da geçersiz (`mevcut_hesap`).
- **403:** rol uygun değil (`rol_gerekli`).
- **404:** başkasının kaynağı. Kaynağın var olduğu sızmasın diye 403 değil 404.

Her yeni uç bu üçlüyle test edilir (`tests/test_sahiplik.py` deseni). GİRVAK okuma işlerinde
her şeyi görür; yazma işleri genç ve firmanındır.

| Kaynak | Genç | Firma | GİRVAK |
|---|---|---|---|
| Sohbet oturumu (Keşif, Tanımlama, firma kartı) | oturumu kendisi açtıysa ¹ | oturumu kendisi açtıysa ¹ | — |
| Yetenek kartı | kendi kartı | kendisine önerilmiş kart (gencin adı görünür, e-postası yok) | ✓ |
| İhtiyaç kartı | kendi kartına önerilmiş ihtiyaç (G1) | kendi kartı; firma kartına önerilmiş ortak ilanı (F16) | ✓ |
| Firma kartı | — | kendi kartı; ilanına önerilmiş firmanın kartı | ✓ |
| Eşleşme ve geçişleri | eşleşmenin aday tarafıysa | ilan tarafıysa ya da aday firmaysa (F12) | okur |
| İş birliği | taraflardan biriyse | taraflardan biriyse | okur, e-postasız |
| Kanıt, referans isteği, itiraz | kendi kartının çalışması | sonucu görür, dosyayı genç izin verirse | ✓ |
| Referans formu (`/dogrulama/referans/{token}`) | token'la girişsiz | token'la girişsiz | token'la girişsiz |

¹ Sohbet açılırken checkpoint durumuna hesap kimliği yazılır; sonraki her istekte token'daki
hesapla karşılaştırılır, uymazsa 404.

Uygunluk kararı `uygun_degil` olan eşleşme hiçbir okumada görünmez; sahiplik sorguları da
`gorunur_kosulu()`'nu uygular (`matching-algorithm.md` § 8).

## 4. Onay hesaba bağlı

Keşif, Tanımlama ve firma kartı onayı kartı token'daki hesabın profiline bağlar; onay isteğinde
e-posta ya da ad yoktur. Onaydaki profil alanları (şehir, çalışma modeli, müsaitlik) profil
güncellemesi olarak yazılır; boş gelen alan kayıtlı değeri silmez. Aynı sohbetin ikinci onayı
mevcut kartı döner (`oturum_id` UNIQUE).

## 5. İki taraflı döngü: eşleşme durumları

Geçiş kuralı tek bir saf fonksiyonda: `app/agents/eslesme_durumu.py` › `gecis(durum, olay, rol)`.
Tablo testle birebir sabitlenmiştir (`tests/test_eslesme_durumu.py`, `tests/test_ilgi_durumu.py`).
"Genç" rolü aday tarafı, "kurum" rolü ilan tarafı demektir (F12).

| Şu an | Olay | Kim | Sonra | Yan etki |
|---|---|---|---|---|
| — | Pipeline adayı seçer | sistem | `onerildi` | Yeni öneri varsa firmaya bildirim |
| `onerildi` | "İlgileniyorum" | ilan tarafı | `ilgileniliyor` | Adaya bildirim |
| `ilgileniliyor` | "Kabul et" | aday tarafı | `kabul_edildi` | İş birliği açılır, e-postalar iki tarafa açılır, "eşleştiniz" e-postası |
| `ilgileniliyor` | "Reddet" | aday tarafı | `reddedildi` | İlan tarafına nötr bildirim |
| `onerildi` | İlgi (iletişim onayıyla) | aday tarafı | `genc_ilgilendi` | Firmaya bildirim |
| `genc_ilgilendi` | İlgiyi geri çek | aday tarafı | `onerildi` | — |
| `genc_ilgilendi` | "İlgileniyorum" | ilan tarafı | `kabul_edildi` | Karşılıklı ilgi: iş birliği açılır, e-postalar açılır |
| `genc_ilgilendi` | "Şimdilik değil" | ilan tarafı | `kapandi` | Adaya nötr bildirim |
| `onerildi`, `genc_ilgilendi`, `ilgileniliyor` | İhtiyaç kapandı | sistem | `kapandi` | Bekleyenlere nötr bildirim |
| `onerildi` | Yeniden hesapta artık uygun değil | sistem | kayıt silinir | Karar verilmiş kayda dokunulmaz (G14) |

- **Geçersiz geçiş** 409 döner ve mevcut durumu söyler ("Bu eşleşme şu an … durumunda").
- **Aynı geçişin tekrarı** (çift tıklama) 200 ile mevcut durumu döner, yan etkiyi (bildirim,
  iş birliği, e-posta) tekrarlamaz.
- **Aktivite tarihi:** her gerçek geçişte `son_aktivite_tarihi` güncellenir; Canlılık onu okur.
- **Ad baştan görünür, e-posta karşılıklı ilgiyle açılır.** Gencin adı ve firmanın adı iki
  tarafa baştan görünür. E-postalar ayrı bir yanıt alanında (`iletisim`) yalnızca `kabul_edildi`
  durumunda ve yalnızca iki taraftan birine döner; diğer durumlarda ve GİRVAK'a `null`.
- **İş birliği yalnızca `kabul_edildi` ile açılır.**

## 6. Uygulama içi bildirimler

- **Tablo:** `bildirim(id, hesap_id, tur, metin, eslesme_id, olusturma_tarihi, okundu_tarihi)`.
- **Yazma:** olayı yazan kod bildirimi de aynı işlemde yazar (`app/servisler/bildirim.py` ›
  `bildirim_ekle`): olay olup bildirim kaybolmasın, bildirim olup olay geri alınmasın. Tekrar ya
  da geçersiz geçiş bildirim yazmaz. Metinde e-posta olmaz.
- **E-posta:** bildirimler e-postayla gönderilmez. İstisna: karşılıklı ilgi kesinleşince
  bildirimi alan tarafa giden "eşleştiniz" e-postası (`app/servisler/eslesme_epostasi.py`).
- **Türler** (`app/models/bildirim.py`): eşleşme (`yeni_oneri`, `ilgi`, `kabul`, `red`,
  `genc_ilgi`, `karsilikli_ilgi`, `firsat_kapandi`, `firsat_guncellendi`), takip (`plan_*`,
  `adim_*`, `isbirligi_tamamlandi`, `isbirligi_sonlandi`), doğrulama (`referans_yaniti`,
  `referans_yanit_yok`, `kanit_curudu`, `inceleme_sonucu`, `ad_degisikligi_sonucu`,
  `hesap_baglama_sonucu`), firma (`firma_dogrulandi`); Canlılık kendi türleriyle yazar
  (`canlilik.md` § 1).
- **Uç noktalar:** `GET /bildirimler` (en yeni önce), `POST /bildirimler/{id}/okundu`,
  `POST /bildirimler/hepsini-oku`. Okunmamış sayısı `GET /me`'de; üst menüdeki rozet sayfa
  değişiminde ve 60 saniyede bir tazelenir. Canlı bağlantı (websocket) yok.

## 7. Ekranlar

| Sayfa | Kim | İçerik |
|---|---|---|
| `/`, `/giris`, `/kayit`, `/kvkk` | herkes | Karşılama, giriş, rol seçimli kayıt, KVKK metni |
| `/eposta-dogrula`, `/referans?token=…` | herkes | E-posta doğrulama, referansın girişsiz yanıt formu |
| `/genc` | genç | "Fırsatlar": önce yanıt bekleyen işler (firmanın ilgisi, plan onayı, geciken adım), sonra fırsatlar; yan sütunda kart özeti, tamamlanacaklar, tek "Süreçlerin" listesi (`docs/kararlar.md` G18) |
| `/kesif`, `/kart/{id}`, `/profil`, `/hesap-baglama/{saglayici}` | genç | Kart sohbeti; kart, çalışma tercihleri ve güven göstergesi; "Hesabım" (ad, eğitim, bağlantılar, bağlı hesaplar, KVKK); hesap bağlama dönüşü |
| `/isbirliklerim` | genç, firma | İş birlikleri, önce süren |
| `/kurum` | firma | İki kapı, ilanlar, öneriler, iş birliği fırsatları, iş birlikleri |
| `/tanimlama`, `/kurum/oneriler`, `/kurum/ilan/{id}/duzenle` | firma | İhtiyaç sohbeti (`?aranan=genc` ya da `?aranan=firma`; parametresiz adres kapıyı sorar), öneriler, ilan düzenleme |
| `/kurum/kart`, `/kurum/profil` | firma | Firma kartı, firma profili |
| `/isbirligi/{id}` | iki taraf, GİRVAK | Plan, onaylar, adımlar, durum özeti |
| `/girvak`, `/girvak/kararlar`, `/girvak/isbirlikleri`, `/girvak/canlilik`, `/girvak/sayilar`, `/girvak/gozlem` | GİRVAK | Özet (altı ihtiyaç alanı), kararlar (firma onayı, inceleme), iş birlikleri, takılan süreçler, sayılar, sistem durumu |
| `/bildirimler` | herkes (girişli) | Liste, "hepsini okundu say" |

**Menü** (`frontend/src/lib/menu.ts`): genç için Fırsatlar, Kartım, İş birliklerim; firma için
Panelim, Yeni ihtiyaç, Firma kartı, İş birliklerim; GİRVAK için Özet, Karar bekleyenler, İş birlikleri,
Takılan süreçler, Sayılar (Sistem durumu hesap menüsünde). Bildirimler her ekranda zil ve okunmamış
sayısı; ayar sayfası (genç "Hesabım", firma "Firma profili") ve çıkış adın altındaki hesap menüsünde.

**Yönlendirme:** giriş gerektiren sayfa `GirisKapisi` ile sarılır; girişsiz açılırsa
`/giris?sonra=<yol>`, rolü uymuyorsa kendi paneli. Kurallar `frontend/src/lib/yonlendirme.ts`'de
(testli).

## 8. Hesapsız profiller

`kullanici.hesap_id` ve `kurum.hesap_id` boş bırakılabilir: kimlik tablosundan önce açılmış
profiller için sahte hesap uydurulmadı. Hesabı olmayan profilin kartı eşleştirmeye girmez
(önerilse bile kabul edecek kimse yok), bildirimi yazılmaz, GİRVAK sayılarına girmez. Bilinen
borç: veritabanı sıfırdan kurulduğu için bu dallar hackathon sonrası bir migration'la
(`hesap_id NOT NULL`) kaldırılabilir.

Yerel geliştirmede temiz veri: `scripts/yerel_sifirla.py` (uygulama tablolarını ve sohbet
checkpoint'lerini boşaltır, onay sorar, `APP_ENV=production` ise çalışmaz) ve ardından
`scripts/demo_hesaplari.py`.

## 9. Kapsam dışı ve demo hesapları

**Yapılmadı (bilinçli):** şifre sıfırlama, refresh token, httpOnly cookie, OAuth ile giriş
(OAuth yalnızca hesap bağlamada), giriş denemesi sınırlaması, hesap silme, bir firmada birden
fazla temsilci hesabı, taraflar arası mesajlaşma.

**Demo hesapları** (`scripts/demo_hesaplari.py`, şifre `.env`'deki `DEMO_SIFRESI`):
`genc@`, `kurum@`, `girvak@`, `girisim@`, `kurumsal@demo.zemin360.example`. `.example` alan adı
belgeler için ayrılmıştır, gerçek bir posta kutusuna çözülmez; e-posta göndericileri bu
adreslere ağ isteği atmaz. Genç kartı ile firmanın ihtiyaç kartı birbirine önerilecek şekilde
seçildi; betik benzerliği ve skoru yazdırır. Havuzu büyütmek için `scripts/demo_zenginlestir.py`.
