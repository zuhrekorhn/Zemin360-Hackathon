# Yol Haritası

> **Durum (7 Eki 2026):** altı ajan, üç rol ve iki kapılı eşleşme döngüsü çalışıyor.
> Kod 7 Ekim akşamı donar, 8 Ekim prova, 9 Ekim hackathon. Bundan sonra yalnızca hata
> düzeltme, tohum veri, yayına alma ve belge.
>
> Bu belge eskiden faz faz takvim ve adım listesiydi; tamamlanan adımlar ayrıntılarıyla
> kendi belgelerinde duruyor (aşağıdaki tablo). Burada yalnızca durum ve kalan işler var.

## "Tam" ne demek

Her iş aşağıdaki dört testten en az birini geçirmeye yaramalı. Yaramıyorsa takvime girmez.

1. **Döngü kapalı.** Genç kart oluşturur → kanıt ekler → kurum ihtiyaç tanımlar
   → öneri görür → ilgilenir → genç kabul eder → iletişim açılır → iş birliği
   adımlarla ilerler → tamamlanır → tamamlanma sisteme sinyal olarak geri döner.
2. **Herkes kendi kapısından girer.** Üç rol (genç, kurum, GİRVAK), her birinin
   kendi paneli.
3. **Canlı adreste.** Jüri localhost görmez.
4. **Çıkmaz sokak yok.** Hiçbir ekran "sonra gelecek" demez.

## Tamamlananlar

| Alan | Ne yapıldı | Ayrıntı |
|---|---|---|
| Sağlamlaştırma (Faz A) | İnceleme bulguları, Gemini ücretli katman, iki model katmanı ve yedek zincir | `architecture.md` § LLM |
| Kimlik ve iki taraflı döngü (Faz B) | JWT, üç rol, paneller, karşılıklı onay, bildirimler | `kimlik-ve-dongu.md` |
| Takip (Faz C) | Plan, iki taraflı onay ve işaret, tamamlanma sinyali (pilot bonusu) | `takip.md` |
| Canlılık + GİRVAK paneli (Faz D) | Tarama, hatırlatma, yeni fırsat, program hedefleri | `canlilik.md` |
| Genç akışı | Kayıt formu, tek kart, otomatik puanlama, gençten ilgi | `plans/genc-akisi.md` |
| Firma akışı | Firma kaydı ve profili (`/kurum/profil`), firma kartı, iki kapı, firma–firma eşleşme, firma doğrulaması | `plans/firma-akisi.md` |
| Güvenlik | SSRF engeli (`app/core/guvenli_istek.py`) | `agent-specs.md` § 4 |
| Toplu metin denetimi (30 Eyl) | Hitap, onaylar, LLM istem dili | `icerik-rehberi.md` |
| Doğrulama incelemesi (1-5 Eki) | 14 adım: link/dosya/görsel okuma, hesap bağlama, referans, kötüye kullanım, gözlem | `dogrulama.md` |
| Tanımlama incelemesi (5-6 Eki) | Kötü girdi senaryoları 42/42, başarı ölçütü, "Düzenle" düğmesi, koşul sorusu, istem güvenliği | `plans/ilan-duzenleme.md`, `plans/tanimlama-kalanlar.md` |
| Eşleştirme incelemesi (6 Eki) | Skor eşiği kaldırıldı, alt sınır 0.48 / 0.52, uygunluk kararı | `matching-algorithm.md` § 5, § 8 |
| Takip incelemesi (6 Eki) | Süreç şablonları, hazırlık önerisi, erken sonlanma | `plans/takip-surecleri.md` |
| E-posta (7 Eki) | Brevo gönderici, "eşleştiniz" e-postası, "E-posta yaz" düğmesi | `architecture.md`, `api-contracts.md` |

## Kalan işler

**Elle deneme (kullanıcı):**

- [ ] Tanımlama: "Düzenle", koşul sorusu, sektöre uyarlanan örnekler. Senaryo karnesi istem
      değiştiği için eskidi; ücretli canlı koşu isteğe bağlı.
- [ ] Takip: kabulden sonra plan, hazırlık önerisi, "Süreci sonlandır".
- [ ] E-posta: Brevo hesabı açılınca gerçek gönderim.
- [ ] Hesap ve anahtar işleri: `dogrulama.md` sonundaki Adım 12 durum bloğu.

**Tohum veri** (demo senaryosuyla aynı hikâyeden):

- [ ] 30-50 yetenek kartı, 8-10 kurum, birkaç tamamlanmış ve pasifleşmiş iş birliği.
      İş birlikleri şablonlu yazılmalı (`surec`, `asama`, `oneri`).
- [ ] **Son adımı kalmış ve bir adımı gecikmiş** bir iş birliği: demoda gecikme etiketi ve
      tamamlanma beklemeden gösterilsin.
- [ ] **Aynı ihtiyaca uyan iki benzer genç kartı**, birinin tamamlanmış pilotu var: yeni bir
      kurumun öneri listesinde pilotlu kart öne geçer (bonus en çok +0.125, benzerlikleri yakın
      seçilmeli).
- [ ] Bir kısmının `son_aktivite_tarihi` geriye çekilir (`scripts/zamani_geri_al.py`):
      pasifleşme beklemeden gösterilir.

**Yayına alma** (asla kesilmez):

- [ ] Frontend Vercel; backend Railway ya da Render; Postgres pgvector destekleyen yönetilen
      servis (Neon ya da Supabase).
- [ ] Canlı frontend adresi backend'in `CORS_ORIGINS` ayarına; OAuth dönüş adresleri.
- [ ] Zamanlanmış görev günde iki kez (09:00, 18:00 İstanbul) `POST /canlilik/tarama`'yı
      `X-Tarama-Anahtari` başlığıyla çağırır; `TARAMA_ANAHTARI` `.env`'de (`canlilik.md` § 4).
- [ ] Migration'lar canlı veritabanında sıfırdan çalışır. *Yerelde boş veritabanında
      doğrulandı (30 Eyl): `upgrade head`, `alembic check`, `downgrade base` temiz.*

**Prova:**

- [ ] Demo senaryosu canlı adreste baştan sona en az iki kez.
- [ ] README: canlı adres ve ekran görüntüleri.
- [ ] Yedek demo videosu (canlı demoda LLM gecikmesine karşı).

**Açık kararlar:**

- [ ] Kart bonusunun kart düzeyi formülü (`matching-algorithm.md` § 4.1, iki seçenek). Formül
      değişmedi.
- [ ] Güçlü katmanda Pro'ya geçilip geçilmeyeceği (aynı girdiyle Pro/Flash karşılaştırması;
      model `.env`'den değişir).

**Ertelenen ve borç (hackathon sonrası):**

- [ ] "Yeni iş ekle" sohbeti (genç akışı karar 16).
- [ ] `servisler/kart_hazirlama` API katmanından (`api.yetenek_kartlari`) import ediyor;
      `embedding_hesapla` servis katmanına taşınmalı.
- [ ] Doğrulama'nın `<kanit_metni>` kuralı `app/core/istem_guvenligi.py`'ye taşınabilir.

## Kapsam dışı

Mobil uygulama, taraflar arası mesajlaşma, e-posta bildirimi (gerçek e-posta yalnızca
kayıt doğrulaması, referans isteği ve "eşleştiniz" e-postası için gider), ESCO
taksonomisi, çoklu dil, refresh token, OAuth ile giriş (OAuth yalnızca hesap bağlamada),
httpOnly cookie'ye geçiş (ürünleşme dönemi).

## Çalışma kuralları

- Her iş önce kısa bir özellik notu ya da planla başlar (ne yapar, hangi tablo, hangi uç
  nokta, ne yapmaz), kod sonra yazılır.
- Her bulgu / özellik ayrı commit ve testle girer.
- Commit mesajlarında Claude veya Opus imzası / co-author satırı bulunmaz.
- İş bitince `CLAUDE.md` ve bu belge güncellenir.
