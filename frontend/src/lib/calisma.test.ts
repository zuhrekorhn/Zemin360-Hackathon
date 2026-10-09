import { describe, expect, it } from "vitest";

import type { GuvenSkoru } from "@/lib/api";
import {
  degerlendirmeBekliyor,
  eksikler,
  kalanCumlesi,
  kartDurumu,
  kartinSiradakiAdimi,
  siradakiAdim,
} from "@/lib/calisma";

const skor = (
  k: number | null,
  s: number | null,
  r: number | null,
  ref: number | null,
) =>
  ({
    kanit_orijinalligi: k,
    sonuc_olculebilirligi: s,
    rol_netligi: r,
    ucuncu_taraf_onayi: ref,
    gerekce_metni: null,
  }) as GuvenSkoru;

const turler = (girdi: Parameters<typeof eksikler>[0]) =>
  eksikler(girdi).map((e) => e.tur);

describe("eksikler", () => {
  it("kanıt da referans da yoksa yalnızca kanıt", () => {
    expect(turler({ kanitSayisi: 0, referansSayisi: 0, skor: null })).toEqual([
      "kanit",
    ]);
  });

  it("kanıt var ama değerlendirilmemişse öneri yok", () => {
    expect(turler({ kanitSayisi: 1, referansSayisi: 0, skor: null })).toEqual(
      [],
    );
  });

  it("ekrandaki Dernek örneği: link çalışmayı göstermiyor → önce doğru kanıt", () => {
    const liste = eksikler({
      kanitSayisi: 1,
      referansSayisi: 1,
      skor: skor(0, 0, 0, 3),
    });
    expect(liste.map((e) => e.tur)).toEqual(["kanit", "sonuc", "rol"]);
    expect(liste[0].etiket).toBe("Doğru kanıtı ekle");
  });

  it("ekrandaki Team ToDo örneği: yalnızca sonuç", () => {
    expect(
      turler({ kanitSayisi: 1, referansSayisi: 1, skor: skor(3, 0, 3, 3) }),
    ).toEqual(["sonuc"]);
  });

  it("referans istenmişse (yanıt beklense de) eksik sayılmaz; olumsuz yanıt eksik", () => {
    expect(
      turler({ kanitSayisi: 1, referansSayisi: 1, skor: skor(2, 2, 2, null) }),
    ).toEqual([]);
    expect(
      turler({ kanitSayisi: 1, referansSayisi: 1, skor: skor(2, 2, 2, 0) }),
    ).toEqual(["referans"]);
  });

  it("değerlendirilmemiş başlık (—) zayıf sayılmaz", () => {
    expect(
      turler({
        kanitSayisi: 1,
        referansSayisi: 1,
        skor: skor(null, null, 2, 3),
      }),
    ).toEqual([]);
  });

  it("siradakiAdim ilk eksik", () => {
    expect(
      siradakiAdim({
        kanitSayisi: 1,
        referansSayisi: 0,
        skor: skor(2, 1, 1, null),
      })?.tur,
    ).toBe("sonuc");
  });
});

describe("kartinSiradakiAdimi", () => {
  const dernek = eksikler({
    kanitSayisi: 1,
    referansSayisi: 1,
    skor: skor(0, 0, 0, 3),
  });
  const todo = eksikler({
    kanitSayisi: 1,
    referansSayisi: 1,
    skor: skor(3, 0, 3, 3),
  });

  it("en az eksiği kalan çalışma: en hızlı kazanç", () => {
    const adim = kartinSiradakiAdimi([
      { id: "d", baslik: "Dernek", eksikler: dernek },
      { id: "t", baslik: "Team ToDo", eksikler: todo },
    ]);
    expect(adim).toMatchObject({
      ciktiId: "t",
      calisma: "Team ToDo",
      eksikSayisi: 1,
    });
    expect(adim?.adim.tur).toBe("sonuc");
    expect(adim && kalanCumlesi(adim)).toMatch(/yalnızca sonuç eksik/);
  });

  it("eksik yoksa null; durum puan değil sayım", () => {
    expect(
      kartinSiradakiAdimi([{ id: "x", baslik: "X", eksikler: [] }]),
    ).toBeNull();
    expect(kartDurumu([dernek, todo, []])).toEqual({
      calisma: 3,
      tamam: 1,
      eksik: 4,
    });
  });
});

describe("degerlendirmeBekliyor", () => {
  const var_ = skor(2, 2, 2, null);

  it("göstergesi olmayan çalışma varsa bekliyor sayılır", () => {
    expect(
      degerlendirmeBekliyor([{ guven_skoru: var_ }, { guven_skoru: null }]),
    ).toBe(true);
  });

  it("hepsinin göstergesi varsa ya da çalışma yoksa beklemez", () => {
    expect(degerlendirmeBekliyor([{ guven_skoru: var_ }])).toBe(false);
    expect(degerlendirmeBekliyor([])).toBe(false);
  });
});
