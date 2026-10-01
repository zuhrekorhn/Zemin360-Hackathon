import { describe, expect, it } from "vitest";

import type { ReferansDurumu, SomutCiktiTaslagi } from "@/lib/api";
import {
  degisenIsKalemiAlanlari,
  eksikKartAlanlari,
  gostergeSifirlanir,
  kartAlanDegerleri,
  kartAlanlariniCevir,
  referansSatiri,
  virgulluListe,
} from "@/lib/kart-duzenleme";

describe("virgulluListe", () => {
  it("boşlukları kırpar, boşları ve tekrarı atar", () => {
    expect(virgulluListe(" Python, FastAPI ,, Python,Docker ")).toEqual([
      "Python",
      "FastAPI",
      "Docker",
    ]);
    expect(virgulluListe("")).toEqual([]);
  });
});

describe("degisenIsKalemiAlanlari", () => {
  const eski: SomutCiktiTaslagi = {
    baslik: "Kütüphane",
    aciklama: null,
    kanit_linki: "https://x.org",
    is_turu: "proje",
  };

  it("aynı değer değişiklik sayılmaz; boş metin null", () => {
    expect(
      degisenIsKalemiAlanlari(eski, {
        ...eski,
        baslik: " Kütüphane ",
        aciklama: "",
      }),
    ).toEqual({});
  });

  it("yalnızca tür değişince gösterge sıfırlanmaz, içerik değişince sıfırlanır", () => {
    const tur = degisenIsKalemiAlanlari(eski, { ...eski, is_turu: "staj" });
    expect(tur).toEqual({ is_turu: "staj" });
    expect(gostergeSifirlanir(tur)).toBe(false);
    const icerik = degisenIsKalemiAlanlari(eski, {
      ...eski,
      aciklama: "Ödünç",
    });
    expect(icerik).toEqual({ aciklama: "Ödünç" });
    expect(gostergeSifirlanir(icerik)).toBe(true);
  });

  it("kanıt iddia formunun alanı değil: link değişikliği gönderilmez", () => {
    expect(degisenIsKalemiAlanlari(eski, { ...eski, kanit_linki: "" })).toEqual(
      {},
    );
  });
});

describe("referansSatiri", () => {
  const referans = (ek: Partial<ReferansDurumu>) =>
    ({
      durum: "yanitlandi",
      guncel: true,
      yeniden_istenebilir: false,
      ...ek,
    }) as ReferansDurumu;

  it("çalışmanın önceki hâline verilmiş yanıt: not gösterilir", () => {
    expect(
      referansSatiri(referans({ guncel: false, yeniden_istenebilir: true })),
    ).toEqual({
      not: "Bu yanıt çalışmanın önceki hâline verildi; güven göstergesine girmiyor.",
      yenidenIstenebilir: true,
    });
  });

  it("düğme backend'in kararını izler, kuralı tekrar etmez", () => {
    // Süresi dolmuş ama aynı kişiden bekleyen istek var: backend "istenemez" der.
    expect(
      referansSatiri(
        referans({ durum: "yanit_yok", yeniden_istenebilir: false }),
      ).yenidenIstenebilir,
    ).toBe(false);
    expect(
      referansSatiri(referans({ yeniden_istenebilir: true }))
        .yenidenIstenebilir,
    ).toBe(true);
  });
});

describe("kart alanları (taslak ve düzenleme ortak)", () => {
  const bosTaslak = {
    rol_alani: null,
    deneyim_seviyesi: null,
    sektor_ilgi_alani: [],
    araclar_teknolojiler: [],
  };

  it("boş taslak boş form alanı olur, yer tutucu yazılmaz", () => {
    expect(kartAlanDegerleri(bosTaslak)).toEqual({
      rol: "",
      deneyim: "",
      sektor: "",
      araclar: "",
      sertifikalar: "",
      diller: "",
    });
  });

  it("onay için rol, deneyim ve en az bir sektör gerekir", () => {
    expect(eksikKartAlanlari(kartAlanDegerleri(bosTaslak))).toEqual([
      "rol",
      "deneyim",
      "sektor",
    ]);
    const dolu = kartAlanDegerleri({
      ...bosTaslak,
      rol_alani: "backend geliştirici",
      deneyim_seviyesi: "orta",
      sektor_ilgi_alani: ["eğitim"],
    });
    expect(eksikKartAlanlari(dolu)).toEqual([]);
    // Yalnızca boşluk ya da virgül doldurmuş sayılmaz.
    expect(eksikKartAlanlari({ ...dolu, rol: "  ", sektor: " , " })).toEqual([
      "rol",
      "sektor",
    ]);
  });

  it("formdan API alanlarına: metin kırpılır, listeler ayrılır", () => {
    const degerler = {
      ...kartAlanDegerleri(bosTaslak),
      rol: " veri analisti ",
      deneyim: "baslangic",
      sektor: "eğitim, sağlık",
    };
    expect(kartAlanlariniCevir(degerler)).toEqual({
      rol_alani: "veri analisti",
      deneyim_seviyesi: "baslangic",
      sektor_ilgi_alani: ["eğitim", "sağlık"],
      araclar_teknolojiler: [],
      sertifikalar: [],
      diller: [],
    });
  });
});
