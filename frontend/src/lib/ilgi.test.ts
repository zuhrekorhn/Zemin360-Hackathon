import { describe, expect, it } from "vitest";

import {
  firmaDurumEtiketi,
  firmaEylemleri,
  gencDurumEtiketi,
  gencEylemleri,
  ilgiGosterenleriAyir,
  uyumMetni,
} from "@/lib/ilgi";

describe("durum etiketleri (rehber § 5.9)", () => {
  it.each([
    ["onerildi", "Sana uygun", "Aday"],
    ["genc_ilgilendi", "İlgin iletildi", "İlgi gösterdi"],
    ["ilgileniliyor", "Firma seninle ilgileniyor", "Yanıt bekleniyor"],
    ["kabul_edildi", "Karşılıklı ilgi", "Karşılıklı ilgi"],
    ["reddedildi", "Kapandı", "Kapandı"],
    ["kapandi", "Kapandı", "Kapandı"],
  ])("%s", (durum, genc, firma) => {
    expect(gencDurumEtiketi(durum)).toBe(genc);
    expect(firmaDurumEtiketi(durum)).toBe(firma);
  });

  it("gence hiçbir durumda ret ifadesi, hiç kimseye kod değeri gösterilmez", () => {
    for (const durum of ["reddedildi", "kapandi", "bilinmeyen_kod"]) {
      expect(gencDurumEtiketi(durum)).not.toMatch(/ret|redd|elen/i);
      expect(gencDurumEtiketi(durum)).not.toContain("_");
      expect(firmaDurumEtiketi(durum)).not.toContain("_");
    }
  });
});

describe("uyumMetni", () => {
  it("yüzde işareti sayıdan önce", () => {
    expect(uyumMetni(0.7249)).toBe("%72 uyum");
  });
});

describe("eylemler", () => {
  it("genç: yalnızca önerilene ilgi, yalnızca bekleyeni geri çeker", () => {
    expect(gencEylemleri("onerildi")).toEqual({ ilgiGoster: true, geriCek: false });
    expect(gencEylemleri("genc_ilgilendi")).toEqual({ ilgiGoster: false, geriCek: true });
    expect(gencEylemleri("kabul_edildi")).toEqual({ ilgiGoster: false, geriCek: false });
  });

  it("firma: ilgi gösterene de ilgilenir, yalnızca ona 'Şimdilik değil' der", () => {
    expect(firmaEylemleri("onerildi")).toEqual({ ilgileniyorum: true, simdilikDegil: false });
    expect(firmaEylemleri("genc_ilgilendi")).toEqual({
      ilgileniyorum: true,
      simdilikDegil: true,
    });
    expect(firmaEylemleri("kabul_edildi")).toEqual({
      ilgileniyorum: false,
      simdilikDegil: false,
    });
  });

  it("ilgi gösterenler ayrılır, sıra korunur", () => {
    const liste = [
      { id: 1, durum: "onerildi" },
      { id: 2, durum: "genc_ilgilendi" },
      { id: 3, durum: "kabul_edildi" },
      { id: 4, durum: "genc_ilgilendi" },
    ];
    const { ilgiGosterenler, digerleri } = ilgiGosterenleriAyir(liste);
    expect(ilgiGosterenler.map((o) => o.id)).toEqual([2, 4]);
    expect(digerleri.map((o) => o.id)).toEqual([1, 3]);
  });
});
