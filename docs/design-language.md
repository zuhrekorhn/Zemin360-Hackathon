# Tasarım Dili

## Marka Karakteri

İki farklı kullanıcı kitlesi var: genç yetenekler (18-30 yaş, sıcak/davetkâr bir şey ister) ve her sektörden kurum temsilcisi (ciddi/güvenilir bir şey ister). Tasarım ikisini aynı anda karşılamalı — ne bir kreş uygulaması gibi ne bir banka dashboard'u gibi.

Yön: **"kök"** metaforu — doğrulanmış güven, büyüyen bir ağ, kök salma. Genel AI/startup klişelerinden (krem + terracotta `#D97757`, siyah + neon vurgu, herkeste aynı SaaS kart kiti) bilinçli olarak uzak duruyoruz.

## Renk Paleti

| Rol | Hex | Kullanım |
|---|---|---|
| Zemin | `#F3F4EE` | Sayfa arka planı |
| Ana (koyu) | `#1E3A2F` | Başlıklar, koyu yüzeyler, **birincil düğmeler** (zemin rengi metinle; 8 Eki 2026, altından değişti: altın her yerde olunca hiçbir şey öne çıkmıyordu) |
| Vurgu | `#B8823C` | Sayfa düzeyindeki tek öne çıkan an: "Sıradaki adım" bandının düğmesi, okunmamış rozeti, zayıf göstergenin amber zemini |
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
  | `genis` | 1024px | İki sütunlu ana sayfa: akış ve yan sütun (genç "Fırsatlar"). |
  | `icerik` (varsayılan) | 672px | Okunan ve listelenen içerik: paneller, kart, sohbet, iş birliği. Satır uzunluğu okunabilir kalsın; panel bir "belge". |
  | `form` | 576px | Tek sütunlu formlar: kayıt, profil. |
  | `dar` | 448px | Birkaç alanlı kısa form: giriş. |

- **Kenar payı** her yerde aynı: mobilde 20px, `sm` ve üstünde 32px.
- **Başlık bloğu:** tek `h1` (Fraunces, 24→30px), altında açıklama. Başlığın yanında durum etiketi, sağda tek bir eylem olabilir.
- **Yükleniyor ve hata** durumları da aynı kabukla ve aynı genişlikte çizilir (`SayfaDurumu`, `GirisKapisi genislik=`). Veri gelince içerik yana ya da aşağı kaymaz.
- **Menü** (`menu-kabugu.tsx`): karşılama ve uygulama menüsü aynı iskeleti giyer. Yapışkandır, 1200px'lik geniş kapsayıcıdadır ve yüksekliği 64px (`lg`'de 76px). Girişten önce ve sonra logo aynı yerde durur. İçerik dar sütunda ortalanır, menü geniş kalır. `lg` altında bağlantılar katlanır menüye girer, bildirim zili ve okunmamış sayısı katlanmadan görünür kalır. Etkin sayfa kalın yazı ve vurgu renginde alt çizgiyle gösterilir.
- **Menü içeriği:** bağlantılar yalnızca sayfadır; bildirimler zil (her ekranda), ayar ve çıkış adın baş harfli hesap menüsünde. "Panele dön" düğmesi yazılmaz, menü var.
- **Ekran "şimdi ne yapmalıyım" sırasıyla dizilir:** yanıt bekleyen iş en üstte ve vurgu renginde sol çizgiyle; boş bölüm çizilmez (yeni kullanıcı yedi boş kutu yerine tek çağrı görür); bölüm başına tek birincil eylem. Açıklama paragrafı yerine eylem: bir bölümün nasıl çalıştığı bir kez söylenir, her başlığın altında tekrarlanmaz.
- **Formlar istenince açılır:** bir öğenin ekleme ve düzenleme formları düğmenin arkasında; düzenle ve sil gibi ikincil eylemler "⋯" menüsünde (`eylem-menusu.tsx`), yıkıcı eylem birincil düğmenin yanında durmaz.
- **Seviye kelime ve çubukla:** güven göstergesi "Eksik / Zayıf / Orta / Güçlü" ve üç parçalı çubuk (`seviye-cubugu.tsx`, karşılama sayfasıyla ortak); "2/3" gibi not biçimi yok. En güçlü seviye bağlantı renginde.
- **Karşılama sayfası** kabuğun dışındadır: 1200px, kendi bölüm ritmi (96–112px) ve daha büyük yazı ölçeği (`src/app/page.tsx`, metinler `src/content/landing.ts`). Uygulamanın içi sade ve dar kalır.
- **Yüzeyler:** kutular zeminden bir ton açık, hairline kenar, çok hafif gölge, 12px köşe (`components/ui/yuzey.ts` › `KUTU`); dikkat isteyen yüzey amber ve kesikli (`DIKKAT`). Bir öğenin bütün işleri sağdan açılan panelde toplanır (`components/ui/yan-panel.tsx`), sayfa formlarla uzamaz.
- **Kontrast:** vurgu rengi (`#B8823C`) üstünde metin koyu olur (`metin`, 4.9:1). Beyaz 3.3:1'de kalıyor. Küçük metin vurgu renginde yazılmaz, zemin üstünde 3:1'de kalıyor.

## Kaçınılacaklar

- Her şeyi aynı yuvarlak kart + aynı gölge kalıbına sokmak.
- 01/02/03 numaralandırma (içerik gerçekten sıralı bir süreç değilse).
- Başlıkların üstüne BÜYÜK HARF etiketler koymak.
- Buton yazılarının sonuna "→" eklemek.
- Her kartta hover'da oynayan animasyon — tek bir yerde, tek bir bilinçli hareket yeterli (örn. gerekçe kartının belirmesi).

## Yazım Tonu

Düz, sade Türkçe; aktif ses ("Kaydet", "Değişikliği gönder" — "Submit" değil). Buton bir eylemi ne diyorsa, sonucu da aynı kelimeyle anons etmeli ("Yayınla" butonu → "Yayınlandı" bildirimi). Hata mesajları özür dilemez, ne olduğunu net söyler. Boş ekranlar bir eyleme davet olarak yazılır.
