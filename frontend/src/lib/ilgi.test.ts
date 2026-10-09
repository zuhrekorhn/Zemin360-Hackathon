import { describe, expect, it } from "vitest";

import {
  firmaDurumEtiketi,
  firmaEylemleri,
  gerekceBekleniyor,
  gerekceYokMetni,
  gencDurumEtiketi,
  gencEylemleri,
  ilgiGosterenleriAyir,
  onerininAdayAdi,
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
  it.each([
    [0.7249, "Güçlü uyum"],
    [0.6, "Güçlü uyum"],
    [0.56, "İyi uyum"],
    [0.45, "İyi uyum"],
    [0.36, "Olası uyum"],
  ])("%s → %s (yüzde gösterilmez)", (skor, metin) => {
    expect(uyumMetni(skor)).toBe(metin);
  });
});

describe("eylemler", () => {
  it("genç: yalnızca önerilene ilgi, yalnızca bekleyeni geri çeker", () => {
    expect(gencEylemleri("onerildi")).toEqual({
      ilgiGoster: true,
      geriCek: false,
    });
    expect(gencEylemleri("genc_ilgilendi")).toEqual({
      ilgiGoster: false,
      geriCek: true,
    });
    expect(gencEylemleri("kabul_edildi")).toEqual({
      ilgiGoster: false,
      geriCek: false,
    });
  });

  it("firma: ilgi gösterene de ilgilenir, yalnızca ona 'Şimdilik değil' der", () => {
    expect(firmaEylemleri("onerildi")).toEqual({
      ilgileniyorum: true,
      simdilikDegil: false,
    });
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

describe("onerininAdayAdi", () => {
  it("genç adayında gencin, firma adayında firmanın adı", () => {
    expect(
      onerininAdayAdi({
        yetenek_karti: { genc_adi: "Elif" },
        firma_karti: null,
      }),
    ).toBe("Elif");
    expect(
      onerininAdayAdi({
        yetenek_karti: null,
        firma_karti: { firma_adi: "Market X" },
      }),
    ).toBe("Market X");
  });
});

describe("gerekceBekleniyor", () => {
  it("bekleyen adayın gerekçesi yoksa bekliyor sayılır", () => {
    expect(
      gerekceBekleniyor([
        { durum: "onerildi", gerekce_metni: "Uygun." },
        { durum: "ilgileniliyor", gerekce_metni: null },
      ]),
    ).toBe(true);
  });

  it("gerekçeler hazırsa ya da eksik olan kapanmış kayıtsa beklemez", () => {
    expect(
      gerekceBekleniyor([{ durum: "onerildi", gerekce_metni: "Uygun." }]),
    ).toBe(false);
    expect(
      gerekceBekleniyor([
        { durum: "kapandi", gerekce_metni: null },
        { durum: "kabul_edildi", gerekce_metni: null },
      ]),
    ).toBe(false);
    expect(gerekceBekleniyor([])).toBe(false);
  });
});

describe("gerekceYokMetni", () => {
  it("hazırlanırken kullanıcıdan bir şey istemez", () => {
    const metin = gerekceYokMetni(true);
    expect(metin).toContain("hazırlanıyor");
    expect(metin).not.toContain("Adayları yenile");
  });

  it("pes edince düğmeye yönlendirir", () => {
    const metin = gerekceYokMetni(false);
    expect(metin).toContain("hazırlanamadı");
    expect(metin).toContain("Adayları yenile");
  });
});
