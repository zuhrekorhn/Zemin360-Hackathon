# Veri Şeması

## ER Diyagramı

```mermaid
erDiagram
  KULLANICI ||--o{ YETENEK_KARTI : sahiptir
  YETENEK_KARTI ||--o{ SOMUT_CIKTI : icerir
  SOMUT_CIKTI ||--o| GUVEN_SKORU : degerlendirilir
  SOMUT_CIKTI ||--o{ REFERANS_ISTEGI : ister
  KURUM ||--o{ IHTIYAC_KARTI : olusturur
  YETENEK_KARTI ||--o{ ESLESME : aday_olur
  IHTIYAC_KARTI ||--o{ ESLESME : eslesir
  ESLESME ||--o| ISBIRLIGI : donusur
  ISBIRLIGI ||--o{ MILESTONE : icerir
  ESLESME ||--o{ CANLILIK_OLAYI : tetikler

  KULLANICI {
    uuid id PK
    string ad
    string email
    string sehir
    string musaitlik
  }
  YETENEK_KARTI {
    uuid id PK
    uuid kullanici_id FK
    string rol_alani
    string deneyim_seviyesi
    boolean kanit_bekleyen
    int versiyon
  }
  SOMUT_CIKTI {
    uuid id PK
    uuid yetenek_karti_id FK
    string baslik
    string kanit_linki
    string kanit_turu
    date tarih
  }
  GUVEN_SKORU {
    uuid id PK
    uuid somut_cikti_id FK
    int kanit_orijinalligi
    int sonuc_olculebilirligi
    int rol_netligi
    int ucuncu_taraf_onayi
    string gerekce_metni
  }
  REFERANS_ISTEGI {
    uuid id PK
    uuid somut_cikti_id FK
    string referans_email
    string durum
    string yanit_metni
  }
  KURUM {
    uuid id PK
    string ad
    string sektor
    string sehir
  }
  IHTIYAC_KARTI {
    uuid id PK
    uuid kurum_id FK
    string problem_tanimi
    string basari_kriteri
    string kisitlar
  }
  ESLESME {
    uuid id PK
    uuid yetenek_karti_id FK
    uuid ihtiyac_karti_id FK
    float skor
    string gerekce_metni
    string durum
  }
  ISBIRLIGI {
    uuid id PK
    uuid eslesme_id FK
    date baslangic_tarihi
    string durum
  }
  MILESTONE {
    uuid id PK
    uuid isbirligi_id FK
    string baslik
    date hedef_tarih
    string durum
  }
  CANLILIK_OLAYI {
    uuid id PK
    uuid eslesme_id FK
    timestamp tetiklenme_tarihi
    string tur
    string mesaj_metni
  }
```

## Tasarım Kararları

- **`GUVEN_SKORU` ve `REFERANS_ISTEGI`, `SOMUT_CIKTI`'dan ayrı tablolar.** Bir çıktının birden fazla referans isteği olabilir; güven skoru zamanla güncellenebilir olmalı (itiraz sonrası yeniden hesaplama).
- **`ESLESME` → `ISBIRLIGI` ilişkisi isteğe bağlı (0 veya 1).** Her eşleşme iş birliğine dönüşmez — sadece kurumun "ilgileniyorum" dediği ve kabul edilen eşleşmeler.
- **`CANLILIK_OLAYI` doğrudan `ESLESME`'ye bağlı, `ISBIRLIGI`'na değil.** Pasiflik takibi bir iş birliği resmen başlamadan da çalışabilmeli — örn. "eşleşme önerildi ama kimse tıklamadı" durumu.
- **`kanit_bekleyen` (YETENEK_KARTI) ve `durum` (REFERANS_ISTEGI, ESLESME, ISBIRLIGI) alanları state machine mantığıyla çalışıyor.** Örn. `REFERANS_ISTEGI.durum`: `bekliyor` → `onaylandi` veya `yanit_yok` (zaman aşımı, ceza değil nötr durum).
