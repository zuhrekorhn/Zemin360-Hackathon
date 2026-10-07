# Katkı Rehberi

Kurulum README'de. Bu belge kodun nasıl yazıldığını ve bir değişikliğin ne zaman "bitti"
sayıldığını anlatır.

## Değişiklikten önce

- İlgili tasarım belgesini oku (`docs/`): ne yapar, hangi tablo, hangi uç, ne yapmaz. Belgelerdeki
  bir kararla çelişen bir yaklaşım (başka kütüphane, başka veri modeli) önce konuşulur;
  gerekçeler `docs/kararlar.md`'de.
- Kullanıcıya görünen her metin `docs/icerik-rehberi.md`'ye uyar: gence "sen", firmaya "siz";
  "ajan", "skor", "embedding" gibi teknik terimler kullanıcıya gösterilmez.

## Bitti sayılması için

Backend (`backend/` içinde):

```bash
ruff check . && ruff format --check .
pytest                      # gerçek API çağrısı yapmaz; yerel DB yoksa DB testleri atlanır
alembic check               # model değiştiyse: alembic revision --autogenerate -m "…"
```

Frontend (`frontend/` içinde):

```bash
npm run lint && npx tsc --noEmit && npm test
```

Aynı kontroller her push'ta CI'da çalışır (`.github/workflows/ci.yml`).

## Kod kuralları

**Katmanlar** (`docs/architecture.md` § Katmanlar): `app/api/` ince kalır; orkestrasyon
`app/servisler/`'de; saf kurallar ve dil modeli çağrıları `app/agents/`'ta; altyapı `app/core/`'da.
Alt katman üst katmandan import etmez.

**Kural tek yerde.** Durum geçişleri saf fonksiyonlardadır (`eslesme_durumu.gecis`,
`takip_durumu.plan_gecisi`…) ve tablo testle sabitlenir. Uç ve arayüz kuralı tekrar etmez,
sonucu okur.

**Yetki üçlüsü.** Her yeni uç `mevcut_hesap` / `rol_gerekli` ile korunur ve şu üçüyle test edilir:
401 token yok, 403 rol uygun değil, 404 başkasının kaynağı (`tests/test_sahiplik.py` deseni).
Sahiplik kuralı `app/servisler/sahiplik.py`'ye eklenir.

**Yapay zekâ karar vermez.** Model öneri, gerekçe ve metin üretir; puan, listeye girme ve durum
geçişi koddadır. Model hatası akışı durdurmaz: bilinmiyor / şablon / "—" yoluna düşülür.

**Arka plan işi eklersen** `tests/conftest.py`'de sahtesini de ekle; yoksa testler gerçek LLM ya
da Voyage çağırır.

**Dış servis eklersen** `app/core/dis_servisler/`'de bir `Protocol` arayüzü, `.env` bayrağı ve
kapalı (Null Object) sürümüyle; seçim yalnızca `kurulum.py`'de.

**Okuma uçları** eşleşme okurken `gorunur_kosulu()` uygular (gizli öneri hiçbir yerde görünmez).

**Adlar.** Veri şemasındaki Türkçe alan adlarına sadık kal (`kanit_bekleyen`, `guven_skoru`);
yorumlar ve değişken adları Türkçe ve İngilizce karışık olabilir. Yorum "neden"i anlatır; bir
kararın gerekçesi uzunsa `docs/kararlar.md`'ye numarayla (ör. `G14`) gönderme yapılır.

## Commit

Küçük ve tek konulu commit'ler; testler geçmeden commit yok. Mesaj Türkçe ve neyin neden
değiştiğini söyler.
