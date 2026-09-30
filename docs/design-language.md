# Tasarım Dili

## Marka Karakteri

İki farklı kullanıcı kitlesi var: genç yetenekler (18-30 yaş, sıcak/davetkâr bir şey ister) ve her sektörden kurum temsilcisi (ciddi/güvenilir bir şey ister). Tasarım ikisini aynı anda karşılamalı — ne bir kreş uygulaması gibi ne bir banka dashboard'u gibi.

Yön: **"kök"** metaforu — doğrulanmış güven, büyüyen bir ağ, kök salma. Genel AI/startup klişelerinden (krem + terracotta `#D97757`, siyah + neon vurgu, herkeste aynı SaaS kart kiti) bilinçli olarak uzak duruyoruz.

## Renk Paleti

| Rol | Hex | Kullanım |
|---|---|---|
| Zemin | `#F3F4EE` | Sayfa arka planı |
| Ana (koyu) | `#1E3A2F` | Başlıklar, koyu yüzeyler |
| Vurgu (CTA) | `#B8823C` | Butonlar, önemli aksiyonlar |
| Bağlantı rengi | `#4A7A6D` | Eşleşme/bağlantı anları, linkler |
| Metin | `#16211B` | Gövde metni |
| Çizgi/kenar | `#D8D6C9` | Hairline çizgiler, kenarlıklar |

## Tipografi

- **Başlıklar:** Fraunces (karakterli, editoryal serif)
- **Gövde/form/arayüz:** IBM Plex Sans (temiz humanist sans)
- **Zorunlu kontrol:** İki fontun da Türkçe karakterleri (ş, ğ, ı, ç, ö, ü) doğru render ettiğini kurulumda doğrula.

## Yerleşim İlkeleri

- Hero alanı jenerik "başlık + buton + gradyan" olmasın — gerçek bir sohbet anını göstersin (Keşif Ajanı'nın sorduğu bir soru + bir "neden eşleşti" gerekçe kartı örneği).
- **İki farklı görsel dil, kasıtlı:** sohbet panelleri yuvarlak/sıcak (chat-bubble hissi); doğrulama/skor gösterimleri daha az yuvarlak, hairline çizgili, "resmi belge" hissi. Bu ayrım ürünün kendi gerilimini (sıcak sohbet vs. ciddi doğrulama) görsel olarak da taşır.
- Gövde metni sola hizalı (Türkçe diyakritikler ragged-right'ta daha okunaklı); hero'da merkez hizalama.

## Sayfa Düzeni

Düzen kodda tek yerde; sayfa kendi kabuğunu yazmaz.

- **Sayfa kabuğu** (`frontend/src/components/sayfa.tsx`): her iç sayfa `<Sayfa>` + `<SayfaBasligi>` ile başlar. Genişlik içeriğin türüne göre seçilir, sayfaya göre değil:

  | Genişlik | Ölçü | Ne için |
  |---|---|---|
  | `icerik` (varsayılan) | 672px | Okunan ve listelenen içerik: paneller, kart, sohbet, iş birliği. Satır uzunluğu okunabilir kalsın; panel bir "belge". |
  | `form` | 576px | Tek sütunlu formlar: kayıt, profil. |
  | `dar` | 448px | Birkaç alanlı kısa form: giriş. |

- **Kenar payı** her yerde aynı: mobilde 20px, `sm` ve üstünde 32px.
- **Başlık bloğu:** tek `h1` (Fraunces, 24→30px), altında açıklama. Başlığın yanında durum etiketi, sağda tek bir eylem olabilir.
- **Yükleniyor ve hata** durumları da aynı kabukla ve aynı genişlikte çizilir (`SayfaDurumu`, `GirisKapisi genislik=`). Veri gelince içerik yana ya da aşağı kaymaz.
- **Menü** (`menu-kabugu.tsx`): karşılama ve uygulama menüsü aynı iskeleti giyer. Yapışkandır, 1200px'lik geniş kapsayıcıdadır ve yüksekliği 64px (`lg`'de 76px). Girişten önce ve sonra logo aynı yerde durur. İçerik dar sütunda ortalanır, menü geniş kalır. `lg` altında bağlantılar katlanır menüye girer, bildirim zili ve okunmamış sayısı katlanmadan görünür kalır. Etkin sayfa kalın yazı ve vurgu renginde alt çizgiyle gösterilir.
- **Karşılama sayfası** kabuğun dışındadır: 1200px, kendi bölüm ritmi (96–112px) ve daha büyük yazı ölçeği (`docs/design/landing/LANDING_HANDOFF.md`). Uygulamanın içi sade ve dar kalır.
- **Kontrast:** vurgu rengi (`#B8823C`) üstünde metin koyu olur (`metin`, 4.9:1). Beyaz 3.3:1'de kalıyor. Küçük metin vurgu renginde yazılmaz, zemin üstünde 3:1'de kalıyor.

## Kaçınılacaklar

- Her şeyi aynı yuvarlak kart + aynı gölge kalıbına sokmak.
- 01/02/03 numaralandırma (içerik gerçekten sıralı bir süreç değilse).
- Başlıkların üstüne BÜYÜK HARF etiketler koymak.
- Buton yazılarının sonuna "→" eklemek.
- Her kartta hover'da oynayan animasyon — tek bir yerde, tek bir bilinçli hareket yeterli (örn. gerekçe kartının belirmesi).

## Yazım Tonu

Düz, sade Türkçe; aktif ses ("Kaydet", "Değişikliği gönder" — "Submit" değil). Buton bir eylemi ne diyorsa, sonucu da aynı kelimeyle anons etmeli ("Yayınla" butonu → "Yayınlandı" bildirimi). Hata mesajları özür dilemez, ne olduğunu net söyler. Boş ekranlar bir eyleme davet olarak yazılır.
