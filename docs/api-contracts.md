# API Sözleşmeleri

Ajan başına dışarıya açılan uç noktalar. Detaylı akışlar için bkz. `sequence-diagrams.md`, veri modelleri için bkz. `data-schema.md`.

**Kimlik ve sahiplik (Faz B):** `/health`, `/auth/kayit`, `/auth/giris` ve token'lı referans uçları (`GET /dogrulama/referans/{token}`, `POST /dogrulama/referans-yaniti`) dışındaki her uç nokta `Authorization: Bearer <token>` ister. 401 token yok/geçersiz, 403 rol uygun değil, 404 başkasının kaynağı (varlığı sızmasın diye 403 değil). Uç nokta başına kim erişir tablosu: `faz-b-kimlik-ve-dongu.md` § 3; kurallar `backend/app/api/sahiplik.py`'de.

| Ajan | Uç nokta | Yöntem | Not |
|---|---|---|---|
| **Kimlik** | `/auth/kayit` | POST | `{email, sifre, rol: genc\|kurum, ad}` → 201 + token. GİRVAK açık kayıtla açılamaz (422), e-posta kayıtlıysa 409 (bkz. `faz-b-kimlik-ve-dongu.md`) |
| | `/auth/giris` | POST | `{email, sifre}` → token. Yanlış e-posta ve yanlış şifre aynı 401'i alır |
| | `/me` | GET | Giriş gerekli (`Authorization: Bearer`). Hesap, profil özeti, kartlar, `okunmamis_bildirim` |
| **Bildirimler** | `/bildirimler` | GET | Kendi bildirimleri, en yeni önce (en çok 100). Her rol |
| | `/bildirimler/{id}/okundu` | POST | Kendi bildirimi; başkasınınki 404. Tekrarında ilk okunma tarihi korunur |
| | `/bildirimler/hepsini-oku` | POST | `{okunan}` döner |
| **Keşif** | `/kesif/sohbet/baslat` | POST | Yeni sohbet oturumu açar |
| | `/kesif/sohbet/cevap` | POST | Kullanıcı cevabını işler, sıradaki soruyu döner |
| | `/kesif/kart/onayla` | POST | Taslağı `YETENEK_KARTI`'na yazar. Tekrarlanabilir: aynı `oturum_id` ikinci kez gelirse yeni kart açılmaz, mevcut kart 200 ile döner. Embedding hesaplanamazsa kart yine 201 ile döner, `embedding_var: false` |
| | `/yetenek-kartlari/{id}/embedding` | POST | Embedding'i yeniden hesaplar (onayda vektör servisine ulaşılamadıysa). Servis yine yoksa 503 |
| | `/yetenek-kartlari/{id}` | GET | İletişim bilgisi döndürmez (agent-specs.md § 1.5). Her somut çıktı, varsa Doğrulama rubriğini (`guven_skoru`) birlikte taşır — kanıt eklenmemişse `null` |
| **Tanımlama** | `/tanimlama/sohbet/baslat` | POST | Keşif ile aynı motoru kullanır, farklı soru seti |
| | `/tanimlama/sohbet/cevap` | POST | Kullanıcı (kurum) cevabını işler, sıradaki soruyu döner |
| | `/tanimlama/kart/onayla` | POST | Taslağı `IHTIYAC_KARTI`'na yazar. Keşif'teki gibi tekrarlanabilir; eşleştirme yalnızca embedding hesaplandıysa arka planda başlar |
| | `/ihtiyac-kartlari/{id}/embedding` | POST | Embedding'i yeniden hesaplar; başarılıysa eşleştirmeyi başlatır |
| | `/ihtiyac-kartlari/{id}` | GET | Eşleştirme Ajanı'nın da okuyacağı kart görünümü. `kurum.id` döner (öneri uç noktası kurum kimliğiyle çalışıyor); iletişim e-postası dönmez |
| **Doğrulama** | `/dogrulama/kanit-ekle` | POST | `SOMUT_CIKTI` + ön rubrik skoru |
| | `/dogrulama/referans/{token}` | GET | Token bazlı, girişsiz. Referans kişinin yanıt vermeden önce gördüğü bilgi: çıktının başlığı, açıklaması, **iddia sahibinin adı** ve isteğin durumu. E-posta/telefon gibi iletişim bilgisi DÖNMEZ — referans kişi kimin için konuştuğunu bilmeli, ama bu uç nokta girişsiz olduğu için yalnızca yanıt vermeye yetecek kadarını açar. Zaman aşımı (`bekliyor` → `yanit_yok`) bu okuma anında hesaplanır |
| | `/dogrulama/referans-yaniti` | POST | Token bazlı, girişsiz — referans kişi için auth gerektirmez. Harcanmış **ya da süresi dolmuş** token 409 döner — GET ile aynı kural. Yanıt yalnızca `{baslik, durum}`: aynı çıktının diğer referanslarının e-postası, puanı ve token'ı DÖNMEZ |
| | `/dogrulama/itiraz` | POST | Yeniden değerlendirme tetikler |
| | `/dogrulama/kanit/{somut_cikti_id}` | GET | Kanıtın güncel durumu: rubrik puanı + referans istekleri. Zaman aşımı (`bekliyor` → `yanit_yok`) bu okuma anında hesaplanır — ayrı bir zamanlayıcı yok |
| **Eşleştirme** | `/eslestirme/calistir` | POST | Pipeline'ı yeniden çalıştırır. Kurum yalnızca kendi kurumu için (gövde boş; başka `kurum_id` 404), GİRVAK `kurum_id` vermek zorunda. Gövdede `ihtiyac_karti_id` verilmezse kurumun en son ihtiyaç kartı. İhtiyaç kartı onaylanınca (ya da embedding'i yeniden hesaplanınca) o kart için arka planda da çalışır (zamanlayıcı yok) |
| | `/eslestirme/oneriler/{kurum_id}` | GET | Kurum yalnızca kendi `kurum_id`'si (başkası 404), GİRVAK hepsi. `?ihtiyac_karti_id=` ile belirli kart (başka kurumunki 404), verilmezse en son kart. Sıralı liste + gerekçe. `skor_esigi` ve `az_sonuc_uyarisi` yanıtta döner — arayüz eşiği kendi içine yazmaz |
| | `/eslestirme/ilgileniyorum` | POST | Kurum (ihtiyacın sahibi): `onerildi` → `ilgileniliyor`. İş birliği AÇMAZ |
| | `/eslestirme/{id}/kabul` | POST | Genç (kartın sahibi): `ilgileniliyor` → `kabul_edildi`, `ISBIRLIGI` açılır, yanıtta `iletisim` (iki e-posta) |
| | `/eslestirme/{id}/red` | POST | Genç (kartın sahibi): `ilgileniliyor` → `reddedildi` |
| | `/eslestirme/bana-gelenler` | GET | Genç: kartlarına ilgi gösterilmiş eşleşmeler (`onerildi` hariç), ihtiyaç kartı ve kurum adıyla |
| | `/eslestirme/onerilerim` | GET | Kurum: tüm ihtiyaç kartlarındaki öneriler, durum ve gencin adıyla (`iletisim` yalnızca `kabul_edildi`'de). Yalnızca okur, pipeline çalıştırmaz |
| | `/isbirliklerim` | GET | Genç ve kurum: taraf olduğu iş birlikleri, iki tarafa aynı görünüm, `iletisim` dahil; eşleşmenin `son_aktivite_tarihi`'ne göre en yeni önce |
| **GİRVAK** | `/girvak/sayilar` | GET | Yalnızca GİRVAK. Hesap (role göre), kart, eşleşme (duruma göre), iş birliği sayıları; kişisel veri yok |
| **Canlılık** | `/canlilik/tarama` | Arka plan iş (günlük cron) | Pasif `ESLESME` kayıtlarını tarar |
| | `/canlilik/hatirlatma/{eslesme_id}` | GET | Üretilen mesajı gösterir |
| **Takip** | `/isbirligi/{id}` | GET | İki tarafa **birebir aynı** görünüm: plan, zaman çizelgesi (gecikme okuma anında), onaylar, ilerleme, durum özeti, `iletisim`. GİRVAK okur, e-postasız; başkasının iş birliği 404. (Sözleşmedeki ayrı `/zaman-cizelgesi` ucunun yerine, Faz C notu § 7) |
| | `/isbirligi/{id}/plan-oner` | POST | Taraflar. Ajandan (yeniden) plan: 3-5 adım; mevcut adımları siler, iki onayı sıfırlar. Yalnızca `plan_bekliyor`, onaylı planda 409; LLM yoksa 503 ve plan değişmez. Genç kabul edince arka planda da çalışır |
| | `/isbirligi/{id}/milestone-ekle` | POST | Taraflar, yalnızca `plan_bekliyor`; iki onay sıfırlanır. 201 |
| | `/isbirligi/{id}/milestone/{mid}` | PATCH | Taslakta başlık/açıklama/hedef tarih (iki onay sıfırlanır); `aktif`'te yalnızca `kanit_linki`. Gönderilmeyen alan değişmez; onaylı planda içerik 409 |
| | `/isbirligi/{id}/milestone/{mid}` | DELETE | Taslaktan siler, sıra yeniden numaralanır |
| | `/isbirligi/{id}/plan-onayla` | POST | Çağıranın tarafı onaylar; iki onay → `aktif` (plan kilitlenir). Boş plan 409, tekrar 200 yan etkisiz |
| | `/isbirligi/{id}/milestone/{mid}/isaretle` | POST | Çağıranın tarafı "tamamlandı" der; iki taraf da derse adım tamamlanır, **son adımla iş birliği kendiliğinden `tamamlandi`** (kural). Plan onaylanmadan 409 |
| | `/isbirligi/{id}/milestone/{mid}/isareti-geri-al` | POST | Kendi işaretini geri alır; iki tarafça tamamlanmış adım geri açılmaz (409) |

**Takip (Faz C, `faz-c-takip.md`):** Yazan uçlar yalnızca iki taraf (genç ve kurum): GİRVAK 403, başkası 404. Kurallar tek yerde, `app/agents/takip_durumu.py` (`plan_gecisi`, `isaret_gecisi`). Yazma istekleri iş birliği satırını kilitler (çift tıklama iki kez uygulanmaz). Bildirimler karşı tarafa; okunmamış "plan düzenlendi" varken yenisi yazılmaz. `GET /bildirimler` satırı iş birliği varsa `isbirligi_id` taşır.

**Eşleşme durumları** (docs/faz-b-kimlik-ve-dongu.md § 5): kural tek yerde, `app/agents/eslesme_durumu.py` › `gecis()`. Tablo dışı geçiş 409 ve mevcut durumu söyler; aynı geçişin tekrarı 200, yan etkisiz. Gencin adı kart görünümünde (`genc_adi`) baştan var; e-postalar yalnızca `kabul_edildi`'de, yalnızca iki tarafa, ayrı `iletisim` alanında döner (GİRVAK'a da `null`).

## Mimari Notlar

- **Eşleştirme ve Canlılık ajanları arka plan işi** (senkron endpoint değil) — Genç ve Kurum aynı anda platformda olmak zorunda değil.
- **Referans yanıt endpoint'i girişsiz** — referans kişiyi üye olmaya zorlamak yanıt oranını düşürür.
