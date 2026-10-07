import { describe, expect, it } from "vitest";

import type {
  BanaGelenIlgi,
  GencEslesmesi,
  IhtiyacKartiYaniti,
  IsbirligiOzeti,
} from "@/lib/api";
import {
  bekleyenSayisi,
  bekleyenler,
  eksikAdimlar,
  ozetCumlesi,
  surecler,
} from "@/lib/genc-paneli";

const ihtiyac = (ad: string) =>
  ({ kurum: { ad, dogrulandi: true } }) as unknown as IhtiyacKartiYaniti;

const ilgim = (
  id: string,
  durum: string,
  tarih: string,
  isbirligi: string | null = null,
) =>
  ({
    eslesme_id: id,
    durum,
    son_aktivite_tarihi: tarih,
    ihtiyac_karti: ihtiyac(`F-${id}`),
    isbirligi_id: isbirligi,
  }) as GencEslesmesi;

const gelen = (
  id: string,
  durum: string,
  tarih: string,
  isbirligi: string | null = null,
) =>
  ({
    eslesme_id: id,
    durum,
    son_aktivite_tarihi: tarih,
    ihtiyac_karti: ihtiyac(`F-${id}`),
    isbirligi_id: isbirligi,
  }) as BanaGelenIlgi;

const isbirligi = (id: string, durum: string, tarih: string, geciken = 0) =>
  ({
    isbirligi_id: id,
    durum,
    baslangic_tarihi: tarih,
    kurum_adi: `F-${id}`,
    ilerleme: { tamamlanan: 0, toplam: 3, geciken },
  }) as IsbirligiOzeti;

describe("bekleyenler", () => {
  it("firmanın ilgisi, onay bekleyen plan ve geciken adım", () => {
    const b = bekleyenler(
      [gelen("a", "ilgileniliyor", "1"), gelen("b", "kabul_edildi", "2", "i9")],
      [
        isbirligi("p", "plan_bekliyor", "1"),
        isbirligi("g", "aktif", "1", 2),
        isbirligi("s", "aktif", "1"),
      ],
    );
    expect(b.ilgiler.map((x) => x.eslesme_id)).toEqual(["a"]);
    expect(b.planlar.map((x) => x.isbirligi_id)).toEqual(["p"]);
    expect(b.gecikenler.map((x) => x.isbirligi_id)).toEqual(["g"]);
    expect(bekleyenSayisi(b)).toBe(3);
  });
});

describe("surecler", () => {
  it("tek liste, en yeni önce; iş birliğine dönüşen ilgi bir kez görünür", () => {
    const satirlar = surecler(
      [ilgim("x", "genc_ilgilendi", "2026-10-03"), ilgim("y", "kabul_edildi", "2026-10-04", "i1")],
      [gelen("z", "kapandi", "2026-10-01"), gelen("w", "ilgileniliyor", "2026-10-06")],
      [isbirligi("i1", "aktif", "2026-10-05")],
    );
    expect(satirlar.map((s) => [s.anahtar, s.etiket])).toEqual([
      ["i1", "Sürüyor"],
      ["x", "İlgin iletildi"],
      ["z", "Kapandı"],
    ]);
    expect(satirlar[0].hedef).toBe("/isbirligi/i1");
    expect(satirlar[1].geriCekilebilir?.eslesme_id).toBe("x");
    expect(satirlar[2].geriCekilebilir).toBeNull();
  });
});

describe("eksikAdimlar", () => {
  const kart = {
    id: "k1",
    rol_alani: "x",
    deneyim_seviyesi: "orta",
    kanit_bekleyen: false,
    embedding_var: true,
  };

  it("kart yoksa önce kart", () => {
    expect(
      eksikAdimlar({
        rol: "genc",
        yetenek_karti: null,
        eksik_profil_alanlari: [],
        kvkk_onayli: true,
      }).map((a) => a.href),
    ).toEqual(["/kesif"]);
  });

  it("tercihler karta, durum ve KVKK hesaba", () => {
    const adimlar = eksikAdimlar({
      rol: "genc",
      yetenek_karti: kart,
      eksik_profil_alanlari: ["sehir", "kariyer_durumu"],
      kvkk_onayli: false,
    });
    expect(adimlar.map((a) => [a.href, a.metin])).toEqual([
      ["/kart/k1#tercihler", "Çalışma tercihlerin eksik: şehir."],
      ["/profil", "Hesabında eksik: durum, KVKK onayı."],
    ]);
  });

  it("eksik yoksa ve firma ise boş", () => {
    const tam = {
      yetenek_karti: kart,
      eksik_profil_alanlari: [],
      kvkk_onayli: true,
    };
    expect(eksikAdimlar({ rol: "genc", ...tam })).toEqual([]);
    expect(eksikAdimlar({ rol: "kurum", ...tam })).toEqual([]);
  });
});

describe("ozetCumlesi", () => {
  it("önce kart, sonra bekleyen, sonra fırsat", () => {
    expect(ozetCumlesi(2, 3, false)).toMatch(/Kartını oluşturduğunda/);
    expect(ozetCumlesi(2, 3, true)).toBe("Yanıtını bekleyen 2 iş var.");
    expect(ozetCumlesi(0, 3, true)).toBe("Kartına uyan 3 fırsat var.");
    expect(ozetCumlesi(0, 0, true)).toMatch(/güçlendirdikçe/);
  });
});
