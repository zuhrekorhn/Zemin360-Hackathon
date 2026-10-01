# Etiketleme Rehberi

Bu rehber, değerlendirme setindeki her vakaya **doğru** güven göstergesinin nasıl yazılacağını tanımlar. Etiket, bugünkü sistemin ne verdiğini değil, **olması gerekeni** söyler. Kaynak: `docs/plans/dogrulama-iyilestirme.md` § 2, § 5.2, § 7, § 11.2.

## 1. Etiketin biçimi

Her vakanın `beklenen` alanı dört başlık taşır:

```yaml
beklenen:
  kanit: 2        # 0-3 ya da null ("—")
  sonuc: 2
  rol: [2, 3]     # birden çok değer kabul edilebilirse liste
  referans: null
etiketleyen: zuhre
gozden_geciren: null
```

- **`null` = "—":** başlık değerlendirilmedi, değerlendirilemedi ya da yanıt yok. 0 ile karıştırılmaz.
- **Liste:** iki değer de savunulabiliyorsa (ör. ekip ortaklığı sayfada belirsizse Rol 2 ya da 3) kullanılır. Liste mümkün olduğunca dar tutulur; tek değer tercih edilir.
- **Etiketlenmemiş vaka:** `beklenen: null`. Karneye girmez. `onerilen` alanı yalnızca öneridir ve "taslak etiket" karnesinde kullanılır.
- **Kim etiketler:** `etiketleyen` boş olan vakanın `beklenen`'i geçersizdir. Etiketleri Zühre koyar. GİRVAK sonradan vakaların en az %20'sini gözden geçirir (`gozden_geciren`); anlaşmazlıklar `ANLASMAZLIKLAR.md`'ye yazılır.

## 2. Kaynak seviyesini belirle

Önce her kanıt parçasının seviyesini belirle. Tavanlar seviyeden gelir.

| Seviye | Ne zaman | Örnek |
|---|---|---|
| **A** Düzenleyen | Bağımsız bir kurum belgeyi üretmiş **ve** kimlik bağı var: imzalı rozet; geçerli e-imza; QR / doğrulama adresi düzenleyenin sitesinde ve kimlik koşulu sağlanıyor; GİRVAK'ın doğruladığı e-Devlet belgesi; e-postası doğrulanmış referansın "evet" yanıtı | Credly rozetindeki e-posta hesap e-postasıyla aynı |
| **B** Platform | Çalışma OAuth ya da profil koduyla **bağlı hesaba** ait | Bağlı GitHub hesabının reposu, bağlı Medium hesabının yazısı |
| **C** Kamuya açık | Herkese açık yayımlanmış çalışmanın kendisi; hesap bağlı değil | Herkese açık repo, blog yazısı, portfolyo işi, herkese açık Drive dosyası, ekran görüntüsü alınmış portfolyo sayfası |
| **D** Beyan | Yalnızca yazılmış iddia metni, çapasız yüklenmiş dosya ya da görsel, doğrulanmamış kullanıcı adı | Sohbette "backend'i ben yazdım" demek; QR'sız PDF yüklemek |

**Kimlik koşulu (ada dayalı A için):** ad eşleşmesi + doğrulanmış e-posta + kilitli ad, üçü birlikte. Biri eksikse en çok C.

## 3. Başlıklar

### Kanıt: iş var mı, bu kişinin mi?

| Durum | Değer |
|---|---|
| Link yok, dosya yok (yalnızca iddia metni) | `null` |
| Link okunamadı: giriş duvarı, bot engeli, sayfa boş, ağ hatası | `null` |
| Link yok (404 / 410), alan adı yok, güvensiz adres | 0 |
| Link açıldı ama çalışmayla **ilgisiz** | 0 |
| Çapasız yüklenmiş dosya / görsel, ilgili | 1 |
| Seviye C, ilgili | 2 |
| Seviye B ya da A, ilgili | 3 |
| Kanıt iddiayla açıkça çelişiyor (ör. yazar listesinde ad yok ama "yazdım" deniyor) | en çok 1 |

### Sonuç: iddiadaki sonuç ne kadar açık ve doğrulanmış?

| Durum | Değer |
|---|---|
| Sonuç yazılmamış | 0 |
| Yalnızca niteliksel ("çok işe yaradı") | 1 |
| Sayı / oran / süre var (beyan) | 2 |
| Sayı + neyi ölçtüğü açık + **bağımsız destek**: platform verisi (yıldız, indirme, mağaza sayısı), A seviyesinde belge, ya da referansın "sonuç doğru: evet" yanıtı | 3 |

Çalışmanın **içindeki** iddia (README'deki kullanıcı sayısı, portfolyodaki "satışı %40 artırdı") bağımsız destek değildir: en çok 2.

### Rol: kişinin payı ne kadar açık ve doğrulanmış?

| Durum | Değer |
|---|---|
| Pay yazılmamış | 0 |
| Belirsiz ("katkıda bulundum", "ekipteydim") | 1 |
| Özgül ("arayüzü ben yaptım") ama doğrulanmamış | 2 |
| Özgül + bağımsız destek: bağlı hesapta commit'lerin en az %90'ı gencin; bireysel proje kuralı; A belgesi rolü adlandırıyor; referansın "pay doğru: evet" yanıtı | 3 |

### Referans

| Durum | Değer |
|---|---|
| Referans istenmedi ya da yanıt gelmedi | `null` |
| Yanıtların ortalaması (evet = 3, kısmen = 1, hayır = 0; "bilmiyorum" ortalamaya girmez; 0.5 yukarı yuvarlanır) | 0-3 |

## 4. Bireysel proje kuralları

| Durum | Kanıt | Rol |
|---|---|---|
| Bağlı hesaba ait, tek katkıcılı repo (commit'lerin ≥ %90'ı) | 3 | 3 |
| Bağlı hesapta tek yazarlı yazı | 3 | 3 |
| Bağlı portfolyo sitesindeki iş | 3 | Ekip / ajans / müşteri ortaklığı belirtilmemişse 3 |
| Aynı işler, hesap bağlı değil | 2 | 2 |

Kurum ya da referans bağı bireysel projede şart değildir.

## 5. Kötü niyetli vakalar

`kotu_niyetli: true` olan vakada etiket yine **doğru davranışı** yazar. Amaç, sistemin sahte bir iddiaya 3 vermediğini ölçmektir: kötü niyetli vakada beklenmeyen her 3, karnenin en kritik ölçütünü bozar. Örnek: başkasının reposuna link veren gencin hesabı bağlı değilse Kanıt 2'dir (iş gerçek ama kimin olduğu kanıtlanmamış). Bağlı hesabı repoda katkıcı değilse de 2'dir, 3 değil.

## 6. Örnekler

| Vaka | Kanıt | Sonuç | Rol | Referans | Gerekçe |
|---|---|---|---|---|---|
| Bağlı GitHub'da tek katkıcılı repo, "400 kitap takip ediliyor" (README'de geçiyor) | 3 | 2 | 3 | — | Bireysel kural; sayı yalnızca README'de (iddia) |
| Aynı repo, hesap bağlı değil | 2 | 2 | 2 | — | Seviye C |
| Linksiz, "satışı %15 artırdım, kampanyayı ben yönettim", yönetici referansı her soruya "evet" | — | 3 | 3 | 3 | Referans sonucu ve payı doğruluyor |
| Behance projesi, bot engeli, hesap bağlı değil, ekran görüntüsü alındı | 2 | 2 | 2 | — | Ekran görüntüsü yolu seviye C |
| LinkedIn gönderisi (giriş duvarı), başka kanıt yok | — | iddiaya göre | iddiaya göre | — | Okunamadı |
| Mobil uygulama iddiası, link kedilerle ilgili bir sayfa | 0 | iddiaya göre | iddiaya göre | — | İlgisiz kanıt |
