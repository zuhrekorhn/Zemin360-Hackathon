# Canlılık Ajanı ve GİRVAK paneli

"Yaşayan bir ağ": kurulan bağlantılar sessizce ölmesin. Bölüm numaraları sabittir; kod
yorumları onlara gönderme yapar.

## 0. Amaç ve sınır

Canlılık döngünün her aşamasında hareketsiz kalan kaydı fark eder ve ilgili kişiye kısa, kişiye
özel bir hatırlatma bırakır. Yeni bir ihtiyaç açıldığında, kartı uzun süredir duran gençlere
fırsatı bildirir. GİRVAK programın altı ihtiyaç alanını gerçek sayılarla, takılan süreçleri ve son
Canlılık olaylarını tek panelde görür.

**Sınır:**
- Davranış tahmini yapmaz; kural tabanlı eşikler yeter.
- Toplu ya da jenerik spam göndermez.
- Hiçbir kaydın durumunu değiştirmez: hatırlatır, karar vermez.
- Hatırlatmalar uygulama içi bildirimdir, e-postayla gitmez.

## 1. Hareketsizlik: neye göre, ne zaman, kime

Hareketsizlik **okuma anında** mevcut alanlardan hesaplanır; "pasif" diye bir alan saklanmaz.
Hareket ölçüsü eşleşmenin `son_aktivite_tarihi` (her geçişte ve her Takip eyleminde
güncellenir), gecikme ölçüsü adımın `hedef_tarih`'i.

| Tür (`tur`) | Kayıt ve durum | Eşik | Kime |
|---|---|---|---|
| `oneri_bekliyor` | Eşleşme `onerildi` | 7 gün | Firma; ihtiyaç kartı başına **tek, toplu** bildirim |
| `ilgi_yanitsiz_1` | Eşleşme `ilgileniliyor` | 3 gün | Aday |
| `ilgi_yanitsiz_2` | Eşleşme `ilgileniliyor` | 10 gün | Aday (ikinci ve son) + firma (bilgi) |
| `genc_ilgisi_yanitsiz` | Eşleşme `genc_ilgilendi` | 5 gün, tek kademe | Firma; yalnızca şablon metin, "siz" hitabı (G6) |
| `plan_onaysiz` | İş birliği `plan_bekliyor` | 5 gün | Planı henüz onaylamamış taraf(lar) |
| `isbirligi_hareketsiz` | İş birliği `aktif` | 14 gün | İki taraf |
| `adim_gecikti` | `aktif` iş birliğinde gecikmiş adım | Hedef tarihten 1 gün sonra | Adımı henüz işaretlememiş taraf(lar) |
| `yeni_firsat` | Yeni ihtiyacın önerisi (§ 2) | — | Genç |

**Kurallar:**
- **Kapsam dışı kayıtlar:** `reddedildi` ve `kapandi` eşleşmeler, `tamamlandi` ve `sonlandi` iş
  birlikleri hatırlatılmaz; hesabı olmayan profil de (`kimlik-ve-dongu.md` § 8). Firma–firma
  eşleşmeleri taranmaz (F18).
- **Gizli öneriler:** uygunluk kararı `uygun_degil` olan eşleşme (`matching-algorithm.md` § 8)
  hiçbir ekranda görünmediği için taramada da yok sayılır: hatırlatılmaz, `oneri_bekliyor`'daki
  öneri sayısına ve `yeni_firsat`'a girmez (`pasif_adaylar(..., yalniz_gorunur=True)`). GİRVAK'ın
  hareketsiz bağlantılar listesi süzgeçsiz okur.
- **Öncelik:** aynı iş birliğinde aynı kişiye aynı taramada tek hatırlatma gider; `adim_gecikti`
  `isbirligi_hareketsiz`'den önce gelir.
- **Eşikler tek yerde:** saf modül `app/agents/canlilik_kurallari.py`, tablo testle sabit.
  `.env`'den değiştirilmez; demo için zaman aracı var (§ 6).
- **Bildirim:** Canlılık türleriyle aynı bildirim tablosuna yazılır; tıklayınca ilgili sayfaya
  gider (firma öneriler sayfasına, genç ilgilere, iş birliği bildirimleri `/isbirligi/{id}`'ye).
  Metinde ad olabilir, e-posta olmaz.

## 2. "Yeni fırsat" dalı

Tarama son **7 gün** içinde açılmış ihtiyaçların `onerildi` önerilerine bakar. Önerilen yetenek
kartı en az **14 gün** önce oluşturulmuşsa kartın sahibine `yeni_firsat` bildirimi gider; her
(genç, ihtiyaç) çifti için bir kez. Yeni kart sahibi zaten fırsatlarına bakıyordur; eski kart
eşiği bu yüzden var.

Metin firmanın adını ve sektörünü söyler, ihtiyacın metnini söylemez; bağlantı `/genc#firsatlar`
(genç önerildiği fırsatı zaten görür, G1). Bildirim eşleşmeye bağlanmaz. "Başvur" düğmesi açmaz,
eşleşmenin durumunu değiştirmez.

## 3. Tekrarın önlenmesi

> **Bir kayıt için aynı türde olay, o kaydın son hareketinden SONRA zaten yazılmışsa yenisi
> yazılmaz.**

- **Hareketsizlik dönemi:** dönem başına tür başına en çok bir hatırlatma. Taraflardan biri bir
  şey yaparsa dönem kapanır; hareketsizlik yeniden eşiği aşarsa yeni dönem başlar. "Yanıt verdi,
  sonra yine sustu" yeniden hatırlatılır; "hiç kıpırdamadı" her taramada tekrarlanmaz.
- **Kademeler:** `ilgi_yanitsiz_1` ve `_2` ayrı türler, her biri bir kez; ikinciden sonra o dönemde
  başka ilgi hatırlatması gitmez.
- **Gecikmiş adım:** anahtar adım başınadır (`milestone_id`).
- **Yeni fırsat:** anahtar (yetenek kartı, ihtiyaç kartı) çifti; bir kez gider.
- **Eşzamanlı taramalar** `pg_advisory_xact_lock` ile sıraya girer (pipeline'la aynı desen); ikinci
  tarama birincinin yazdıklarını görür ve hiçbir şey yazmaz.
- **İdempotent:** taramayı art arda iki kez çalıştırmak ikinci seferde sıfır olay üretir (testli).

## 4. Periyodik tarama

Taramanın asıl işi bir uç noktadır: `POST /canlilik/tarama` ("zamanlayıcı yok" ilkesi,
`kararlar.md`). Uygulama içinde zamanlayıcı kurulmadı: ücretsiz katmanda uyuyan servisle uyur,
çoklu süreçte her worker kendi zamanlayıcısını çalıştırır, yeniden başlatmada kayar.

- **Bugün:** GİRVAK panelindeki **"Taramayı şimdi çalıştır"** düğmesi ya da
  `scripts/canlilik_taramasi.py`.
- **Ürünleşmede:** platform cron'u günde iki kez (09:00 ve 18:00, İstanbul) ucu çağırır.
- **Yetki:** GİRVAK token'ıyla (düğme) ya da `X-Tarama-Anahtari` başlığıyla (cron). Cron kullanıcı
  token'ı taşımaz (GİRVAK token'ı 7 günde düşer, tarama sessizce dururdu); kimliği `.env`'deki ayrı
  gizli anahtar `TARAMA_ANAHTARI` (en az 32 karakter), sabit zamanlı karşılaştırılır. Anahtar
  tanımlı değilse başlık yolu tamamen kapalıdır. Yanlış anahtar 401, diğer her çağrı 401/403.
- **Yanıt:** türe göre olay sayısı, gönderilen bildirim sayısı, süre. Panelde "son tarama".

Aynı tarama eşleşmeye bağlı olmayan üç işi de yapar (Canlılık olayı yazmazlar, özetin `olaylar`
sözlüğünde sayaçları görünür, hataları taramayı düşürmez):

- **Referans istekleri** (`dogrulama.md` § 7): bekleyen isteğe 3. gün tek hatırlatma e-postası
  (yalnızca sistemin gönderdiği isteklere), 7. günde `yanit_yok` ve gence nötr bildirim
  (`app/servisler/dogrulama/referans.py` › `referans_taramasi`). E-postalar commit'ten sonra gider.
- **Link çürümesi** (`dogrulama.md` § 10.4): eskiden açık okunmuş kanıt linklerini en çok haftada
  bir, taramada en çok 100 link yeniden açar (yalnızca erişim durumu). Üst üste 3 kez silinmiş ya
  da gizlenmiş çıkan link Kanıt'a girmez, gence nötr `kanit_curudu` bildirimi gider, önceki puan
  saklanır (`app/servisler/dogrulama/curume.py`).
- **Saklama süresi:** 90 günü geçen gözlem kayıtları ve referans izleri silinir (`dogrulama.md`
  § 10.3).

## 5. Kişiye özel hatırlatma metni

- **Hızlı katman, tek LLM çağrısı.** Girdi yapılandırılmış: tür, alıcının rolü, karşı tarafın adı,
  kaç gün, adım adı. Çıktı en fazla iki cümle, nötr ve destekleyici, bir eylem çağrısıyla.
- **Şablona düşer:** LLM yanıt vermezse ya da çıktı kurala uymazsa her türün sabit şablon metni
  kullanılır; hatırlatma asla kaybolmaz.
- **Eşzamanlılık sınırı:** bir taramada LLM çağrıları en çok 4'er eşzamanlı.
- **Yazılanlar:** metin hem `canlilik_olayi.mesaj_metni`'ne hem bildirime, aynı işlemde yazılır.

## 6. Veri modeli ve demo aracı

`canlilik_olayi(id, eslesme_id, tetiklenme_tarihi, tur, mesaj_metni, alici_hesap_id, milestone_id,
ihtiyac_karti_id)`. Olay eşleşmeye bağlıdır; toplu `oneri_bekliyor`'da her eşleşme için ayrı olay
yazılır, firmaya tek bildirim gider. İndeks `(eslesme_id, tur, tetiklenme_tarihi)` tekrar kuralının
sorgusu için.

**Demo aracı:** `scripts/zamani_geri_al.py --gun N` (yalnızca yerel, `APP_ENV=production`'da
çalışmaz) bütün tarih kolonlarını N gün geriye çeker; hareketsizlik günlerce beklemeden yerelde
gösterilir. Hangi kolonların kaydırıldığı betikte tek listede, test bütün tarih kolonlarını
kapsadığını denetler.

## 7. GİRVAK paneli

1. **Altı ihtiyaç alanı (Özet):** brifteki ihtiyaç alanları (Hackathon onboarding sunumu, 2-3. sayfa) için
   gerçek sayılar, her kartta brifteki adla: 01 Genç Yeteneklerin Keşfi, 02 Profil ve Portfolyo
   Doğruluğu, 03 Kurum–Kişi Eşleşmesi, 04 Yaşayan Bir Ağ, 05 İhtiyaçların Net Tanımı, 06 Şeffaf İş Birliği
   Takibi. Sayılar `GET /girvak/ozet`'ten (`app/api/girvak_ozet.py`), cümleleri arayüz kurar
   (`frontend/src/lib/girvak.ts`). **Uydurma hedef sayısı yok:** programın brifinde "80 başvuru, 20 kurum,
   10 eşleşme, 5 pilot" gibi sayısal hedefler bulunmuyor; önceki sürümdeki bu rakamlar kaldırıldı (10 Eki).

   | Alan | Ana sayı | Altındaki cümle |
   |---|---|---|
   | 01 Keşif | Kart oluşturan genç | Kayıtlı genç ve en az bir fırsat gören genç |
   | 02 Doğruluk | Değerlendirilen çalışmanın yüzdesi | Bekleyen inceleme sayısı |
   | 03 Eşleşme | Karşılıklı ilgi | Toplam öneri |
   | 04 Yaşayan ağ | Takılan süreç | Son 30 günde gönderilen hatırlatma (yeni fırsat bildirimi hariç) |
   | 05 Net tanım | Tanımlanan ihtiyaç | Hedef değeri (ölçülebilir) olan ihtiyaç |
   | 06 Takip | İş birliği | Tamamlanan; gecikmiş adım |

2. **Takılan süreçler:** eşiği aşmış kayıtlar, okuma anında aynı kurallarla; tür, taraflar,
   kaç gündür hareketsiz, son hatırlatmanın tarihi. En uzun süredir hareketsiz olan önce.
3. **Son Canlılık olayları:** son 20 olay; tür, alıcı, mesaj, zaman.
4. **“Şimdi kontrol et”** ve son kontrolün özeti.
5. **İş birlikleri:** bütün iş birlikleri (`GET /girvak/isbirlikleri`), duruma göre süzülür; taraflar ve adım
   ilerlemesi görünür, **e-posta ve iletişim hiç dönmez**. Satırdan iş birliğinin kendi sayfasına geçilir.
6. **Kararlar:** onay bekleyen firmalar, incelemeler ve daha önce verilen kararlar (“Şimdilik değil” dediğiniz
   firma burada durur ve onaylanabilir).
7. **Sayılar:** eşleşme hunisi (önerilen, karşılıklı ilgi, iş birliği, tamamlanan; adım adım yüzdeyle),
   hesaplar, kırılım, kapanan ihtiyaçların nedenleri; **Raporu yazdır** (menü yazdırmada gizlenir).
8. **Sistem durumu** (hesap menüsünde): dış servisler ve kanıt linklerinin açılabilirliği; teknik sayfa.

Panelin diğer bölümleri: genç–firma / firma–firma kırılımlı sayılar (F19), firma doğrulama (F6),
inceleme kuyruğu ve gözlem (`dogrulama.md` § 9, § 10.3).

## 8. Uç noktalar ve yetki

| Uç nokta | Kim | Not |
|---|---|---|
| `POST /canlilik/tarama` | GİRVAK ya da `X-Tarama-Anahtari` | Tarama özeti; idempotent |
| `GET /canlilik/pasifler` | GİRVAK | Okuma anında hareketsiz kayıtlar; kişisel veri yalnızca ad |
| `GET /canlilik/olaylar` | GİRVAK | Son olaylar (varsayılan 20) |
| `GET /girvak/sayilar` | GİRVAK | Hesap, kart, eşleşme, iş birliği sayıları, kırılım, kapanan ihtiyaçlar |
| `GET /girvak/ozet` | GİRVAK | Altı ihtiyaç alanı için ham sayılar (`kesif`, `dogruluk`, `eslesme`, `ag`, `tanim`, `takip`) |
| `GET /girvak/isbirlikleri` | GİRVAK | Bütün iş birlikleri; taraflar, durum, ilerleme; e-posta yok |

Genç ve firma bu uçları çağıramaz (403); hatırlatmayı bildirim olarak görür.

## 9. Kararlar

1. **Tetikleyici bir uç noktadır**, uygulama içi zamanlayıcı değil (§ 4).
2. **Program hedef sayısı yok; altı ihtiyaç alanı var.** Brifte sayısal hedef bulunmadığı için hedef çubukları
   kaldırıldı; panel, brifteki altı ihtiyaç alanının çözülüp çözülmediğini gerçek sayılarla gösterir (10 Eki).
3. **Yeni fırsat firmanın adını söyler** (§ 2). Genç önerildiği fırsatı zaten gördüğü için (G1)
   anonimliğin gerekçesi kalmadı.
4. **Eşikler** § 1'deki tablo; fırsatta 7 günlük yeni ihtiyaç ve 14 günlük eski kart.

## 10. Kapsam dışı

Hatırlatmaların e-posta ya da SMS ile gönderilmesi; hatırlatma tercihleri ve sessize alma;
davranış tahmini; Canlılık'ın bir kaydın durumunu değiştirmesi; GİRVAK'ın kullanıcı yönetimi;
zaman serisi / trend grafikleri; PDF dosyası üretme (yalnızca yazdır); firma–firma eşleşmelerinin taranması (F18).
