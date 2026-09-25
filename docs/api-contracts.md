# API Sözleşmeleri

Ajan başına dışarıya açılan uç noktalar. Detaylı akışlar için bkz. `sequence-diagrams.md`, veri modelleri için bkz. `data-schema.md`.

| Ajan | Uç nokta | Yöntem | Not |
|---|---|---|---|
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
| **Eşleştirme** | `/eslestirme/calistir` | Arka plan iş (cron/kuyruk) | Kullanıcı isteğine bağlı değil |
| | `/eslestirme/oneriler/{kurum_id}` | GET | Sıralı liste + gerekçe. `skor_esigi` ve `az_sonuc_uyarisi` yanıtta döner — arayüz eşiği kendi içine yazmaz |
| | `/eslestirme/ilgileniyorum` | POST | `ESLESME.durum`'u günceller, `ISBIRLIGI` oluşturabilir |
| **Canlılık** | `/canlilik/tarama` | Arka plan iş (günlük cron) | Pasif `ESLESME` kayıtlarını tarar |
| | `/canlilik/hatirlatma/{eslesme_id}` | GET | Üretilen mesajı gösterir |
| **Takip** | `/isbirligi/{id}/milestone-ekle` | POST | |
| | `/isbirligi/{id}/milestone/{mid}` | PATCH | Durum günceller, kanıt ekler |
| | `/isbirligi/{id}/zaman-cizelgesi` | GET | İki tarafa da aynı görünüm |

## Mimari Notlar

- **Eşleştirme ve Canlılık ajanları arka plan işi** (senkron endpoint değil) — Genç ve Kurum aynı anda platformda olmak zorunda değil.
- **Referans yanıt endpoint'i girişsiz** — referans kişiyi üye olmaya zorlamak yanıt oranını düşürür.
