# Genç akışı — yeni arayüz metinleri (toplu denetim listesi)

Plan § 0, karar 15: yazılan ve değişen her kullanıcı metni burada. Kurallar
`docs/icerik-rehberi.md`'de (28 Eyl'de onaylandı). Toplu denetim genç akışı
bittikten sonra bu listeyle yapılacak.

Sütunlar: **Dosya** · **Bileşen / yer** · **Metin** · **Kime** (genç / kurum / herkes).

## Denetime not: mevcut ekranlarda düzeltilecekler

Karar 15 gereği şimdi değiştirilmiyor; toplu denetimde ele alınacak.

| Dosya | Yer | Sorun |
|---|---|---|
| `frontend/src/app/kurum/page.tsx` | Boş durum: "Henüz ihtiyaç kartın yok. Tanımlama Ajanı'yla kısa bir sohbet yap…" | Kuruma "sen"; "Ajan" terimi |
| `frontend/src/app/kurum/oneriler/page.tsx` | "Henüz bir ihtiyaç kartın yok. Eşleştirme, Tanımlama Ajanı'yla…" | Kuruma "sen"; "Ajan" terimi |
| `frontend/src/app/tanimlama/page.tsx` | Sayfa geneli | Kuruma "sen"/"siz" karışık olabilir; taranmalı |
| `frontend/src/app/genc/page.tsx` | Boş durum: "…Keşif Ajanı'yla kısa bir sohbet yap…" | "Ajan" terimi |
| `frontend/src/app/kesif/page.tsx` | Başlık ve sohbet adı "Keşif Ajanı" | "Ajan" terimi |
| `frontend/src/app/kart/[id]/page.tsx` | "Doğrulama Ajanı kanıtı dört ayrı başlıkta puanlar…" | "Ajan" terimi |
| `frontend/src/app/isbirligi/[id]/page.tsx` | "Takip Ajanı'nın özeti", "Ajandan plan iste", "Ajandan yeniden öner", "Ajan yeni bir plan önerecek…" | "Ajan" terimi |
| `frontend/src/app/girvak/page.tsx` | "…Canlılık Ajanı'nın son hatırlatmaları…" | "Ajan" terimi (GİRVAK paneli; belki kalabilir) |
| ~~`frontend/src/app/page.tsx`~~ | ~~"Altı problem, altı ajan", "Keşif Ajanı", "Tanımlama Ajanı'yla…"~~ | **Kapandı (30 Eyl):** karşılama sayfası yeniden yazıldı, ajan metinleri kalktı; aşağıda "Karşılama sayfası" |
| `frontend/src/app/kurum/page.tsx` | "· eşleştirmeye hazır değil" | Terim yok ama nedeni söylemiyor; denetimde bakılsın |

## 7. adım — Kart düzenleme

> **Rehberden önce yazıldı**; denetimde rehbere göre düzeltilecek. Bilinen uyumsuzluklar:
> "iş" / "iş kalemi" → "çalışma" ("İş ekle" → "Çalışma ekle", "İşi ekle", "Bu kartta henüz iş yok", "Değişen işin kanıtı", "Bu iş daha önce değerlendirildi", "Bu yanıt işin önceki hâline…"); tür seçeneği "İş" → "İş deneyimi"; "Senin payın" ve "Sonuç (sayıyla)" etiketleri (§ 5.3 isim öbeği, sorun yok ama "Rol" başlığıyla tutarlılık bakılsın); bekleme notuna "Sayfayı yenileyerek görebilirsin." eklenmeli (§ 5.8); silme onayı "kartından silinsin mi" → "silinsin mi" (§ 5.6); "Kaydedildi." tek başına. Yer tutucularda "ör." var, uzun tire yok.

| Dosya | Bileşen / yer | Metin | Kime |
|---|---|---|---|
| `frontend/src/components/kart-duzenleme.tsx` | Kayıt sonrası not | "Kaydedildi. Değişen işin kanıtı yeniden değerlendiriliyor; güven göstergesi birkaç dakika içinde güncellenir." | genç |
| `frontend/src/components/kart-duzenleme.tsx` | Sıfırlama onayı (confirm) | "Bu iş daha önce değerlendirildi. İçeriği ya da linki değişirse güven göstergesi sıfırlanır ve kanıt yeniden değerlendirilir; önceki referans yanıtları geçmiş olarak kalır. Devam edilsin mi?" | genç |
| `frontend/src/components/kart-duzenleme.tsx` | Silme onayı (confirm) | "“{başlık}” kartından silinsin mi? Kanıtı ve referans istekleri de silinir." | genç |
| `frontend/src/components/kart-duzenleme.tsx` | KartAlanlariFormu etiketleri | "Rol / alan", "Deneyim", "Sektör ilgisi", "Araçlar ve yöntemler", "Sertifikalar", "Diller", yer tutucu "Virgülle ayır"; düğmeler "Kaydet", "Kaydediliyor…", "Vazgeç" | genç |
| `frontend/src/components/kart-duzenleme.tsx` | IsKalemiEylemleri | "Düzenle", "Sil" | genç |
| `frontend/src/components/kart-duzenleme.tsx` | IsKalemiEkleFormu | "Referans kişi eklemek için işi kaydettikten sonra kanıt bölümünü kullan."; düğmeler "İşi ekle", "Ekleniyor…", "Vazgeç" | genç |
| `frontend/src/components/is-kalemi-formu.tsx` | Alan etiketleri (6. adımda yazıldı, burada da kullanılıyor) | "Türü", "Belirtilmedi", "Başlık", "Ne yaptın, ne ortaya çıktı?", "Sonuç (sayıyla)", "Senin payın", "Kanıt linki", "Referans kişinin e-postası"; yer tutucular "ör. 400 kitap ve 120 üye takip ediliyor", "ör. backend'i ben yazdım", "github.com/… veya bir demo adresi", "işini doğrulayabilecek biri" | genç |
| `frontend/src/lib/kart-duzenleme.ts` | Referans satırı notu | "Bu yanıt işin önceki hâline verildi; güven göstergesine girmiyor." | genç |
| `frontend/src/components/kanit.tsx` | Referans satırı düğmesi | "Referansı yeniden iste" | genç |
| `frontend/src/app/kart/[id]/page.tsx` | Kart sayfası | "Kartı düzenle", "İş ekle", "Kaydedildi.", "Bu kartta henüz iş yok. Aşağıdan ekleyebilirsin." (sahibi) / "Bu kartta somut çıktı yok." (diğerleri); satırlar "Sertifikalar", "Diller" | genç / herkes |
| `backend/app/agents/dogrulama/kurallar.py`, `referans_durumu.py` | 409 cümleleri (arayüzde görünür) | "Bu kişiden yanıt zaten bekleniyor.", "Bu referans işin güncel hâli için zaten yanıt verdi." | genç |
| `backend/app/api/kart_duzenleme.py` | 404 cümlesi | "İş kalemi bulunamadı" | genç |

## 9. adım — İlgi durum makinesi (backend cümleleri; arayüz 10. adımda)

| Dosya | Bileşen / yer | Metin | Kime |
|---|---|---|---|
| `backend/app/api/eslestirme.py` | Bildirim (genç ilgi gösterdi) | "{genç adı} ihtiyacınızla ilgileniyor. Siz de ilgilenirseniz iletişim bilgileriniz karşılıklı paylaşılır." | firma |
| `backend/app/api/eslestirme.py` | Bildirim (karşılıklı ilgi) | "{firma adı} ilgine karşılık verdi. İletişim bilgileriniz paylaşıldı ve iş birliği başladı." (10. adımda düzeltildi: adın ardındaki "da" eki ünlü uyumu yüzünden kaldırıldı) | genç |
| `backend/app/servisler/ilgi.py` | Bildirim (şimdilik değil / ihtiyaç kapandı) | "{firma adı} tarafındaki fırsat kapandı." | genç |
| `backend/app/agents/eslesme_durumu.py` | 409 (eşik altı) | "Bu fırsat için ilgi gösterilemiyor; uyumun yeterli değil." | genç |
| `backend/app/agents/eslesme_durumu.py` | 409 (kapalı ihtiyaç) | "Bu fırsat kapandı." | genç |
| `backend/app/servisler/eslestirme.py` | 409 (kapalı ihtiyaçta yeniden hesap) | "Bu ihtiyaç kapandı; yeni aday aranmıyor." | firma |
| `backend/app/agents/eslesme_durumu.py` | 409 cümlesi, yeni durum ve olay etiketleri | "…'ilgi iletildi, firmanın yanıtı bekleniyor' durumunda…", "…'kapandı' durumunda…"; "ilgi gösterilemez", "ilgi geri çekilemez", "kapatılamaz" | ikisi |

> **Denetime not:** 409 cümlesinin kalıbı ("Bu eşleşme şu an '…' durumunda; … .") Faz B'den; "eşleşme" kelimesi ve tırnaklı durum adı rehberdeki § 5.4 ("ne oldu + ne yapmalı") biçimine uymuyor, denetimde bakılsın. Mevcut "kurum ilgileniyor, gencin yanıtı bekleniyor" etiketinde "kurum" geçiyor (rehber: "firma"). Ad + ek taraması (10. adım): backend bildirimlerinde adın ardına ek gelen başka metin yok; "{ad} ile" kalıplarında "ile" ayrı kelime, ünlü uyumundan etkilenmez.

## 10. adım — Genç ana sayfası ve firma tarafı

| Dosya | Bileşen / yer | Metin | Kime |
|---|---|---|---|
| `backend/app/agents/guclendirme.py` | "Kartını güçlendir" satırı | "Bu çalışmaya kanıt eklersen {n} fırsatta öne çıkabilirsin." / "Kanıt eklemek, yeni fırsatlarda kartını güçlendirir." | genç |
| `frontend/src/lib/ilgi.ts` | Durum etiketleri (rehber § 5.9 birebir) | Genç: "Sana uygun", "İlgin iletildi", "Firma seninle ilgileniyor", "Karşılıklı ilgi", "Kapandı". Firma: "Aday", "İlgi gösterdi", "Yanıt bekleniyor", "Karşılıklı ilgi", "Kapandı". Bilinmeyen kod: "Durumu güncelleniyor" | ikisi |
| `frontend/src/lib/ilgi.ts` | Açıklama başlığı; uyum | "Neden uygun?"; "%{n} uyum" | ikisi |
| `frontend/src/lib/ilgi.ts` | İletişim onayı (İlgileniyorum'dan sonra açılan alan) | "Firma da ilgilenirse e-posta adresin, sana ayrıca sorulmadan firmayla paylaşılır." · onay kutusu "Bunu onaylıyorum" | genç |
| `frontend/src/components/firsatlar.tsx` | Fırsat kartı | "İlgileniyorum", "İlgimi ilet", "İletiliyor…", "Vazgeç", "Başarı ölçütü: …", "Açıklama henüz hazır değil." | genç |
| `frontend/src/components/firsatlar.tsx` | İlgi satırı | "İlgimi geri çek", "İş birliğine git"; onay (confirm) "{firma adı} fırsatına gösterdiğin ilgi geri çekilsin mi?" | genç |
| `frontend/src/app/genc/page.tsx` | "Sana uygun fırsatlar" bölümü | Başlık; açıklama "Kartına uyan firma ihtiyaçları. İlgilendiğin fırsatı firmaya bildirebilirsin; firma da ilgilenirse iletişim bilgileriniz paylaşılır."; boş durum "Şu an sana uygun bir fırsat yok. Kanıt eklemek ve kartını güncel tutmak, yeni fırsatlarda öne çıkmanı sağlar." [Kartına git] | genç |
| `frontend/src/app/genc/page.tsx` | "Kartını güçlendir" bölümü | Başlık; açıklama "Kanıt eklediğin çalışmalar güven göstergeni güçlendirir."; düğme "Kanıt ekle" | genç |
| `frontend/src/app/genc/page.tsx` | "İlgilerim" bölümü | Başlık; açıklama "İlgi gösterdiğin fırsatlar. Firma yanıt verene kadar ilgini geri çekebilirsin." | genç |
| `frontend/src/app/genc/page.tsx` | "Bana gelen ilgiler" durumları (not 4 gereği değişti) | "Kabul ettin, iş birliği açıldı" → "Karşılıklı ilgi"; "Reddettin" → "Kapandı" | genç |
| `frontend/src/app/kurum/oneriler/page.tsx` | İlgi gösterenler bölümü | Başlık "İlgi gösterenler", "Adaylar"; açıklama "Bu adaylar ihtiyacınızla ilgilendiklerini bildirdi. Siz de ilgilenirseniz iletişim bilgileriniz karşılıklı paylaşılır ve iş birliği başlar." | firma |
| `frontend/src/app/kurum/oneriler/page.tsx` | Aday kartı | Rozet "İlgi gösterdi"; düğmeler "İlgileniyorum", "Şimdilik değil"; yardım "İlgilenirseniz iletişim bilgileriniz paylaşılır ve iş birliği başlar."; "İş birliğine gidin"; durum açıklaması "Bu aday için süreç kapandı."; başlık "Neden eşleşti" → "Neden uygun?" (not 4) | firma |
| `frontend/src/app/kurum/oneriler/page.tsx` | "Şimdilik değil" onayı (confirm) | "{genç adı} için “Şimdilik değil” demek istiyor musunuz? Adaya bu fırsatın kapandığı bildirilir; neden yazılmaz." | firma |
| `frontend/src/app/kurum/oneriler/page.tsx`, `frontend/src/app/kurum/page.tsx` | Durum etiketleri (not 4 gereği değişti) | "Önerildi" → "Aday", "İlgini bildirdin"/"Gencin yanıtı bekleniyor" → "Yanıt bekleniyor", "Kabul edildi(, iş birliği açıldı)" → "Karşılıklı ilgi", "Aday şu an kabul etmedi" → "Kapandı" | firma |
| `frontend/src/app/tanimlama/page.tsx` | Onay formu notu (karar 1) | "Onaylanan ihtiyaç, eşleşen adaylara gösterilir." | firma |

> **Denetime not (10. adım):** Onay pencereleri (`window.confirm`) tarayıcının kendi düğmelerini ("Tamam/İptal") gösteriyor; rehber § 5.6 "Sil / Vazgeç" gibi eylem adı istiyor, bunun için özel bir onay bileşeni gerekir (mevcut ekranlarda da aynı). Firma öneriler sayfasında "Adaylar" / "İlgi gösterenler" dışındaki mevcut metinler ("Eşleştirme önerileri", "skoruyla", "Karar senin", "Yeniden hesapla", eşik açıklaması "%40 … eşik değerini") rehbere uymuyor ("skor", "eşik", "sen"); dokunulmadı.

## 11. adım — Canlılık: yanıtsız genç ilgisi

| Dosya | Bileşen / yer | Metin | Kime |
|---|---|---|---|
| `backend/app/agents/canlilik.py` | Hatırlatma (şablon, 5 gün) | "{genç adı} {n} gündür ihtiyacınızla ilgili yanıtınızı bekliyor. İlgileniyorsanız karşılıklı ilgiyi başlatabilir ya da “Şimdilik değil” diyebilirsiniz." (7. günde "bir haftadır") | firma |
| `frontend/src/lib/canlilik.ts` | GİRVAK paneli tür etiketi | "Yanıtsız genç ilgisi" | GİRVAK |

> **Denetime not (11. adım):** Canlılık'ın kişiselleştirme istemi (`KISISEL_TALIMAT`) her alıcıya "sen" diye hitap ettiriyor; mevcut firma hatırlatmaları (`oneri_bekliyor`, `ilgi_yanitsiz_2` firma kısmı, `plan_onaysiz`, `isbirligi_hareketsiz`, `adim_gecikti` firmaya gidenleri) ve şablonları da "sen" kullanıyor ("İhtiyaç kartın için…", "…bakabilirsin"). Rehber firmaya "siz" istiyor: denetimde istem alıcıya göre hitap seçecek biçimde düzeltilmeli, şablonlar ayrılmalı. Yeni tür bu yüzden yalnızca şablonla gidiyor.

## Karşılama sayfası (30 Eyl)

Kaynak: `docs/design/landing/LANDING_HANDOFF.md` (v2), metinler rehbere göre orada yazıldı ve birebir kullanıldı. Bütün metinler tek dosyada: `frontend/src/content/landing.ts` (tek tek listelenmedi, dosyanın kendisi liste). Hitap: ortak bölümler hitapsız; "Nasıl çalışır" genç sekmesi "sen", firma sekmesi "siz".

| Dosya | Bileşen / yer | Metin | Kime |
|---|---|---|---|
| `frontend/src/content/landing.ts` | Menü, hero, örnek sohbet, sorun bandı, nasıl çalışır, "Neden uygun?" örneği, süreç, güven, kapanış, altbilgi | Brief v2 § 3.1–3.9 | herkes (sekmeler genç / firma) |
| `frontend/src/components/karsilama/menu.tsx` | Mobil menü düğmesinin açıkken etiketi (brief'te yok, ekran okuyucu için) | "Menüyü kapat" | herkes |

> **Denetime not:** "Değerlendirme nasıl yapılıyor?", "Gizlilik" ve "İletişim" bağlantıları brief gereği şimdilik `#`. KVKK bağlantıları mevcut `/kvkk` sayfasına gidiyor. Logo yerleri boş kutu; gerçek logolar eklenince doldurulacak.

## Sayfa kabuğu ve menü (30 Eyl)

| Dosya | Bileşen / yer | Metin | Kime |
|---|---|---|---|
| `frontend/src/components/ust-menu.tsx` | Girişsiz menü (iç sayfalar) | "Giriş" → "Giriş yap", "Kayıt" → "Kayıt ol" (karşılama menüsüyle aynı; rehber § 2.7 aynı eylem aynı ad) | herkes |
| `frontend/src/components/ust-menu.tsx` | Mobil bildirim zili (ekran okuyucu) | "Bildirimler" · okunmamış varsa "Bildirimler, {n} okunmamış" | genç / firma |
| `frontend/src/components/menu-kabugu.tsx` | Katlanır menü düğmesi (ekran okuyucu) | "Menüyü aç" / "Menüyü kapat" | herkes |

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

## Doğrulama adım 11 — kötüye kullanım işaretleri (5 Eki)

Kalemin etiketi ve itirazı (gence "sen"); kuyruk satırları GİRVAK'a ("siz" gerektiren cümle yok, olgu cümleleri).

| Yer | Metin |
|---|---|
| Kalem etiketi | "Doğrulanamadı" |
| Etiket açıklaması | "GİRVAK bu çalışmayı inceledi ve şimdilik doğrulayamadı. Güven göstergen bu yüzden değişmedi; karara aşağıdan itiraz edebilirsin." |
| GİRVAK notu | "GİRVAK’ın notu: …" |
| İtiraz düğmesi (karar varken) | "Karara itiraz et"; yardım: "GİRVAK’ın yeniden bakmasını isteyebilirsin." |
| İtiraz formu yardımı (karar varken) | "Neyin gözden kaçtığını yaz; itirazın GİRVAK’a gider ve sonucu sana bildirilir." |
| İtiraz iletildi | "İtirazın GİRVAK'a iletildi; inceleyip sonucu sana bildirecek. Çalışmanı ya da kanıtını değiştirirsen yeniden değerlendirilir." |
| KVKK (ne için) | "Kötüye kullanımı fark etmek: referans istediğinde ve referansın yanıt verdiğinde IP adresinin ve tarayıcı bilgisinin geri çevrilemez bir özeti 90 gün saklanır; ham adres saklanmaz. Şüpheli bir durum GİRVAK'ın incelemesine gider, puanını kendiliğinden değiştirmez." |
| KVKK (hizmet sağlayıcı) | "Google Cloud Vision: tasarım ya da fotoğraf alanındaysan, yüklediğin görselin küçültülmüş bir kopyası internette başka bir sayfada yayımlanmış mı diye aranabilir." |
| GİRVAK kuyruğu | Aynı çalışma / dosya / görsel başka hesapta, şüpheli referans yanıtı, belge tutarsız, kanıt çelişiyor satırları (`lib/inceleme.ts`) |

## Doğrulama adım 12 — süreklilik ve ölçüm (5 Eki)

| Yer | Metin |
|---|---|
| Bildirim `kanit_curudu` (gence "sen") | "“{çalışma başlığı}” çalışmandaki kanıt linki art arda üç kontrolde açılmadı; silinmiş ya da gizlenmiş olabilir. Kanıt başlığı şimdilik boş. Linki düzeltir ya da yeni bir kanıt eklersen gösterge yeniden hesaplanır." (`app/servisler/dogrulama/curume.py`) |
