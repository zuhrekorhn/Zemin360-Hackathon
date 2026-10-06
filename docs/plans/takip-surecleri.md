# Takip: gerçekçi süreçler (6 Eki)

Durum: **uygulandı (6 Eki), altı adım altı commit; elle deneme kullanıcıda.** Takip incelemesi (`ajan-inceleme-sirasi`: Eşleştirme → Takip → Canlılık).
Eşleştirme incelemesi paralel oturumda; bu plan pilot bonusuna (`tamamlanan_pilot_sayilari`,
`matching-algorithm.md` § 4) dokunmaz.

## Sorun

Ajan her eşleşmeye "1. hafta tanışma, 2. hafta taslak…" diye serbest bir proje planı yazıyor.
Gerçek hayatta genç–firma eşleşmesi bir işe alım/staj sürecidir, firma–firma eşleşmesi bir
pilot ya da tedarik sürecidir; adımlar sektörde bellidir ve her eşleşme "tamamlandı" ile
bitmez (görüşmeden sonra "şimdilik değil" olağan bir sonuçtur). Ayrıca model kurala uymazsa
plan boş kalıyor.

## Karar

**Adımlar kodda, kişiselleştirme ajanda.** Her eşleşme türünün sabit bir süreç şablonu var
(Strategy: `SurecSablonu`, seçim tek fonksiyonda). Ajan adımları UYDURMAZ; her adım için
"ne olunca tamam sayılır" cümlesini ve bir hazırlık önerisini (görüşme soruları, deneme görevi)
ilana ve karta göre yazar. Model başarısız olursa şablonun kendi metni kullanılır: plan hiçbir
zaman boş kalmaz. Ajan yine karar vermez; adımları taraflar onaylar, işaretler, düzenler.

### Şablonlar (`app/agents/takip_surecleri.py`)

| Şablon | Seçim | Adımlar (varsayılan hafta) |
|---|---|---|
| `ise_alim` | genç ilanı, tam / yarı zamanlı ya da belirtilmemiş | Tanışma görüşmesi planlandı (1) · Görüşme yapıldı (2) · Deneme görevi teslim edildi (3) · Karar verildi (4) · İlk ay değerlendirmesi (8) |
| `staj` | genç ilanı, staj | Tanışma görüşmesi (1) · Staj planı ve sorumlu kişi belirlendi (2) · Staj başladı (3) · Ara değerlendirme (6) · Staj sonu değerlendirmesi (10) |
| `proje` | genç ilanı, proje bazlı | Tanışma görüşmesi (1) · Kapsam ve teslim tarihi netleşti (2) · İlk teslim (4) · Geri bildirim ve düzeltme (5) · Son teslim (6) |
| `pilot` | firma ilanı: pilot (büyük anlaşmadan önce küçük deneme işi) | Tanışma toplantısı (1) · Ön görüşme ve gizlilik (2) · Deneme işinin kapsamı ve ölçütü onaylandı (3) · Deneme işi yürütüldü (8) · Değerlendirme: devam mı? (9) |
| `tedarik` | firma ilanı: tedarik | Tanışma toplantısı (1) · Teklif ve numune (2) · Anlaşma (4) · İlk teslimat (6) · Teslimat değerlendirmesi (8) |
| `isbirligi` | firma ilanı: ortak ürün, yatırım, diğer, belirtilmemiş | Tanışma toplantısı (1) · Ön görüşme ve gizlilik (2) · İş birliğinin kapsamı netleşti (3) · İş birliği yürütüldü (8) · Değerlendirme (9) |

Son adım her şablonda ilanın başarı kriterine bağlanır. Haftalar varsayılan; taraflar düzenler.
Yeni şablon = tabloya bir satır; seçim kuralı ve ajan değişmez (açık/kapalı).

### Erken sonlanma

İş birliği her eşleşmede "tamamlandı" ile bitmiyor. Yeni durum `sonlandi`: iki taraftan biri
`plan_bekliyor` ya da `aktif` iken nötr bir nedenle sonlandırır (`karar_olumsuz`,
`baska_yoldan_ilerlendi`, `iletisim_kurulamadi`). Karşı tarafa nötr bildirim, neden yazılmaz
(rehber § 5.7). Kural `takip_durumu.py`'de saf bir geçiş; `sonlandi` geri açılmaz. Pilot bonusu
yalnızca `tamamlandi`'yı sayar (değişmez); Canlılık zaten yalnızca açık iş birliklerine bakar.

## Veri (tek migration, yalnızca ekleme)

- `isbirligi.surec` (String, null: eski kayıt), `isbirligi.sonlanma_nedeni`, `isbirligi.sonlanma_tarihi`.
- `milestone.asama` (şablondaki adım anahtarı; elle eklenen adımda null), `milestone.oneri` (Text).

## Adımlar (her biri ayrı commit, testler yalnızca sonda)

1. **Şablonlar ve seçim** (saf): `takip_surecleri.py` › `SurecSablonu`, `surec_sec(ihtiyac)`,
   `sablon_adimlari(sablon, baslangic)`.
2. **Ajanı kişiselleştirmeye çevir:** `takip.py` istemi şablon adımlarını alır, adım başına
   `tamam_tanimi` + `oneri` döner; anahtar eşleşmezse o adımda şablon metni. Genç ve firma
   istemi aynı fonksiyondan (bugünkü `replace` ile türetme kalkar).
3. **Migration + servis:** kabulde şablon adımları her zaman yazılır, ajan arka planda
   zenginleştirir (`plan_onerildi_mi` deseni korunur; `tests/conftest.py` sahtesi güncellenir).
4. **Erken sonlanma:** `takip_durumu.sonlanma_gecisi`, uç `POST /isbirlikleri/{id}/sonlandir`,
   bildirim türü, sahiplik üçlüsü.
5. **Arayüz:** iş birliği sayfasında adımlar bir süreç çizgisi; her adımda "Hazırlık önerisi"
   açılır bölüm; "Süreci sonlandır" (OnayAlani ile, neden seçimi). Metinler rehbere göre.
6. **Belgeler ve testler:** `faz-c-takip.md`, api-contracts, agent-specs § 6, roadmap; birim
   (seçim, geçerlilik, sonlanma geçişi) ve uç testleri (sahiplik, sonlanma, bildirim).

## Dikkat (paralel oturum)

Eşleştirme oturumu aynı ağaçta: yalnızca kendi dosyalarım stage'lenir; migration oluşturmadan
önce `alembic heads` tek olmalı (değilse kullanıcıya sorulur); `agents/eslestirme.py`'ye dokunulmaz.
