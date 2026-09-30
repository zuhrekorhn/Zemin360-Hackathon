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

## 4. adım — Firma doğrulaması

| Dosya | Yer | Metin | Kime |
|---|---|---|---|
| `lib/firma-dogrulama.ts`, `components/dogrulanmis-firma.tsx` | İşaret | Doğrulanmış firma | herkes |
| `app/kurum/profil/page.tsx` | Doğrulanmamışsa | Doğrulama bekleniyor. Program ekibi firmanızı doğrulayınca adınızın yanında “Doğrulanmış firma” işareti görünür. Web sitenizi değiştirirseniz doğrulama yeniden yapılır. | firma |
| `backend/app/api/girvak.py` | Firmaya bildirim | Firmanız doğrulandı. Adınızın yanında artık “Doğrulanmış firma” işareti görünüyor. | firma |
| `components/firma-onaylari.tsx` | Bölüm | Onay bekleyen firmalar · "Sistemin ipucu e-posta uzantısıyla web sitesinin adresini karşılaştırır; siteye bağlanmaz. Kararı siz verirsiniz. Onaylanan firmanın adının yanında “Doğrulanmış firma” işareti görünür." · Boş: Onay bekleyen firma yok. | GİRVAK |
| 〃 | Butonlar | Onayla · Şimdilik değil | GİRVAK |
| `lib/firma-dogrulama.ts` | İpucu cümleleri | E-posta uzantısı ({alan}) web sitesiyle uyuşuyor. · …uyuşmuyor. · Herkese açık bir e-posta servisi kullanılmış ({alan}); uzantı firmayı göstermiyor. · Web sitesi yazılmamış; e-posta uzantısı karşılaştırılamadı. · Kayıtlı bir e-posta yok. | GİRVAK |

Denetime not: "Şimdilik değil" GİRVAK'ın düğmesi; firmaya hiçbir metin gitmiyor, profilinde "Doğrulama bekleniyor" kalıyor (rehber § 2.5, olumsuz haber nazik).

## 5a. adım — Firma kartı (tablo, okuma, düzenleme)

Arayüz 5b'de. Bu adımda yalnızca backend cümleleri:

| Dosya | Yer | Metin | Kime |
|---|---|---|---|
| `backend/app/api/firma_karti.py` | 404 | Firma kartınız henüz yok. | firma |
| `backend/app/core/firma_karti.py`, `schemas/firma_karti.py` | 422 | Firmanın ne yaptığı zorunlu · En az bir yetkinlik zorunlu · En çok 15 yetkinlik yazılabilir · Bir yetkinlik en çok 80 karakter olmalı · {Alan} en çok {n} karakter olmalı · Tanınmayan iş birliği türü | firma |
| `backend/app/core/firma_karti.py` | İş birliği türleri | Pilot uygulama · Tedarik · Ortak ürün · Yatırım · Diğer | firma |

Denetime not: "Bu alanlar boş bırakılamaz: ne_yapiyoruz" 422 cümlesi alan adını kod adıyla veriyor (genç profilindeki aynı cümle de öyle); arayüz formu göndermeden önce kendi cümlesini göstermeli.

## 5b. adım — Firma kartı sohbeti ve sayfası

| Dosya | Yer | Metin | Kime |
|---|---|---|---|
| `backend/app/agents/firma_karti.py` | Açılış | Firmanızın ne yaptığını birkaç cümleyle anlatın: hangi ürünü ya da hizmeti sunuyorsunuz, kimler için? | firma |
| 〃 | Zorunlu sorular | Firmanızın sunduğu ürün ya da hizmeti bir-iki cümleyle anlatır mısınız? Kimler için ve hangi sorunu çözüyor? · Firmanızın en güçlü olduğu alanlar neler? Kısa başlıklar yeterli, örneğin “talep tahmini” ya da “soğuk zincir lojistiği”. | firma |
| 〃 | Ek sorular | Bugüne kadar yaptığınız bir-iki işi ya da çalıştığınız müşteri türlerini anlatır mısınız? Bir sonuç varsa sayıyla yazabilirsiniz. · Nasıl bir firmayla, ne için iş birliği yapmak istersiniz? Örneğin bir pilot uygulama, tedarik ya da ortak ürün. | firma |
| `backend/app/api/firma_karti.py` | 409/422/503/429 | Firma kartınız zaten var; kart sayfasından düzenleyebilirsiniz. · Kartta firmanın ne yaptığı ve en az bir yetkinlik olmalı. · Kart sohbeti şu an hazır değil · {hız sınırı} Sohbetiniz kayıtlı. · Taslak hazır; sıradaki adım onay · Taslak henüz hazır değil | firma |
| `app/kurum/kart/page.tsx` | Başlık, giriş | Firma kartı · Firmanızın ne yaptığını anlatan kart. İş birliği ortağı arayan firmalar sizi bu kartla bulur. | firma |
| 〃 | Sohbet notu | Bu sohbet yapay zekâ desteğiyle ilerler. Kartınız siz onaylamadan kaydedilmez. Kayıtta verdiğiniz bilgiler tekrar sorulmaz. | firma |
| 〃 | Sohbet adı | Zemin360 | firma |
| 〃 | Taslak | Kartınızın taslağı · Sohbetten çıkan kart bu. Gözden geçirin, gerekirse düzeltin ve onaylayın. · Kartı onayla | firma |
| 〃 | Görünüm | Kartı düzenle · Yetkinlikler · Önceki işler · Aradığınız ortak · İş birliği türleri · Kartınız kaydedildi. · Kaydet · Vazgeç | firma |
| 〃 | Bekleme | Kartınız eşleştirmeye hazırlanıyor. Birkaç saniye sonra sayfayı yenileyerek görebilirsiniz. | firma |
| `components/firma-karti-formu.tsx` | Etiketler | Ne yapıyorsunuz? · Yetkinlikler · Önceki işleriniz · Nasıl bir ortak arıyorsunuz? · İş birliği türleri (isteğe bağlı) · Virgülle ayırın; en çok 15 tane. | firma |
| `lib/firma-karti.ts` | Form hataları | Firmanızın ne yaptığını yazın. · Açıklama en çok 1000 karakter olmalı. · En az bir yetkinlik yazın. · En çok 15 yetkinlik yazabilirsiniz. | firma |
| 〃, `app/kurum/page.tsx` | Panel çağrısı | Firma kartınızı oluşturun, diğer firmalar sizi bulabilsin. · Firma kartını oluştur | firma |
| `components/ust-menu.tsx` | Menü | Firma kartı | firma |

Denetime notlar:
- Sohbet balonundaki bekleme metni "Ajan düşünüyor…" ortak bileşenden geliyor (`components/sohbet.tsx`); firma kartı sohbetinde de görünüyor. Metin denetiminde değiştirilmeli.
- "Kartınız eşleştirmeye hazırlanıyor": "eşleştirme" mevcut firma metinlerinde de geçiyor; rehberde terim olarak yok, denetimde bakılsın.

## 6. adım — Ortak ilanı ve iki kapı

| Dosya | Yer | Metin | Kime |
|---|---|---|---|
| `lib/ilan.ts`, `app/kurum/page.tsx` | Kapılar | Genç yetenek bul · "Bir ihtiyacınızı tanımlayın, ona uygun genç yetenekleri görün." · İş birliği ortağı bul · "Bir iş için ortak arayın: girişim, KOBİ ya da kurumsal firmalar önerilsin." | firma |
| 〃 | İlan etiketi | İş birliği ortağı | firma |
| `backend/app/agents/tanimlama.py` | Ortak açılış | Merhaba! Bir iş birliği ortağıyla çözmek istediğiniz problemi anlatın: bugün ne yaşıyorsunuz ve ortaktan ne bekliyorsunuz? | firma |
| 〃 | Ortak soruları | Ortak firma işe başladığında hangi sorunu çözecek? Bugün o iş nasıl yürüyor ve nerede tıkanıyor? · Bu iş birliği bittiğinde neye bakıp “oldu” diyeceksiniz? Sayıyla ifade edebilir misiniz: bir oran, bir süre ya da bir adet? | firma |
| `app/tanimlama/page.tsx` | Ortak giriş | Kısa bir sohbet. Bir iş birliği ortağıyla çözmek istediğiniz ihtiyacı ölçülebilir bir karta çevireceğiz; bu karta uyan firmalar önerilecek. Kart siz onaylamadan kaydedilmez. | firma |
| 〃 | Ortak onay formu | Aradığınız firma türleri (hiçbiri seçilmezse hepsi) · İş birliği türü · Belirtmek istemiyorum · Fark etmez · "Aranan şehir yalnızca ortağın belirli bir şehirde olması şartsa seçilir; seçilmezse şehir fark etmez." | firma |
| 〃 | Taslak kartı | Aranan firma türleri · Hepsi · İş birliği türü | firma |
| 〃 | Kayıtlı ortak ilanı | Artık firma kartlarıyla eşleştirilebilir. | firma |

Denetime not: Tanımlama sayfasının başlığı ve sohbet adı hâlâ "Tanımlama Ajanı" (mevcut metin); ortak kapısında da görünüyor.

## 7a. adım — Firma–firma eşleştirme (backend)

| Dosya | Yer | Metin | Kime |
|---|---|---|---|
| `backend/app/api/eslestirme.py` | 409 (geçici, 8. adımda kalkar) | Firmalarla ilgi ve iletişim yakında açılacak; şimdilik öneriyi görebilirsiniz. | firma |
| `backend/app/agents/eslestirme.py` | Gerekçe istemi | Firma adayı için "Neden uygun?" metni; ilanı açan firmaya hitaben, aday firmadan üçüncü şahısla (genç gerekçesindeki bilinen sınırın aynısı: aday firma da aynı metni görecek) | firma |

## 7b. adım — Öneriler sayfasında firma adayları

| Dosya | Yer | Metin | Kime |
|---|---|---|---|
| `app/kurum/oneriler/page.tsx` | Ortak ilanı girişi | İlanınıza uyan firmalar, uyumuyla ve neden önerildikleriyle birlikte. Karar sizin. | firma |
| 〃 | Ortak ilanı boş durum | Şu an ilanınıza yeterince uyan bir firma yok. Firmalar kartlarını oluşturdukça yeni öneriler çıkabilir. · İlanınızdaki problemi ve başarı kriterini netleştirmek de yardımcı olur. | firma |
| 〃 | Firma adayı kartı | Ne yapıyor? · Yetkinlikler · Önceki işler · İş birliği türleri · {n} tamamlanan iş birliği · "Bu öneri için açıklama henüz hazır değil. Uyum ve sıralama bundan etkilenmiyor; “Yeniden hesapla” ile tekrar denenir." | firma |
| 〃 | Geçici not (8. adımda kalkar) | Firmalarla ilgi ve iletişim yakında açılacak; şimdilik öneriyi görebilirsiniz. | firma |
| `app/kurum/page.tsx` | Önerilerim satırı (firma adayı) | Firma | firma |

Denetime not: genç adayı kartındaki mevcut metinler ("Karar senin.", "tamamlanmış pilot" rozeti, eşik cümlesi) değiştirilmedi; firma adayı kartında rehbere uygun karşılıkları kullanıldı ("Karar sizin.", "tamamlanan iş birliği", eşik yok).

## 8a. adım — Firmalar arası ilgi (backend)

Bildirimler (firmaya "siz"):

| Olay | Kime | Metin |
|---|---|---|
| Aday firma ilgi gösterdi | ilan sahibi | {aday firma} iş birliği ilanınızla ilgileniyor. Siz de ilgilenirseniz iletişim bilgileriniz karşılıklı paylaşılır. |
| İlan sahibi ilk ilgiyi gösterdi | aday firma | {ilan firması}, iş birliği ilanı için firmanızla ilgileniyor. Kabul ederseniz e-posta adresleriniz paylaşılır. |
| Karşılıklı ilgi | aday firma | {ilan firması} ilginize karşılık verdi. İletişim bilgileriniz paylaşıldı ve iş birliği başladı. |
| Aday firma kabul etti | ilan sahibi | {aday firma} ilginizi kabul etti; iletişim bilgileri açıldı. |
| Aday firma kabul etmedi | ilan sahibi | {aday firma} bu eşleşmeyi şu an kabul etmedi. |
| Şimdilik değil / ilan kapandı | aday firma | {ilan firması} tarafındaki fırsat kapandı. (mevcut metin) |

7a'daki geçici 409 cümlesi ("Firmalarla ilgi ve iletişim yakında açılacak…") kaldırıldı.

Denetime not: genç tarafındaki kabul bildirimi "{genç} ilgini kabul etti" firmaya "sen" diyor (mevcut metin); firma adayındaki karşılığı "ilginizi".

## 8b-8c. adım — Firmalar arası ilgi ve iş birliği (arayüz)

| Dosya | Yer | Metin | Kime |
|---|---|---|---|
| `components/firma-firsatlari.tsx` | Bölüm | Size uygun iş birliği fırsatları · "Firma kartınıza uyan iş birliği ilanları. İlgilendiğiniz ilanı açan firmaya bildirebilirsiniz; o da ilgilenirse iletişim bilgileriniz paylaşılır." | firma |
| 〃 | Boş durum | Şu an kartınıza uyan bir ilan yok. Yeni ilanlar açıldıkça burada görünür. | firma |
| 〃 | Bölüm | Size gelen ilgiler · "Bu firmalar iş birliği ilanları için sizinle ilgileniyor. Kabul ederseniz iletişim bilgileriniz paylaşılır ve iş birliği başlar." | firma |
| 〃 | Bölüm | İlgilerimiz | firma |
| 〃 | Butonlar | İlgileniyoruz · İlgimizi ilet · İletiliyor… · Vazgeç · Kabul et · Şimdilik değil · İlgimizi geri çek · İş birliğine gidin | firma |
| `lib/firma-ilgi.ts` | Onay | İlanı açan firma da ilgilenirse e-posta adresiniz, size ayrıca sorulmadan o firmayla paylaşılır. (+ mevcut "Bunu onaylıyorum") | firma |
| 〃 | Aday firma durum etiketleri | Size uygun · İlginiz iletildi · Firma sizinle ilgileniyor · Karşılıklı ilgi · Kapandı | firma |
| `app/kurum/oneriler/page.tsx` | Firma adayı eylemleri | İlgileniyorum · Şimdilik değil · "Firmaya bildirilir; kabul ederse iş birliği açılır ve e-postalar paylaşılır." · "Firmanın yanıtı bekleniyor; kabul ederse iletişim bilgileri açılır." | firma |
| `components/panel.tsx` | İletişim etiketi | Ortak firmanın e-postası | firma |
| `app/kurum/page.tsx`, `app/isbirligi/[id]/page.tsx` | Rol alanı yoksa | İş birliği ortağı | firma |
| `backend/app/agents/takip.py` | Firma planı istemi | "İki firma arasında…", "İki firmanın ayrı ekipleri olduğunu hesaba kat…" (LLM istemi; kullanıcıya görünen adım metinlerini üretir) | — |

Denetime notlar:
- Rehber § 5.9'da "aday firma" sütunu yok; aday firmanın etiketleri gencin sütununun "siz" hâli olarak yazıldı. Rehbere sütun eklenmeli.
- Firmanın gördüğü "Kurumun e-postası" (mevcut `IletisimSatiri` etiketi) → "Firmanın e-postası".
- Firma panelindeki mevcut "İş birliklerim" boş durumu gence göre yazılı ("Bir genç ilgini kabul ettiğinde…"); firmaya "sen" ve iki tür ortağı kapsamıyor.

## 9. adım — GİRVAK kırılımı ve demo verisi

| Dosya | Yer | Metin | Kime |
|---|---|---|---|
| `app/girvak/page.tsx` | Bölüm | Genç–firma ve firma–firma · "Yukarıdaki toplamların eşleşme türüne göre dağılımı. Firma–firma, bir firmanın iş birliği ortağı aradığı ilanlardan çıkan eşleşmeler." | GİRVAK |
| 〃 | Sayı etiketleri | Genç–firma karşılıklı ilgi · Genç–firma iş birliği · Genç–firma tamamlanan · Firma–firma öneri · Firma–firma karşılıklı ilgi · Firma–firma iş birliği · Firma–firma tamamlanan | GİRVAK |
| `backend/scripts/demo_hesaplari.py` | Demo firmaları | Tazele Analitik (girişim) · Anadolu Market Zinciri A.Ş. (kurumsal); kart, ilan ve tanıtım metinleri demo içeriği | — |

## Toplu metin denetimi (30 Eyl): kapandı

Rehbere (`docs/icerik-rehberi.md`) göre bütün ekranlar ve kullanıcıya dönen backend
cümleleri tarandı. Yukarıdaki "Denetime not" satırları ve adım tablolarındaki
bilinen uyumsuzluklar bu turda düzeltildi; tablolardaki eski metinler tarih kaydı
olarak duruyor. Son onay Zühre'de (rehber § 8).

**Genel kurallar, uygulandığı yer:**

| Kural | Nasıl uygulandı |
|---|---|
| "Ajan" gösterilmez (§ 4) | Sayfa başlıkları "Yetenek kartını oluştur" / "İhtiyacınızı tanımlayın"; sohbet balonunun adı "Zemin360"; iş birliği sayfasında "Durum özeti", "Plan önerisi al", "Yeni plan önerisi al"; GİRVAK'ta "Son hatırlatmalar" |
| Yapay zekâ bir kez söylenir (§ 9.5) | Keşif, Tanımlama ve firma kartı sohbetinin açıklamasında; kart sayfasında "Çalışmaların" başlığının altında güven göstergesi notu |
| Hitap (§ 3) | Ortak ekranlar bakan hesaba göre: `lib/hitap.ts` (`hitapRolden`, `hitapla`) ve `useHitap()`; iş birliği sayfası, sohbet alanı, bildirimler boş durumu, takip ve canlılık bildirimleri (`siz_mi`) |
| "kurum" → "firma", "ilan" → "ihtiyaç / fırsat" | Kayıt (rol kartları § 9.4, "Firmanın adı"), KVKK maddeleri, profil bandı, panel ve öneri ekranları, GİRVAK sayaçları |
| "çalışma" (§ 9.1) | Kart sayfası "Çalışmaların" / "Çalışmaları", "Çalışma ekle", Keşif taslağı, referans sayfası ("Anlatılan çalışma", "Çalışmanın sahibi") |
| Güven göstergesi başlıkları | Kanıt · Sonuç · Rol · Referans; rozet "tamamlanan iş birliği" |
| Skor / eşik gösterilmez | "%72 uyum"; eşik cümleleri "yeterince uyan" diliyle; GİRVAK'ta "hareketsizlik süresi" |
| Onaylar sayfa içinde (§ 5.6) | `components/onay-alani.tsx`; çalışma silme ve gösterge sıfırlama, fırsattan ilgiyi geri çekme, "Şimdilik değil", yeni plan önerisi. `window.confirm` kalmadı |
| Uzun tire yok (§ 6) | Cümlelerden kaldırıldı. Boş değer hücrelerindeki tek başına "—" işareti metin değil, bırakıldı |
| Yer tutucu "ör." ile | Kalan iki yer tutucu düzeltildi |
| Hatalar (§ 5.4) | İngilizce şema metinleri gösterilmez (`lib/ayrinti.ts`); ağ hatası "Şu an bağlantı kuramadık."; 401/403/404/409/422 için cümleler (`lib/hata.ts`); backend'de boş alan cümleleri tek yerde (`app/core/alan_adlari.py`) |
| LLM'in yazdığı kullanıcı metni | Tüm istemlere `app/core/kullanici_dili.py` › `KULLANICI_DILI_KURALLARI` eklendi |

**Bilinen sınırlar (bilinçli bırakıldı):**

- "Neden uygun?" açıklaması firmaya hitaben 3. şahısla yazılıyor ve gence de aynen gösteriliyor (§ 9.2).
- "Pilot uygulama" firma kartında bir iş birliği türünün adı; rehber yalnızca tek başına "pilot"u yasaklıyor.
- Kart sayfasındaki "kart no · sürüm" satırı teknik ama kullanıcıyı yanıltmıyor; kaldırılması ayrıca konuşulabilir.
