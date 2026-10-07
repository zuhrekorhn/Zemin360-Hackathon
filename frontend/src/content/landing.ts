/**
 * Karşılama sayfasının (/) bütün metinleri — tek kaynak.
 *
 * Metinler içerik rehberine (docs/icerik-rehberi.md) göre yazıldı. Kopya değişikliği
 * yalnızca burada yapılır; bileşenler metin taşımaz. Mobilde de aynı metinler
 * gösterilir, yalnızca yerleşim değişir.
 */

export type Sekme = "genc" | "firma";

export type Seviye = 1 | 2 | 3;

/** Seviye çubuğunun kelimesi: renk tek başına bilgi taşımasın. */
export const SEVIYE_KELIMELERI: Record<Seviye, string> = {
  1: "Zayıf",
  2: "Orta",
  3: "Güçlü",
};

/** CTA hedefleri: mevcut kayıt ve giriş akışı (kayit/page.tsx `?rol=`). */
export const YOLLAR = {
  gencKayit: "/kayit?rol=genc",
  firmaKayit: "/kayit?rol=kurum",
  kayit: "/kayit",
  giris: "/giris",
  kvkk: "/kvkk",
} as const;

export const MENU = {
  logo: "Zemin360",
  baglantilar: [
    { etiket: "Nasıl çalışır", hedef: "#nasil" },
    { etiket: "Gençler için", hedef: "#nasil", sekme: "genc" },
    { etiket: "Firmalar için", hedef: "#nasil", sekme: "firma" },
    { etiket: "Neden Zemin360", hedef: "#surec" },
  ] as { etiket: string; hedef: string; sekme?: Sekme }[],
  giris: "Giriş yap",
  kayit: "Kayıt ol",
  menuyuAc: "Menüyü aç",
  menuyuKapat: "Menüyü kapat",
};

/** Hero ve kapanıştaki iki kapı; ikisi de aynı route'lara gider. */
export const KAPILAR = {
  genc: {
    baslik: "Fırsat arıyorum",
    alt: "Genç yetenekler için",
    hedef: YOLLAR.gencKayit,
  },
  firma: {
    baslik: "Yetenek ya da ortak arıyorum",
    alt: "Firmalar için",
    hedef: YOLLAR.firmaKayit,
  },
};

export const HERO = {
  etiket: "Genç yetenekler ve firmalar için buluşma platformu",
  baslik: "Yetenek ve ihtiyaç, kanıtla buluşsun.",
  metin:
    "Gençler yaptıkları çalışmaları görünür kılıyor, firmalar aradıkları yeteneği ya da iş birliği ortağını buluyor. Her eşleşmenin nedeni iki tarafa da açıkça gösteriliyor.",
};

export const DEMO = {
  baslik: "Kısa bir sohbet",
  rozet: "Örnek",
  soru: "Son bir yılda tamamladığın, sonucunu gösterebileceğin bir çalışman var mı?",
  yanit:
    "Mahalle kütüphanesine ödünç takip sistemi yazdım. 400 kitap ve 120 üyeyi takip ediyor.",
  ayrac: "Yetenek kartın hazır",
  kart: {
    ad: "Ayşe Y.",
    ozet: "1 çalışma · 1 referans",
    yetkinlikler: [
      "Veritabanı tasarımı",
      "Yazılım geliştirme",
      "Uçtan uca proje",
    ],
  },
  firsat: {
    baslik: "Sana uygun · Kooperatif üye kayıt sistemi",
    metin:
      "Benzer bir sorunu daha önce çözmüş, sonucu somut, referansı doğrulanmış.",
  },
};

export const SORUN = {
  baslik: "İyi fırsatlar çoğu zaman doğru kişiyi tanıyanlara gidiyor.",
  maddeler: [
    {
      baslik: "Yapılanlar görünmüyor.",
      metin:
        "Bir özgeçmiş, bir gencin gerçekte neler başardığını anlatmaya yetmiyor.",
    },
    {
      baslik: "İhtiyaç netleşmiyor.",
      metin:
        "“Dijitalleşmek istiyoruz” gibi genel bir istek, kiminle çalışılması gerektiğini söylemiyor.",
    },
    {
      baslik: "Başlayan iş birliği yarım kalıyor.",
      metin:
        "Tanışmadan sonra süreç takip edilmediğinde, umut vadeden iş birlikleri sessizce sönüyor.",
    },
  ],
};

export type Adim = { baslik: string; metin: string; sonuc: string };

export const NASIL = {
  ustEtiket: "Nasıl çalışır",
  baslik: "Üç adımda doğru eşleşme.",
  sekmeler: [
    { deger: "genc", etiket: "Genç yetenek" },
    { deger: "firma", etiket: "Firma" },
  ] as { deger: Sekme; etiket: string }[],
  sonucEtiketi: "Sonuç:",
  adimlar: {
    genc: [
      {
        baslik: "Kısa bir sohbetle başla.",
        metin:
          "Form doldurmak ya da CV yüklemek yerine, yaptığın çalışmaları birkaç soruyla anlat. Yetenek kartın bu sohbetten oluşur.",
        sonuc: "Yetenek kartın",
      },
      {
        baslik: "Çalışmalarını kanıtla.",
        metin:
          "Her çalışman için bir kanıt linki ekle ya da seni tanıyan birinden referans iste. Kanıtın güçlendikçe kartın öne çıkar.",
        sonuc: "Güven göstergesi",
      },
      {
        baslik: "Sana uygun fırsatları gör.",
        metin:
          "Hangi fırsata neden uygun olduğunu açıkça gör. İlgileniyorsan firmaya bildir.",
        sonuc: "Sana uygun fırsatlar",
      },
    ],
    firma: [
      {
        baslik: "İhtiyacınızı kendi cümlelerinizle anlatın.",
        metin:
          "Aklınızdakini olduğu gibi yazın. İhtiyacı netleştirmek için size birkaç soru sorulur.",
        sonuc: "Taslak ihtiyaç",
      },
      {
        baslik: "İhtiyaç kartınızı onaylayın.",
        metin:
          "Genel bir istek; kapsamı, beklenen sonucu ve başarı ölçütü belli bir tanıma dönüşür.",
        sonuc: "İhtiyaç kartı",
      },
      {
        baslik: "Uygun adayları ve iş ortaklarını görün.",
        metin:
          "İhtiyacınıza uygun genç yetenekleri ve iş birliği yapabileceğiniz firmaları, neden uygun olduklarıyla birlikte görün.",
        sonuc: "Adaylar ve olası iş ortakları",
      },
    ],
  } as Record<Sekme, Adim[]>,
};

export const SEFFAF = {
  ustEtiket: "Şeffaf eşleşme",
  baslik: "Her eşleşmenin nedeni açıkça görünür.",
  metin:
    "Tek bir puan yerine dört başlıkta değerlendirme: kanıt, sonuç, rol ve referans. Firma neye güvenebileceğini, genç neyi güçlendirebileceğini görür.",
  baglanti: { etiket: "Değerlendirme nasıl yapılıyor?", hedef: "#" },
  kart: {
    baslik: "Neden uygun?",
    rozet: "Örnek",
    altbaslik:
      "Üye kayıtlarını elle tutmaktan kurtulmak isteyen bir kooperatifin ihtiyacıyla",
    satirlar: [
      {
        baslik: "Kanıt",
        metin: "Kanıt linki açılıyor, çalışmayı kendisi geliştirmiş.",
        seviye: 3,
      },
      {
        baslik: "Sonuç",
        metin: "400 kitap ve 120 üye belirtilmiş, kullanım süresi yok.",
        seviye: 2,
      },
      {
        baslik: "Rol",
        metin: "Çalışmanın tamamını tek başına üstlenmiş.",
        seviye: 3,
      },
      {
        baslik: "Referans",
        metin: "Kütüphane sorumlusu referans isteğini yanıtladı.",
        seviye: 2,
      },
    ] as { baslik: string; metin: string; seviye: Seviye }[],
  },
  not: "Kanıt, sonuç ve rol yapay zekâ desteğiyle değerlendirilir; referans puanını referans kişi verir.",
};

export const SUREC = {
  ustEtiket: "Tanışmadan iş birliğine",
  baslik: "Eşleşmeyle bitmiyor, iş birliği boyunca süreç takip ediliyor.",
  metin:
    "Her adım yapay zekâ desteğiyle ilerler; son kararı her zaman kullanıcı verir.",
  kartlar: [
    {
      no: "01",
      soru: "Beni kim fark edecek?",
      baslik: "Yetenek kartı oluşturur",
      metin:
        "Kısa bir sohbetten, gencin çalışmalarını anlatan bir yetenek kartı çıkarır.",
    },
    {
      no: "02",
      soru: "Tam olarak neye ihtiyacımız var?",
      baslik: "İhtiyacı netleştirir",
      metin:
        "Genel bir isteği, ölçülebilir bir ihtiyaç kartına dönüştürür.",
    },
    {
      no: "03",
      soru: "Anlatılanlar gerçekten doğru mu?",
      baslik: "Kanıtı değerlendirir",
      metin:
        "Çalışmaları kanıt, sonuç, rol ve referans başlıklarında değerlendirir.",
    },
    {
      no: "04",
      soru: "Kiminle çalışmalıyım?",
      baslik: "Doğru kişiyle buluşturur",
      metin: "Uygun eşleşmeleri, neden uygun olduklarıyla birlikte önerir.",
    },
    {
      no: "05",
      soru: "İş birliği ne durumda?",
      baslik: "İş birliğini izler",
      metin:
        "Planı ve adımları iki tarafın da gördüğü tek bir ekranda tutar.",
    },
    {
      no: "06",
      soru: "Bağlantılarımız hâlâ canlı mı?",
      baslik: "Bağlantıları canlı tutar",
      metin: "Sessizleşen bağlantıları fark eder, hatırlatma gönderir.",
    },
  ],
  dongu:
    "Tamamlanan her iş birliği, sonraki eşleşmeleri daha isabetli hâle getirir.",
};

export const GUVEN = {
  maddeler: [
    {
      baslik: "Unvan değil, kanıt.",
      metin:
        "Yetenek kartları, açılabilen kanıtlar ve yanıtlanan referanslarla güçlenir.",
    },
    {
      baslik: "Onay olmadan hiçbir şey kaydedilmez.",
      metin:
        "Yetenek kartı da ihtiyaç kartı da sahibi onaylamadan kaydedilmez.",
      baglanti: { etiket: "KVKK aydınlatma metni", hedef: YOLLAR.kvkk },
    },
    {
      baslik: "Herkes aynı tabloyu görür.",
      metin:
        "İş birliği başladığında plan, adımlar ve son durum iki tarafın da erişebildiği ortak bir alanda tutulur.",
    },
  ] as {
    baslik: string;
    metin: string;
    baglanti?: { etiket: string; hedef: string };
  }[],
  program:
    "Türkiye Girişimcilik Vakfı'nın (GİRVAK) Zemin360 programı kapsamında geliştirilmektedir.",
};

export const KAPANIS = {
  baslik: "Yapılan iş görünsün, doğru kişiler buluşsun.",
};

export const ALTBILGI = {
  logo: "Zemin360",
  slogan: "Genç yetenekleri ve firmaları kanıtla buluşturan platform",
  baglantilar: [
    { etiket: "Gizlilik", hedef: "#" },
    { etiket: "KVKK", hedef: YOLLAR.kvkk },
    { etiket: "İletişim", hedef: "#" },
  ],
};
