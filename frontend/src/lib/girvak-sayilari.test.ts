import { describe, expect, it } from "vitest";

import type { GirvakSayilari } from "@/lib/api";
import { huniAdimlari, sayiGruplari } from "@/lib/girvak-sayilari";

const SAYILAR = {
  hesap: { genc: 5, kurum: 3, girvak: 1 },
  yetenek_karti: 4,
  ihtiyac_karti: 6,
  eslesme: {
    onerildi: 10,
    ilgileniliyor: 3,
    genc_ilgilendi: 2,
    kabul_edildi: 4,
    reddedildi: 1,
    kapandi: 0,
  },
  isbirligi: 4,
  isbirligi_durumlari: { plan_bekliyor: 1, aktif: 1, tamamlandi: 2 },
  kapanan_ihtiyaclar: {
    platformda_bulundu: 1,
    baska_yoldan_bulundu: 0,
    vazgecildi: 0,
    hatali_girildi: 0,
  },
  kirilim: {
    genc_firma: { oneri: 0, karsilikli_ilgi: 2, isbirligi: 3, tamamlanan: 1 },
    firma_firma: { oneri: 0, karsilikli_ilgi: 2, isbirligi: 1, tamamlanan: 1 },
  },
} as unknown as GirvakSayilari;

describe("huniAdimlari", () => {
  it("öneri bütün durumların toplamı; her adımda oranlar doğru", () => {
    const adimlar = huniAdimlari(SAYILAR);
    expect(adimlar.map((a) => [a.etiket, a.sayi])).toEqual([
      ["Önerildi", 20],
      ["İki taraf da ilgilendi", 4],
      ["İş birliği açıldı", 4],
      ["Tamamlandı", 2],
    ]);
    // Çubuk ilk adıma göre, yüzde bir öncekine göre.
    expect(adimlar.map((a) => a.genislik)).toEqual([100, 20, 20, 10]);
    expect(adimlar.map((a) => a.oncekineGore)).toEqual([null, 20, 100, 50]);
  });

  it("hiç öneri yoksa bölme hatası ve NaN yok", () => {
    const bos = huniAdimlari({
      ...SAYILAR,
      eslesme: {
        onerildi: 0,
        ilgileniliyor: 0,
        genc_ilgilendi: 0,
        kabul_edildi: 0,
        reddedildi: 0,
        kapandi: 0,
      },
      isbirligi: 0,
      isbirligi_durumlari: { plan_bekliyor: 0, aktif: 0, tamamlandi: 0 },
    });
    expect(bos.every((a) => a.sayi === 0 && a.genislik === 0)).toBe(true);
    expect(bos.map((a) => a.oncekineGore)).toEqual([null, null, null, null]);
    expect(JSON.stringify(bos)).not.toContain("NaN");
  });
});

describe("sayiGruplari", () => {
  it("dört grup ve brifteki 'Zemin360'ta bulundu' etiketi", () => {
    const gruplar = sayiGruplari(SAYILAR);
    expect(gruplar.map((g) => g.kimlik)).toEqual([
      "hesaplar",
      "eslesmeler",
      "kirilim",
      "kapananlar",
    ]);
    const kapanan = gruplar[3].ogeler.map((o) => o.etiket);
    expect(kapanan).toContain("Zemin360'ta bulundu");
    expect(kapanan).toContain("Yanlış ya da eksik girildi");
  });
});
