# Firma akışı — yeni arayüz metinleri (toplu denetim listesi)

Yazılan ve değişen her kullanıcı metni burada (genç akışındaki karar 15'in
devamı). Kurallar `docs/icerik-rehberi.md`'de: firmaya "siz", teknik terim yok.
Toplu metin denetimi bu listeyle ve `genc-akisi-metinler.md` ile yapılacak.

Sütunlar: **Dosya** · **Yer** · **Metin** · **Kime**.

## Denetime not

| Dosya | Yer | Sorun |
|---|---|---|
| `frontend/src/app/kayit/page.tsx` | Rol kartları "Gencim" / "Kurum adına", ad etiketi "Kurumun adı", açıklama "Kayıttan sonra doğrudan paneline geçersin." | Rehber § 4: "Genç yetenek olarak katılıyorum" / "Firma olarak katılıyorum"; firmaya "siz"; "kurum" → "firma". Mevcut metin, bu adımda değiştirilmedi |
| `frontend/src/app/tanimlama/page.tsx` | "Kurum bilgileri" başlığı ve altındaki "Kurum adınız…" cümlesi | "kurum" → "firma"; eski hesap dışında altında alan kalmıyor, başlık denetimde gözden geçirilsin |
| `frontend/src/components/ust-menu.tsx` | "Yeni ihtiyaç" | Sorun yok; "Firma profili" yanına eklendi |

## 2. adım — Firma kayıt formu ve profil

| Dosya | Yer | Metin | Kime |
|---|---|---|---|
| `components/firma-profil-alanlari.tsx` | Tür başlığı | Firma türü | firma |
| 〃 | Tür seçenekleri | Girişim · KOBİ · Kurumsal | firma |
| 〃 | Tür açıklaması | İş birliği ortağı ararken hangi tür firmalarla eşleşeceğinizi belirler. | firma |
| 〃 | Etiketler | Sektör · Şehir · Web sitesi · Çalışan sayısı · Kuruluş yılı · Kısa tanıtım · Adınız · Göreviniz | firma |
| 〃 | Bölüm başlığı | Firmanızı tanıtın (isteğe bağlı) | firma |
| 〃 | Yer tutucu | ornekfirma.com | firma |
| 〃 | Tanıtım notu | Bir-iki cümle; en çok 300 karakter. | firma |
| `lib/firma-profil.ts` | Form hataları | Firma türünü seçin. · Sektörü yazın. · Şehri seçin. · Web sitesi geçerli bir adres değil. · Kuruluş yılı 1900 ile {yıl} arasında olmalı. · Tanıtım en çok 300 karakter olmalı. | firma |
| 〃 | Panel bandı | Profilinizi tamamlayın: profilinizde eksik bilgi var ({alanlar}); KVKK aydınlatma metnini onaylamadınız. | firma |
| 〃 | Eksik alan adları | firma türü · sektör · şehir | firma |
| `app/kayit/page.tsx` | KVKK hatası (firma) | KVKK aydınlatma metnini onaylayın. | firma |
| `app/kurum/page.tsx` | Bant bağlantısı | Firma profiline git | firma |
| `app/kurum/profil/page.tsx` | Başlık | Firma profili | firma |
| 〃 | Giriş | Firmanızın temel bilgileri. İletişim e-postanız ({e-posta}) yalnızca karşılıklı ilgi oluşunca paylaşılır. | firma |
| 〃 | Etiket, hata | Firma adı · Firma adı boş olamaz. | firma |
| 〃 | Kaydedildi | Firma profiliniz kaydedildi. | firma |
| `components/ust-menu.tsx` | Menü | Firma profili | firma |
| `app/tanimlama/page.tsx` | Onay formu notu (profil tamsa) | Aranan şehir, adayın nerede olmasını istediğiniz yer. Çalışma modeli “Uzaktan” ise şehir filtresi uygulanmaz. | firma |
| `backend/app/core/firma_profili.py`, `schemas/auth.py` | 422 cümleleri | Kuruluş yılı 1900 ile {yıl} arasında olmalı · Tanıtım en çok 300 karakter olmalı · Firma kaydında firma bilgileri zorunlu · KVKK aydınlatma metni onaylanmalı | firma |

## 3. adım — İlan kapatma

| Dosya | Yer | Metin | Kime |
|---|---|---|---|
| `components/ilan-kapatma.tsx` | Düğme | İhtiyacı kapat | firma |
| 〃 | Onay sorusu | Bu ihtiyaç kapatılsın mı? Bekleyen adaylara “fırsat kapandı” bildirimi gider ve yeni aday aranmaz. Kapanan ihtiyaç tekrar açılmaz. | firma |
| 〃 | Neden başlığı | Neden kapatıyorsunuz? | firma |
| `lib/ilan.ts` | Nedenler | Platformda bulduk · Başka yoldan bulduk · Vazgeçtik | firma |
| `components/ilan-kapatma.tsx` | Not | Nedeni yalnızca program ekibi görür; adaylara gösterilmez. | firma |
| 〃 | Butonlar | Kapat · Kapatılıyor… · Vazgeç | firma |
| `app/kurum/page.tsx` | Kapalı ilan etiketi | Kapandı | firma |
| `app/girvak/page.tsx` | Bölüm | Kapanan ihtiyaçlar · "Firmaların ihtiyacı kapatırken seçtiği neden. Nedeni yalnızca siz görürsünüz." · Platformda bulundu · Başka yoldan bulundu · Vazgeçildi | GİRVAK |
| `app/servisler/ilgi.py` | Gence bildirim (mevcut, değişmedi) | {firma adı} tarafındaki fırsat kapandı. | genç |

Denetime not: firma ilanına aday firma da gelecek (7-8. adım); "bekleyen adaylara" ifadesi iki durumu da kapsıyor.
