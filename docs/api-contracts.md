# API Sözleşmeleri

Ajan başına dışarıya açılan uç noktalar. Detaylı akışlar için bkz. `sequence-diagrams.md`, veri modelleri için bkz. `data-schema.md`.

| Ajan | Uç nokta | Yöntem | Not |
|---|---|---|---|
| **Keşif** | `/kesif/sohbet/baslat` | POST | Yeni sohbet oturumu açar |
| | `/kesif/sohbet/cevap` | POST | Kullanıcı cevabını işler, sıradaki soruyu döner |
| | `/kesif/kart/onayla` | POST | Taslağı `YETENEK_KARTI`'na yazar |
| | `/yetenek-kartlari/{id}` | GET | İletişim bilgisi döndürmez (agent-specs.md § 1.5). Her somut çıktı, varsa Doğrulama rubriğini (`guven_skoru`) birlikte taşır — kanıt eklenmemişse `null` |
| **Tanımlama** | `/tanimlama/sohbet/baslat` | POST | Keşif ile aynı motoru kullanır, farklı soru seti |
| | `/tanimlama/sohbet/cevap` | POST | Kullanıcı (kurum) cevabını işler, sıradaki soruyu döner |
| | `/tanimlama/kart/onayla` | POST | Taslağı `IHTIYAC_KARTI`'na yazar |
| | `/ihtiyac-kartlari/{id}` | GET | Eşleştirme Ajanı'nın da okuyacağı kart görünümü. `kurum.id` döner (öneri uç noktası kurum kimliğiyle çalışıyor); iletişim e-postası dönmez |
| **Doğrulama** | `/dogrulama/kanit-ekle` | POST | `SOMUT_CIKTI` + ön rubrik skoru |
| | `/dogrulama/referans-yaniti` | POST | Token bazlı, girişsiz — referans kişi için auth gerektirmez |
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
