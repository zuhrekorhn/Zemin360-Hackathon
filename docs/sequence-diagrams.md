# Sequence Diyagramları

Uçtan uca dört akış. Arka plan işleri (`BackgroundTasks`) yanıt döndükten sonra çalışır;
diyagramlarda "arka planda" diye işaretli.

## Akış 1 — Kart, ilan ve eşleşme (iki kapı)

Genç ve firma aynı anda platformda olmak zorunda değil: eşleştirme hangisi önce gelirse gelsin
kart ya da ilan onaylanınca o kayıt için çalışır.

```mermaid
sequenceDiagram
  actor G as Genç
  actor F as Firma
  participant K as Keşif / Tanımlama<br/>(sohbet motoru)
  participant E as Eşleştirme<br/>(pipeline)
  participant DB as Veri katmanı

  G->>K: Kayıttan sonra sohbet (form bilgisi sorulmaz)
  K-->>G: Kart taslağı
  G->>K: Onaylar (onaysız kaydedilmez)
  K->>DB: Yetenek kartı
  K-)E: Arka planda: embedding, çalışmaların değerlendirilmesi, açık ilanlarla eşleştirme

  F->>K: İhtiyaç sohbeti (genç yetenek ya da iş birliği ortağı kapısı)
  K-->>F: İlan taslağı
  F->>K: Onaylar
  K->>DB: İhtiyaç kartı
  K-)E: Arka planda: embedding ve eşleştirme

  E->>DB: Sert filtreler (SQL) + pgvector benzerliği + alt sınır
  E->>E: Skor (yalnızca sıralar), LLM gerekçesi ve uygunluk kararı
  E->>DB: onerildi (uygun_degil saklanır, görünmez)
  E-)F: Bildirim: yeni öneri

  alt Firma önce ilgilenir
    F->>E: İlgileniyorum
    E->>DB: ilgileniliyor
    E-)G: Bildirim
    G->>E: Kabul (ya da red → reddedildi)
  else Genç önce ilgilenir
    G->>E: İlgi + iletişim onayı
    E->>DB: genc_ilgilendi
    E-)F: Bildirim (5 gün yanıt yoksa Canlılık hatırlatır)
    F->>E: İlgileniyorum (ya da "şimdilik değil" → kapandi)
  end
  E->>DB: kabul_edildi + iş birliği açılır
  E-)G: Bildirim ve "eşleştiniz" e-postası (alan tarafa)
  E-)F: E-postalar iki tarafa açılır, "E-posta yaz" taslağı
```

Kural tek fonksiyonda (`app/agents/eslesme_durumu.py`); geçersiz geçiş 409, aynı geçişin tekrarı
200 ve yan etkisiz. Ayrıntı: `kimlik-ve-dongu.md` § 5. Firma–firma'da aday tarafında bir firma
vardır; akış aynıdır.

## Akış 2 — Doğrulama (kanıt, referans ve zaman aşımı dalı)

Zaman aşımı bir hata değil, tasarlanmış bir dal: kişiyi cezalandırmayan nötr bir durum.

```mermaid
sequenceDiagram
  actor G as Genç
  participant D as Doğrulama
  participant DB as Veri katmanı
  actor R as Referans kişi

  G->>D: Kanıt ekler (link, dosya ya da görsel)
  D->>D: Okuma zinciri: platform → genel → yedek okuyucu; seviye (A-D)
  D->>D: Model alıntıyla gerçek çıkarır, kural puanlar
  D->>DB: Güven göstergesi (okunamayan başlık "—", 0 değil)

  G->>D: Referans ister (gencin kendi adresi 422)
  D->>R: Tek kullanımlık bağlantı e-postayla (genç bağlantıyı görmez)

  opt Adres yanlışsa
    G->>D: Geri çeker (geri_cekildi)
  end
  opt 3. gün, yanıt yoksa (Canlılık taraması)
    D->>R: Tek hatırlatma
  end

  alt 7 gün içinde yanıt
    R->>D: 4 soruluk form (ilişki; çalışma, pay, sonuç doğru mu)
    D->>DB: Koşullu güncelleme (yalnızca bekliyor ise), Referans başlığı
    D-)G: Bildirim; pay / sonuç "evet" ise arka planda yeniden puanlama
  else Zaman aşımı (okuma anında ya da taramada)
    D->>DB: yanit_yok
    D-)G: Nötr bildirim: yeniden ya da başkasından isteyebilir
  end

  opt Genç itiraz ederse
    G->>D: Not ile itiraz (aynı girdi önceki sonucu döner, en çok 3)
    D->>DB: Yeniden değerlendirme ya da GİRVAK kuyruğu
  end
```

Referans yanıt ucu (`/dogrulama/referans-yaniti`) token'lı ve girişsizdir: referans kişiyi üye
olmaya zorlamak yanıt oranını düşürür. Ayrıntı: `dogrulama.md`.

## Akış 3 — Takip (plan, onay, adımlar, tamamlanma)

```mermaid
sequenceDiagram
  actor A as Aday tarafı
  actor F as İlan tarafı
  participant T as Takip
  participant DB as Veri katmanı
  participant E as Eşleştirme

  T-)T: Arka planda: süreç şablonu seçilir (işe alım, staj, proje, deneme işi, tedarik, iş birliği)
  T->>DB: Şablon adımları, ajan "ne olunca tamam" ve hazırlık önerisini yazar
  T-)A: Bildirim: plan önerildi
  T-)F: Bildirim: plan önerildi

  A->>T: Adımı düzenler (iki onay sıfırlanır)
  A->>T: Planı onaylar
  F->>T: Planı onaylar
  T->>DB: aktif, plan kilitlenir

  loop Her adım
    A->>T: Tamamlandı olarak işaretle
    F->>T: Tamamlandı olarak işaretle
    T->>DB: Adım tamamlandı (iki işaret)
  end
  T->>DB: Son adımla tamamlandi (kural, ajan değil)
  E->>DB: Sonraki eşleştirmelerde adayın bonusuna toplamsal girer (en çok +0.125)

  opt Erken sonlanma
    A->>T: Süreci sonlandır (nedenle)
    T->>DB: sonlandi (geri açılmaz, tamamlanmış sayılmaz)
    T-)F: Nedensiz nötr bildirim
  end
```

Ayrıntı: `takip.md`.

## Akış 4 — Canlılık taraması

```mermaid
sequenceDiagram
  actor V as GİRVAK (düğme) ya da betik
  participant C as Canlılık
  participant DB as Veri katmanı
  participant L as LLM (hızlı katman)

  V->>C: POST /canlilik/tarama
  C->>DB: Danışma kilidi (eşzamanlı tarama sıraya girer)
  C->>DB: Hareketsiz kayıtlar (okuma anında, eşiklere göre)
  C->>DB: Son hareketten sonra aynı türde olay var mı? (tekrar kuralı)
  C->>L: Kişiye özel hatırlatma metni
  L-->>C: Metin (yoksa şablon)
  C->>DB: Canlılık olayı + bildirim (aynı işlemde)
  C->>C: Referans hatırlatma ve zaman aşımı, link çürümesi yoklaması, 90 günlük temizlik
  C-->>V: Özet: türe göre olay sayıları
```

Tarama idempotenttir: art arda iki kez çalıştırmak ikinci seferde sıfır olay üretir. Ayrıntı:
`canlilik.md`.
