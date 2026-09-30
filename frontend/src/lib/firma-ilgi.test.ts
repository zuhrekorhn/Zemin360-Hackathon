import { describe, expect, it } from "vitest";

import type { FirmaAdayEslesmesi } from "@/lib/api";
import {
  adayEslesmeleriniAyir,
  adayFirmaDurumEtiketi,
  adayFirmaEylemleri,
} from "@/lib/firma-ilgi";

function satir(
  eslesme_id: string,
  durum: string,
  baslatan: string | null,
): FirmaAdayEslesmesi {
  return {
    eslesme_id,
    durum,
    baslatan,
    uyum: 0.6,
    gerekce_metni: null,
    son_aktivite_tarihi: "2026-09-30T10:00:00Z",
    ihtiyac_karti: {} as FirmaAdayEslesmesi["ihtiyac_karti"],
    isbirligi_id: null,
    iletisim: null,
  };
}

describe("adayEslesmeleriniAyir", () => {
  it("fırsat, gelen ilgi ve kendi ilgisi ayrı; başlatanı olmayan kapanmış kayıt düşer", () => {
    const { firsatlar, gelenler, ilgilerimiz } = adayEslesmeleriniAyir([
      satir("a", "onerildi", null),
      satir("b", "ilgileniliyor", "kurum"),
      satir("c", "kabul_edildi", "kurum"),
      satir("d", "genc_ilgilendi", "genc"),
      satir("e", "kapandi", "genc"),
      satir("f", "kapandi", null),
    ]);
    expect(firsatlar.map((s) => s.eslesme_id)).toEqual(["a"]);
    expect(gelenler.map((s) => s.eslesme_id)).toEqual(["b", "c"]);
    expect(ilgilerimiz.map((s) => s.eslesme_id)).toEqual(["d", "e"]);
  });
});

describe("etiket ve eylemler", () => {
  it("firmaya 'siz', ret ifadesi yok", () => {
    expect(adayFirmaDurumEtiketi("genc_ilgilendi")).toBe("İlginiz iletildi");
    expect(adayFirmaDurumEtiketi("ilgileniliyor")).toBe(
      "Firma sizinle ilgileniyor",
    );
    expect(adayFirmaDurumEtiketi("reddedildi")).toBe("Kapandı");
    expect(adayFirmaDurumEtiketi("bilinmeyen")).toBe("Durumu güncelleniyor");
  });

  it("durum başına eylemler", () => {
    expect(adayFirmaEylemleri("onerildi")).toEqual({
      ilgiGoster: true,
      geriCek: false,
      kabulVeyaRed: false,
    });
    expect(adayFirmaEylemleri("genc_ilgilendi").geriCek).toBe(true);
    expect(adayFirmaEylemleri("ilgileniliyor").kabulVeyaRed).toBe(true);
    expect(adayFirmaEylemleri("kabul_edildi")).toEqual({
      ilgiGoster: false,
      geriCek: false,
      kabulVeyaRed: false,
    });
  });
});
