# E-posta: konuşulanlar ve yapılacaklar (6 Eki)

Durum: **karar notu, plan değil.** Yeni bir sohbette bu dosyadan başlanır; plan orada yazılır.

## Bugün ne var

- Kod hazır: `app/core/dis_servisler/eposta.py` (kipler: `resend`, `log`, `kapali`; seçim
  `kurulum.eposta_gonderici()`, gönderim hatası akışı düşürmez: `dusmeden_gonder`).
- E-posta yalnızca iki yerde gidiyor: referans isteği ve hatırlatması
  (`app/servisler/dogrulama/referans_epostasi.py`) ve gencin e-posta adresini doğrulama
  (`app/servisler/kimlik_dogrulama.py`). Resend kurulu değil: kip `log`, bağlantı yalnızca
  backend terminalinde görünüyor.
- Eşleşmeden sonra e-posta yok: karşılıklı ilgide (`kabul_edildi`) site içi bildirim gidiyor
  ve iki tarafın e-posta adresi sitede birbirine açılıyor (`iletisim` alanı).

## Kararlar

1. **Alan adı yok.** Resend herkese göndermek için doğrulanmış alan adı istiyor (gönderenin
   adresin sahibi olduğunu kanıtlaması; sahte e-postayı önler). Alan adı olmadan yalnızca hesap
   sahibinin kendi adresine gönderiyor. Bu yüzden Resend şimdilik yok.
2. **Brevo önerildi:** ücretsiz (günde 300), alan adı istemiyor; tek bir gönderen adresinin
   (kullanıcının Gmail'i) doğrulanması yetiyor. Kodda yeni bir adaptör gerekir
   (`BrevoGonderici`, aynı `EpostaGonderici` protokolü; `EPOSTA_SAGLAYICI=brevo`). Not: Gmail
   adresinden otomatik gönderim spama düşebilir; kullanıcıya söylendi.
3. **Brevo tek işle üç şeyi çözer:** referans e-postası, adres doğrulaması ve yeni
   "eşleştiniz" e-postası. Öncelik düşük ("cepte"); demo için şart değil.
4. **"E-posta yaz" düğmesi (öncelikli, ücretsiz, servis gerekmez):** karşılıklı ilgiden sonra
   eşleşme / iş birliği ekranında `mailto:` bağlantısı; kişinin kendi e-posta programı hazır
   bir taslakla açılır, kişi düzenleyip kendi adresinden gönderir. Taslak **kişiselleştirilir**
   (LLM yok, şablon): alıcının adı, gönderen firma/genç adı, ilanın problemi, başarı kriteri,
   gencin kartından bir çalışma başlığı; firma→genç ("sen") ve genç→firma ("siz") ayrı metin.
   Metinler `docs/icerik-rehberi.md`'ye uyar. Sıra: Eşleştirme incelemesi (paralel oturum)
   bittikten sonra, aynı ekranlara dokunmasınlar diye.

**Durum (7 Eki):** "E-posta yaz" düğmesi yapıldı (`lib/eposta-taslagi.ts`, `IletisimSatiri`'nin
`taslak` prop'u). Taslak dört yönde: firma→genç, genç→firma, firma→firma (iki yön). Bağlantı
1500 karakteri geçmez; sığmazsa çalışma, sonra başarı ölçütü düşer, sonra problem kısalır.
Uçlara e-posta içermeyen iki alan eklendi: `basari_kriteri` ve `calisma_basligi`
(`/eslestirme/onerilerim`, `/isbirliklerim`, `/isbirligi/{id}`; `/me` ilan özetinde
`basari_kriteri`). Brevo (karar 2-3) henüz yapılmadı.

## Örnek taslak (firma → genç)

> Konu: Zemin360 eşleşmesi: {ilan_kisa}
>
> Merhaba {genc_adi},
> {firma_adi} olarak Zemin360'ta "{problem}" ihtiyacımız için eşleştik. Kartındaki
> "{calisma_basligi}" çalışman dikkatimizi çekti. Hedefimiz: {basari_kriteri}.
> Bu hafta kısa bir tanışma görüşmesi yapabilir miyiz?

## Dikkat

`mailto` adresi çok uzun olmasın (gövde ~1500 karakteri geçmesin). E-posta adresi yalnızca
`kabul_edildi`'de ve yalnızca iki tarafa döner; düğme de yalnızca orada görünür.
