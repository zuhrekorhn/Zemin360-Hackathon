# Yedek okuyucu (Playwright servisi)

Backend'in düz HTTP isteğiyle okuyamadığı kanıt sayfalarını gerçek bir tarayıcıda açar:
JavaScript ile çizilen sayfalar (Kaggle, GrabCAD) ve tarayıcı olmayan istemciyi reddeden
siteler (Behance, Dribbble). İşlenmiş HTML'i ve istenirse ekran görüntüsünü döner
(1280 px genişlik, sayfanın üstten en çok 3 parçası, JPEG). Plan:
`docs/plans/dogrulama-iyilestirme.md` § 5.1, § 5.5.

Backend'den ayrı bir uygulamadır. Chromium ağır, kaynak tüketimi öngörülemez ve
kullanıcının verdiği adresi açar; bu yüzden ayrı bir süreçte çalışır. Backend ona
`YEDEK_OKUYUCU_ADRESI` üzerinden bağlanır; servis kapalıysa okuma onsuz biter.

## Uç noktalar

```
POST /oku     {"url", "ekran": "her_zaman" | "metin_azsa" | "hayir", "en_az_metin": 200}
              → {"durum", "son_url", "html", "ekran_goruntuleri": [base64 JPEG], "hata"}
GET  /saglik  → {"durum": "ok"}
```

`hata`: `guvensiz`, `bulunamadi`, `zaman_asimi`, `acilamadi` (yoksa `null`). `durum`, ana
çerçevenin son belgesinin HTTP durumudur: bot doğrulaması yapan site önce bir ara sayfa
(202 / 403) verir, tarayıcı onu geçince asıl sayfaya gider. Ekran görüntüsünün ne zaman
alınacağına backend karar verir; servis yalnızca uygular.

## Güvenlik

- **Tek ağ kapısı:** Chromium yalnızca süreç içindeki süzgeçli vekile (`vekil.py`) bağlanır.
  Yerel adresler de vekilden geçer (`<-loopback>`). WebRTC vekilsiz UDP açamaz.
- **Kurallar backend'le aynı:** her bağlantı `app/core/guvenli_istek.py`'deki
  `hedefi_dogrula` ile denetlenir: yalnızca 80 / 443, alan adının bütün IP'leri genel
  internette. Bağlantı denetlenen IP'ye açılır, bu yüzden DNS yeniden bağlama işe yaramaz.
  Yönlendirmeler, görseller, `fetch` ve WebSocket'ler de aynı denetimden geçer.
- **Neden istek yakalama değil:** Playwright'ta yakalanan bir isteğe 3xx verilince tarayıcı
  yönlendirmeyi yakalamadan doğrudan ağdan izliyor (denendi). İstekleri Python'dan atmak
  da tarayıcının TLS kimliğini kaybettirip bot engelini geri getiriyor. Vekilde HTTPS
  tarayıcıda uçtan uca kalır (CONNECT tüneli).
- **Anahtar:** `YEDEK_OKUYUCU_ANAHTARI` doluysa istek `Authorization: Bearer <anahtar>`
  ister. Servis yerel makine dışına açılacaksa doldurulmalı.
- Her istek ayrı tarayıcı bağlamında açılır: çerez ve depolama paylaşılmaz. Service
  worker ve indirme kapalı.

## Yerelde çalıştırma

`backend/` içinde, backend'in sanal ortamıyla:

```bash
uv pip install --python .venv/Scripts/python.exe -e ".[yedek-okuyucu]"
python -m playwright install chromium
python -m yedek_okuyucu          # http://127.0.0.1:8100
```

Ortam değişkenleri: `PORT` (8100), `YEDEK_OKUYUCU_HOST` (127.0.0.1),
`YEDEK_OKUYUCU_ANAHTARI`, `YEDEK_OKUYUCU_ESZAMANLI` (aynı anda açılan sayfa, 2).
