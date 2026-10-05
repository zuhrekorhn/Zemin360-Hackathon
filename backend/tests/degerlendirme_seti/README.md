# Doğrulama değerlendirme seti

Doğrulama'nın güven göstergesini ölçen etiketli vakalar (`docs/plans/dogrulama-iyilestirme.md` § 10.1). Her puanlama değişikliği bu set üzerinde önce ve sonra çalıştırılır.

## İçerik

| Yol | Ne |
|---|---|
| `ETIKETLEME_REHBERI.md` | Doğru etiketin kuralları (önce bunu oku) |
| `ANLASMAZLIKLAR.md` | Gözden geçirmede etiketleyenle ayrışılan vakalar |
| `vakalar/<alan>.yaml` | Vakalar; alan başına bir dosya |
| `dosyalar/` | Dosya ve görsel kanıtları |
| `kaset/` | Kayıtlı DNS, HTTP ve model yanıtları (çevrimdışı karne) |
| `karneler/` | Tarihli karneler ve gerileme anlık görüntüsü (`mevcut_sistem.json`) |

Kod `backend/degerlendirme/` paketinde.

## Kullanım

```bash
python -m scripts.karne                              # çevrimdışı, yalnızca etiketli vakalar
python -m scripts.karne --taslak                     # etiketsiz vakada önerilen etiketle
python -m scripts.karne --model kaydet               # kod değişti: kayıtlı sayfalar, eksik model çağrıları
python -m scripts.karne --ag kaydet --model kaydet   # yeni vaka: gerçek ağ + model
```

- **Kod değiştiğinde** `--model kaydet` kullanılır: sayfalar kasetten gelir, karnedeki fark yalnızca kodun farkıdır.
- **Ağ kaydı** sıfırdan başlar ve bütün sayfaları yeniden çeker. Sayfalar zamanla değiştiği için yalnızca yeni vaka eklenince kullanılır.
- **Model kaydı** daha önce görülmüş girdiyi yeniden çağırmaz. Dosyaya yalnızca o çalıştırmada kullanılan kayıtları yazar.

## Adalet

Karne, alan başına adalet tablosunu da yazar (`degerlendirme/adalet.py`, plan § 10.2): ortalama Kanıt, "—" oranı, Kanıt 3'e giden vakalar ve sorun işaretleri. Her alanda 3'e giden en az bir yol olmalı; işaret varsa vaka ya da yol eklenir (tavan düşürülmez). Etiketsiz vaka bu tabloya da girmez.

## Etiketleme durumu

- Vakaların `onerilen` alanı taslaktır, etiket değildir. Etiketi Zühre koyar (`beklenen` + `etiketleyen`).
- Etiketlenmemiş vaka resmî karneye girmez.
- Hedef: 120 vaka. Kötü niyetli vakaları Zühre üretir. Taslaktaki kötü niyetli örnekler yalnızca öneridir.
- GİRVAK vakaların en az %20'sini gözden geçirir (`gozden_geciren`).

## Yeni vaka eklemek

1. İlgili `vakalar/<alan>.yaml` dosyasına vakayı ekle (şema: `degerlendirme/vaka.py`).
2. Link varsa `python -m scripts.karne --ag kaydet --model kaydet` ile kaseti güncelle.
3. `pytest tests/test_degerlendirme_seti.py` setin bütünlüğünü denetler: her link kayıtlı, kimlikler tekil.
