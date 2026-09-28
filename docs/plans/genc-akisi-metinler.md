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
| `frontend/src/app/page.tsx` | "Altı problem, altı ajan", "Keşif Ajanı", "Tanımlama Ajanı'yla…" | "Ajan" terimi (tanıtım sayfası; jüri için bilinçli olabilir) |
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
| `backend/app/agents/dogrulama.py` | 409 cümleleri (arayüzde görünür) | "Bu kişiden yanıt zaten bekleniyor.", "Bu referans işin güncel hâli için zaten yanıt verdi." | genç |
| `backend/app/api/kart_duzenleme.py` | 404 cümlesi | "İş kalemi bulunamadı" | genç |

## 9. adım — İlgi durum makinesi (backend cümleleri; arayüz 10. adımda)

| Dosya | Bileşen / yer | Metin | Kime |
|---|---|---|---|
| `backend/app/api/eslestirme.py` | Bildirim (genç ilgi gösterdi) | "{genç adı} ihtiyacınızla ilgileniyor. Siz de ilgilenirseniz iletişim bilgileriniz karşılıklı paylaşılır." | firma |
| `backend/app/api/eslestirme.py` | Bildirim (karşılıklı ilgi) | "{firma adı} da seninle ilgileniyor; karşılıklı ilgi oluştu. İletişim bilgileriniz paylaşıldı ve iş birliği başladı." | genç |
| `backend/app/servisler/ilgi.py` | Bildirim (şimdilik değil / ihtiyaç kapandı) | "{firma adı} tarafındaki fırsat kapandı." | genç |
| `backend/app/agents/eslesme_durumu.py` | 409 (eşik altı) | "Bu fırsat için ilgi gösterilemiyor; uyumun yeterli değil." | genç |
| `backend/app/agents/eslesme_durumu.py` | 409 (kapalı ihtiyaç) | "Bu fırsat kapandı." | genç |
| `backend/app/servisler/eslestirme.py` | 409 (kapalı ihtiyaçta yeniden hesap) | "Bu ihtiyaç kapandı; yeni aday aranmıyor." | firma |
| `backend/app/agents/eslesme_durumu.py` | 409 cümlesi, yeni durum ve olay etiketleri | "…'ilgi iletildi, firmanın yanıtı bekleniyor' durumunda…", "…'kapandı' durumunda…"; "ilgi gösterilemez", "ilgi geri çekilemez", "kapatılamaz" | ikisi |

> **Denetime not:** 409 cümlesinin kalıbı ("Bu eşleşme şu an '…' durumunda; … .") Faz B'den; "eşleşme" kelimesi ve tırnaklı durum adı rehberdeki § 5.4 ("ne oldu + ne yapmalı") biçimine uymuyor, denetimde bakılsın. Mevcut "kurum ilgileniyor, gencin yanıtı bekleniyor" etiketinde "kurum" geçiyor (rehber: "firma"). "{firma adı} da" ekinde ünlü uyumu ("de/da") ada göre değişir; şimdilik sabit "da".
