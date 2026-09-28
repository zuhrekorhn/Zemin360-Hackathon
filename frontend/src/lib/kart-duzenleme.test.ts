import { describe, expect, it } from "vitest";

import type { ReferansDurumu, SomutCiktiTaslagi } from "@/lib/api";
import {
  degisenIsKalemiAlanlari,
  gostergeSifirlanir,
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
      degisenIsKalemiAlanlari(eski, { ...eski, baslik: " Kütüphane ", aciklama: "" }),
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

  it("işin önceki hâline verilmiş yanıt: not ve yeniden iste", () => {
    expect(referansSatiri(referans({ guncel: false }))).toEqual({
      not: "Bu yanıt işin önceki hâline verildi; güven göstergesine girmiyor.",
      yenidenIstenebilir: true,
    });
  });

  it("güncel yanıt ve bekleyen istek yeniden istenemez; süresi dolan istenebilir", () => {
    expect(referansSatiri(referans({})).yenidenIstenebilir).toBe(false);
    expect(referansSatiri(referans({ durum: "bekliyor" })).yenidenIstenebilir).toBe(false);
    expect(referansSatiri(referans({ durum: "yanit_yok" })).yenidenIstenebilir).toBe(true);
  });
});
