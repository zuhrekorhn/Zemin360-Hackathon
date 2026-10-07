import { describe, expect, it } from "vitest";

import type { GuvenSkoru } from "@/lib/api";
import { siradakiAdim } from "@/lib/calisma";

const skor = (k: number | null, s: number | null, r: number | null, ref: number | null) =>
  ({
    kanit_orijinalligi: k,
    sonuc_olculebilirligi: s,
    rol_netligi: r,
    ucuncu_taraf_onayi: ref,
    gerekce_metni: null,
  }) as GuvenSkoru;

const tur = (girdi: Parameters<typeof siradakiAdim>[0]) => siradakiAdim(girdi)?.tur ?? null;

describe("siradakiAdim", () => {
  it("kanıt da referans da yoksa önce kanıt", () => {
    expect(tur({ kanitSayisi: 0, referansSayisi: 0, skor: null })).toBe("kanit");
  });

  it("kanıt var ama değerlendirilmemişse adım yok (kanıt bölümü kendi düğmesini gösterir)", () => {
    expect(tur({ kanitSayisi: 1, referansSayisi: 0, skor: null })).toBeNull();
  });

  it("ekrandaki örnek: Kanıt Güçlü, Sonuç Eksik → sonucu ekle", () => {
    expect(tur({ kanitSayisi: 1, referansSayisi: 1, skor: skor(3, 0, 3, 3) })).toBe("sonuc");
  });

  it("sıra: sonuç, pay, kanıt, referans", () => {
    expect(tur({ kanitSayisi: 1, referansSayisi: 0, skor: skor(1, 2, 1, null) })).toBe("rol");
    expect(tur({ kanitSayisi: 1, referansSayisi: 0, skor: skor(1, 2, 2, null) })).toBe("kanit");
    expect(tur({ kanitSayisi: 1, referansSayisi: 0, skor: skor(2, 2, 2, null) })).toBe("referans");
  });

  it("referans istenmişse (yanıt beklense de) yeniden önerilmez; hepsi yeterliyse adım yok", () => {
    expect(tur({ kanitSayisi: 1, referansSayisi: 1, skor: skor(2, 2, 2, null) })).toBeNull();
    expect(tur({ kanitSayisi: 1, referansSayisi: 0, skor: skor(3, 2, 2, 3) })).toBeNull();
  });

  it("değerlendirilmemiş başlık (—) zayıf sayılmaz", () => {
    expect(tur({ kanitSayisi: 1, referansSayisi: 1, skor: skor(null, null, 2, 3) })).toBeNull();
  });
});
