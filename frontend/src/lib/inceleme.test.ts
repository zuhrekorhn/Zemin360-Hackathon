import { describe, expect, it } from "vitest";

import type { IncelemeSatiri } from "@/lib/api";
import { ayrintiSatirlari, kararEtiketleri, turEtiketi } from "@/lib/inceleme";

function satir(tur: string, ayrinti: Record<string, unknown>): IncelemeSatiri {
  return {
    id: "1",
    tur,
    durum: "acik",
    olusturma_tarihi: "2026-10-02T10:00:00Z",
    kapanma_tarihi: null,
    girvak_notu: null,
    genc_adi: "Elif",
    kart_id: null,
    somut_cikti_id: null,
    cikti_basligi: null,
    ayrinti,
  };
}

describe("inceleme metinleri", () => {
  it("türün etiketi, bilinmeyen tür için genel etiket", () => {
    expect(turEtiketi("itiraz_siniri")).toBe("İtiraz hakkı doldu");
    expect(turEtiketi("yeni_bir_tur")).toBe("İnceleme");
  });

  it("talepte onay/ret, sinyalde sorun yok / doğrulanamadı", () => {
    expect(kararEtiketleri("ad_degisikligi")).toEqual({
      kapandi: "Onayla",
      dogrulanamadi: "Reddet",
    });
    expect(kararEtiketleri("itiraz_siniri").kapandi).toBe("Sorun yok");
  });

  it("ayrıntı türe göre okunur", () => {
    expect(
      ayrintiSatirlari(
        satir("ad_degisikligi", {
          eski_ad: "Elif Yılmaz",
          yeni_ad: "Elif Kaya",
          gerekce: "Evlilik",
        }),
      ),
    ).toEqual(["Elif Yılmaz → Elif Kaya", "Gerekçe: Evlilik"]);
    expect(
      ayrintiSatirlari(satir("itiraz_siniri", { itiraz_notlari: ["a", 3] })),
    ).toEqual(["İtiraz notu: a"]);
    expect(ayrintiSatirlari(satir("belge_tutarsiz", { x: 1 }))).toEqual([]);
  });
});
