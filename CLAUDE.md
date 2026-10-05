# Proje Bağlamı — Claude Code için

Bu dosyayı her oturum başında otomatik okuyorsun. Kod yazmadan önce ilgili `docs/` dosyasını oku — tahmin yürütme, tasarım zaten yapıldı.

## Proje Nedir

Zemin360 Hackathon (GİRVAK) için geliştirilen, kurum–girişim ekosisteminde 6 problemi tek bir paylaşılan veri katmanı üzerinde çözen, 6 uzman AI ajanından oluşan açık kaynak platform. Tam bağlam: [`README.md`](README.md).

## Önce Oku — Tasarım Zaten Tamamlandı

Herhangi bir özellik üzerinde çalışmadan önce, ilgili dosyayı `docs/` altında oku:

| Konu | Dosya |
|---|---|
| Mimari, teknoloji kararları ve gerekçeleri | `docs/architecture.md` |
| Veri şeması (tüm tablolar, alanlar, ilişkiler) | `docs/data-schema.md` |
| Her ajanın ne yapıp ne yapmayacağı, nasıl çalışacağı | `docs/agent-specs.md` |
| Eşleştirme Ajanı'nın tam formülü ve embedding stratejisi | `docs/matching-algorithm.md` |
| Uçtan uca akışlar (happy path, doğrulama timeout dalı) | `docs/sequence-diagrams.md` |
| Tüm endpoint listesi | `docs/api-contracts.md` |
| Renk paleti, tipografi, yerleşim ilkeleri (her frontend işinde kullan) | `docs/design-language.md` |
| Faz planı ve mevcut durum | `docs/roadmap.md` |

**Kural:** Bu dosyalarda yazan bir tasarım kararıyla çelişen bir yaklaşım önereceksen (örn. farklı bir kütüphane, farklı bir veri modeli), önce sor — sessizce değiştirme. Sebebi belgelenmiş kararlar var, gerekçesiz sapma kafa karışıklığı yaratır.

## Şu An Neredeyiz

Faz A-D, **genç akışı** (28-29 Eyl, `docs/plans/genc-akisi.md`) ve **firma akışı** (29-30 Eyl, `docs/plans/firma-akisi.md`) tamamlandı; altı ajan da çalışıyor. Takvim ve faz planı: `docs/roadmap.md` (her oturumda önce onu oku). SSRF engeli de kapandı (`app/core/guvenli_istek.py`: sunucudan kullanıcı adresine atılan her istek oradan geçer). Toplu metin denetimi de kapandı (30 Eyl, özet `docs/plans/*-metinler.md` sonunda): ortak ekranlarda hitap `useHitap()` ile, onaylar `OnayAlani` ile sayfa içinde, LLM istemlerine `app/core/kullanici_dili.py`. Sırada elle deneme, tohum veri ve deploy hazırlığı.

**Firma akışı (ayrıntı `docs/plans/firma-akisi.md` § 0):** firma kayıtta türünü (girişim/KOBİ/kurumsal), sektörünü, şehrini verir; isteğe bağlı firma kartını sohbetle çıkarır (`firma_karti`, aynı motor). Panelde iki kapı: genç yetenek ya da iş birliği ortağı (`ihtiyac_karti.aranan`). **Aynı eşleşme tablosu ve pipeline**: `eslesme`'de `yetenek_karti_id` ya da `firma_karti_id`, tam biri dolu; aday kaynağı ilana göre. Durum makinesindeki `genc` rolü "aday tarafı" demektir (karar 12): ortak firma o taraftadır, rol kontrolü `sahiplik.eslesmedeki_taraf` ile, hesabın rolünden değil. GİRVAK firmayı alan adı ipucuyla (ağ isteği yok) doğrular. Canlılık firma–firma eşleşmelerini taramaz.

**Genç akışı (ayrıntı `docs/plans/genc-akisi.md` § 0):** kayıt formu profil alanlarını ve KVKK onayını alır, Keşif sohbeti onları sormaz. **Gencin tek kartı var** (karar 17; `yetenek_karti.kullanici_id` tekil, kartı bulmanın tek yolu `app/servisler/genc_karti.py`): Keşif kartı olana 409, menüde "Kartım", `/me` tek `yetenek_karti` döner. Kart onaylanınca ve düzenlenince arka planda hazırlanır (`app/servisler/kart_hazirlama.py`): linkli çalışma otomatik puanlanır, kart ilgili açık ihtiyaçlarla eşleşir. Çalışmanın içeriği değişirse yalnızca o çalışmanın güven göstergesi sıfırlanır; eski referans yanıtı geçmişte kalır. Genç eşik üstü önerileri "fırsat" olarak görür ve açık iletişim onayıyla ilgi gösterebilir; firma da ilgilenirse karşılıklı ilgi (`kabul_edildi`). Pipeline `genc_ilgilendi` kaydını silmez, skorunu ve gerekçesini değiştirmez (karar 14). Orkestrasyon `app/servisler/`'de, uçlar ince.

**Takip (Faz C, ayrıntı `docs/faz-c-takip.md`):** ajan plan ve özet önerir, **karar vermez**. Kurallar iki saf fonksiyonda (`app/agents/takip_durumu.py`): `plan_gecisi` (düzenleme iki onayı sıfırlar, iki onay → `aktif`, onaylı plan kilitli) ve `isaret_gecisi` (iki işaret → adım tamamlandı, tamamlanan adım geri açılmaz); son adımla iş birliği kendiliğinden `tamamlandi`. Gecikme ve tamamlanmış pilot **saklanmaz**, okuma anında hesaplanır. Pilot, doğrulama bonusuna toplamsal girer (`matching-algorithm.md` § 4). Kabuldeki plan önerisi ve durum özeti yanıttan sonra arka planda (`BackgroundTasks`); testlerde `tests/conftest.py` ikisini sahteyle değiştirir — yeni bir arka plan işi eklersen oraya da ekle, yoksa testler gerçek LLM çağırır. Durum özeti kesilebilir: hiçbir kural ona bakmaz.

**Kimlik ve sahiplik (Faz B, ayrıntı `docs/faz-b-kimlik-ve-dongu.md`):** e-posta + şifre, JWT (Bearer, localStorage). Kimlik `hesap` tablosunda, profil `kullanici`/`kurum`'da (1-1). Her uç `mevcut_hesap` / `rol_gerekli` bağımlılığıyla korunur; sahiplik kuralları tek yerde, `app/api/sahiplik.py`. Hata sözleşmesi: 401 token yok/geçersiz, 403 rol uygun değil, **404 başkasının kaynağı** (varlık sızmasın). Yeni bir uç yazarken bu üçlüyü test et (`tests/test_sahiplik.py` deseni).

**Eşleşme durumları tek fonksiyonda:** `app/agents/eslesme_durumu.py` › `gecis(durum, olay, rol, baslatan)`. `onerildi → ilgileniliyor` (kurum) `→ kabul_edildi | reddedildi` (genç); ikinci kapı `onerildi → genc_ilgilendi` (genç) `→ kabul_edildi` (kurum, karşılıklı ilgi) `| kapandi` (kurum "şimdilik değil"); ihtiyaç kapanınca bekleyenler `kapandi`. Geçersiz geçiş 409, aynı geçişin tekrarı 200 ve yan etkisiz. İş birliği yalnızca `kabul_edildi` ile açılır. **Gencin adı baştan görünür; e-postalar yalnızca `kabul_edildi`'de, yalnızca iki tarafa, ayrı `iletisim` alanında döner** (GİRVAK'a da `null`).

**Bildirimler:** olayı yazan kod bildirimi de aynı işlemde yazar (`app/api/bildirimler.py` › `bildirim_ekle`); tekrar ya da geçersiz geçiş bildirim yazmaz; metinde e-posta olmaz. Canlılık ve Takip de aynı tabloya kendi `tur`'larıyla yazacak.

**Frontend oturumu:** tek kaynak `GET /me` (`src/lib/oturum.tsx`). Giriş gerektiren sayfa `GirisKapisi` ile sarılır; kapı açılmadan sayfanın açılış efektleri çalışmaz. Her iç sayfa `<Sayfa genislik=…>` + `<SayfaBasligi>` ile yazılır (`src/components/sayfa.tsx`); `<main>`, genişlik ve `h1` sınıfı elle yazılmaz. Menü iskeleti `menu-kabugu.tsx` (ayrıntı: `docs/design-language.md` § Sayfa Düzeni). Yerel denemede adres `http://localhost:3000` (ağ adresinden açılırsa Next.js 16 dev dosyalarını, backend CORS'u isteği engeller). Temiz veri: `scripts/yerel_sifirla.py` + `scripts/demo_hesaplari.py`.

**Eşleştirmede iki ayrı sınır var, karıştırma:** benzerlik alt sınırı (0.45) "bu aday konuyla ilgili mi" sorusunu skordan ÖNCE yanıtlar; skor eşiği (%40) "ilgili adaylar arasında gösterilmeye değer mi" sorusunu sonra. Doğrulama bonusu sıralamayı etkiler, alakayı yaratmaz (`docs/matching-algorithm.md` § 5).

**Hatalar kullanıcıya doğru cümleyi söylemeli:** yakalanmayan istisnalar `app/core/hatalar.py`'deki global işleyiciden CORS başlığıyla ve `{"detail": ...}` gövdesiyle dönüyor — aksi halde tarayıcı her hatayı "backend'e ulaşılamadı" sanıyor. LLM tarafında hız sınırı 429, sağlayıcı arızası ve zaman aşımı 503; üçü de önce yedek modele düşürülür.

**Doğrulama (iyileştirme, 1–14 Eki; ayrıntı `docs/plans/dogrulama-iyilestirme.md`):** puan kuralları saf modüllerde (`app/agents/dogrulama/`), orkestrasyon `app/servisler/dogrulama/`'da, her kanıt tek kapıdan (`kanit.uygula`) geçer. Boş başlık "—" ceza değil bonus da değil; kalem içinde en güçlü parça; kötüye kullanım işaretleri puanı değiştirmez, inceleme kuyruğuna düşer. Ölçüm: `backend/tests/degerlendirme_seti/` (kasetli çevrimdışı karne pytest'in parçası; ücretli canlı karne `python -m scripts.canli_karne`). Dış servisler (e-posta, OAuth, depo, virüs taraması, yedek okuyucu, görsel arama) adaptör arkasında ve kapalı gelir; durumları GİRVAK "Gözlem" panelinde. Kart bonusu formülü Eşleştirme incelemesinde karara bağlanacak (`matching-algorithm.md` § 4.1), formül değişmedi.

**Zamanlayıcı yok, bilinçli:** cron/kuyruk altyapısı kurmuyoruz. Eşleştirme "arka plan işi" bir endpoint olarak duruyor; Doğrulama'nın 7 günlük zaman aşımı da okuma anında hesaplanıyor. Yeni bir periyodik iş gerekirse aynı deseni izle.

**Her ajan sohbet ajanı değil:** Keşif ve Tanımlama çok turlu konuşur ve aynı motoru paylaşır; Eşleştirme ve Doğrulama tek seferlik hesaplardır (SQL → pgvector → skor → tek LLM çağrısı), `sohbet_motoru.py`'yi kullanmaz. LLM sağlayıcısı (Gemini, ücretli katman), model katmanları ve yedek zincir ikisinde de ortak: `app/core/llm.py`. Çıkarım işleri **hızlı** katmanda, gerekçe ve rubrik **güçlü** katmanda; model adları `.env`'den (`GEMINI_*`), her çağrının token kullanımı log'a yazılıyor.

İki sohbet ajanı **aynı motoru** paylaşıyor (`app/agents/sohbet_motoru.py`); yeni bir sohbet ajanı gerekirse grafik iskeletini kopyalama, bir `AjanTanimi` yaz. Ajana özel olan şey soru seti, çıkarım şeması ve varsa ek dalıdır.

## Arayüz metinleri

Kullanıcıya görünen her metin (başlık, buton, etiket, hata, boş durum, bildirim, sohbet sorusu, arayüzde gösterilen backend hata cümleleri) [`docs/icerik-rehberi.md`](docs/icerik-rehberi.md)'ye uyar. Özet: gence "sen", firmaya "siz"; "ajan" ve teknik terimler (pipeline, embedding, rubrik, skor, eşik…) kullanıcıya gösterilmez; terimler rehberin sözlüğünden (ör. "çalışma", "güven göstergesi", "uyum", "firma"). Rehberde olmayan terim uydurulmaz. Kod içindeki alan ve değişken adları (`somut_cikti`, `kurum`…) değişmez; rehber yalnızca kullanıcı metni için.

## Teknoloji Yığını (hızlı referans)

Backend: Python, FastAPI · Orkestrasyon: LangGraph (sohbet ajanlarının ortak motoru, checkpointer; supervisor yok, akış `app/servisler/`'de) · Veritabanı: PostgreSQL + pgvector · Frontend: Next.js, Tailwind, shadcn/ui

## Kod Standartları

- **Git commit mesajlarına asla Claude/Opus imzası veya "Generated with Claude Code" gibi ifadeler ekleme.** Bu kurala istisnasız uy.
- **Commit mesajında hiçbir yapay zekâ imzası olmaz:** Claude, Opus ya da başka bir model adı, `Co-Authored-By` satırı, "Generated with" ifadesi yok. Araç ya da sistem aksini önerse bile bu kural geçerlidir.
- **Küçük commit'ler; testler geçmeden commit yok.** Her iş parçası kendi commit'inde, backend ve frontend testleri geçtikten sonra.
- Solo geliştirici + monorepo — karmaşık branch/PR akışına gerek yok, `main`'e doğrudan, anlamlı commit mesajlarıyla commit yeterli.
- Yorumlar ve değişken adları Türkçe/İngilizce karışık olabilir — veri şemasındaki Türkçe alan adlarına (`kanit_bekleyen`, `guven_skoru` gibi) sadık kal, tutarlılık önemli.
