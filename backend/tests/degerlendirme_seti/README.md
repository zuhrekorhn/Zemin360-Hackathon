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
python -m scripts.karne                 # çevrimdışı, yalnızca etiketli vakalar
python -m scripts.karne --taslak        # etiketsiz vakada önerilen etiketle
python -m scripts.karne --kip kaydet    # gerçek ağ + model, kaseti günceller
```

Kayıt kipi yalnızca yeni ya da değişen vakalar için çalıştırılır. Daha önce kaydedilmiş model girdisi yeniden çağrılmaz; bir sayfayı yeniden kaydetmek için ilgili kaydı `kaset/ag.json`'dan silmek gerekir.

## Etiketleme durumu

- Vakaların `onerilen` alanı taslaktır, etiket değildir. Etiketi Zühre koyar (`beklenen` + `etiketleyen`).
- Etiketlenmemiş vaka resmî karneye girmez.
- Hedef: 120 vaka. Kötü niyetli vakaları Zühre üretir. Taslaktaki kötü niyetli örnekler yalnızca öneridir.
- GİRVAK vakaların en az %20'sini gözden geçirir (`gozden_geciren`).

## Yeni vaka eklemek

1. İlgili `vakalar/<alan>.yaml` dosyasına vakayı ekle (şema: `degerlendirme/vaka.py`).
2. Link varsa `python -m scripts.karne --kip kaydet` ile kaseti güncelle.
3. `pytest tests/test_degerlendirme_seti.py` setin bütünlüğünü denetler: her link kayıtlı, kimlikler tekil.
