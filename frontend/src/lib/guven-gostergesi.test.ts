import { describe, expect, it } from "vitest";

import {
  baslikGosterimi,
  gostergeDoluMu,
  ilkCumle,
  notuBasliklaraAyir,
} from "./guven-gostergesi";

describe("baslikGosterimi", () => {
  it("değerlendirilmemiş başlık 0 değil, tire gösterir", () => {
    expect(baslikGosterimi("Kanıt", null)).toEqual({
      metin: "—",
      sozlu: "değerlendirilmedi",
      seviye: null,
    });
  });

  it("değer kelimeyle ve çubuk seviyesiyle", () => {
    expect(baslikGosterimi("Sonuç", 2)).toEqual({
      metin: "Orta",
      sozlu: "Orta, 3 üzerinden 2",
      seviye: 2,
    });
    expect(baslikGosterimi("Kanıt", 3).metin).toBe("Güçlü");
  });

  it("referans yoksa 'referans yok' der", () => {
    expect(baslikGosterimi("Referans", null).sozlu).toBe("referans yok");
  });

  it("0 bir değerlendirme sonucudur, tire değildir", () => {
    expect(baslikGosterimi("Referans", 0)).toEqual({
      metin: "Eksik",
      sozlu: "Eksik, 3 üzerinden 0",
      seviye: 0,
    });
  });
});

describe("notuBasliklaraAyir", () => {
  it("tek paragraflık notu başlıklarına böler", () => {
    expect(
      notuBasliklaraAyir(
        "Kanıt: Link açılıyor. Sonuç: Sonucu yazmamışsın. Rol: Payın açık.",
      ),
    ).toEqual([
      { baslik: "Kanıt", metin: "Link açılıyor." },
      { baslik: "Sonuç", metin: "Sonucu yazmamışsın." },
      { baslik: "Rol", metin: "Payın açık." },
    ]);
  });

  it("başlıksız not tek parça, boş not hiç", () => {
    expect(notuBasliklaraAyir("Genel bir not.")).toEqual([
      { baslik: null, metin: "Genel bir not." },
    ]);
    expect(notuBasliklaraAyir(null)).toEqual([]);
    expect(notuBasliklaraAyir("  ")).toEqual([]);
  });
});

describe("gostergeDoluMu", () => {
  const bos = {
    kanit_orijinalligi: null,
    sonuc_olculebilirligi: null,
    rol_netligi: null,
    ucuncu_taraf_onayi: null,
    gerekce_metni: null,
  };

  it("gösterge yoksa ya da dört başlık da boşsa hayır", () => {
    expect(gostergeDoluMu(null)).toBe(false);
    expect(gostergeDoluMu(bos)).toBe(false);
  });

  it("tek bir başlık doluysa evet (0 da dolu sayılır)", () => {
    expect(gostergeDoluMu({ ...bos, ucuncu_taraf_onayi: 0 })).toBe(true);
  });
});

describe("ilkCumle", () => {
  it("ilk cümleyi alır; noktasız metni olduğu gibi bırakır", () => {
    expect(
      ilkCumle("Payını yazmamışsın. Doğru kanıtı paylaşarak belirtebilirsin."),
    ).toBe("Payını yazmamışsın.");
    expect(ilkCumle("Sürüm 1.2 hazır")).toBe("Sürüm 1.2 hazır");
  });
});
