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
    const link = degisenIsKalemiAlanlari(eski, { ...eski, kanit_linki: "" });
    expect(link).toEqual({ kanit_linki: null });
    expect(gostergeSifirlanir(link)).toBe(true);
  });
});

describe("referansSatiri", () => {
  const referans = (ek: Partial<ReferansDurumu>) =>
    ({ durum: "yanitlandi", guncel: true, ...ek }) as ReferansDurumu;

  it("çalışmanın önceki hâline verilmiş yanıt: not ve yeniden iste", () => {
    expect(referansSatiri(referans({ guncel: false }))).toEqual({
      not: "Bu yanıt çalışmanın önceki hâline verildi; güven göstergesine girmiyor.",
      yenidenIstenebilir: true,
    });
  });

  it("güncel yanıt ve bekleyen istek yeniden istenemez; süresi dolan istenebilir", () => {
    expect(referansSatiri(referans({})).yenidenIstenebilir).toBe(false);
    expect(
      referansSatiri(referans({ durum: "bekliyor" })).yenidenIstenebilir,
    ).toBe(false);
    expect(
      referansSatiri(referans({ durum: "yanit_yok" })).yenidenIstenebilir,
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
