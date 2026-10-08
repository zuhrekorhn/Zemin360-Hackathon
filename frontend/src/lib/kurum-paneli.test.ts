import { describe, expect, it } from "vitest";

import type { IsbirligiOzeti, KurumOnerisi, MeYaniti } from "@/lib/api";
import {
  adaySatirlari,
  firmaEksikAdimlari,
  ihtiyacSayilari,
  kurumBekleyenSayisi,
  kurumBekleyenleri,
  kurumOzetCumlesi,
  sayimMetni,
} from "@/lib/kurum-paneli";

const oneri = (
  id: string,
  durum: string,
  tarih: string,
  ihtiyac = "i1",
): KurumOnerisi =>
  ({
    eslesme_id: id,
    durum,
    son_aktivite_tarihi: tarih,
    ihtiyac_karti_id: ihtiyac,
    aday_adi: `Aday ${id}`,
    rol_alani: null,
  }) as KurumOnerisi;

const isbirligi = (id: string, durum: string, geciken = 0): IsbirligiOzeti =>
  ({ isbirligi_id: id, durum, ilerleme: { geciken } }) as IsbirligiOzeti;

describe("kurumBekleyenleri", () => {
  it("yalnızca firmanın yanıtını bekleyen işleri toplar", () => {
    const b = kurumBekleyenleri(
      [
        oneri("a", "genc_ilgilendi", "2026-10-02"),
        oneri("b", "onerildi", "2026-10-03"),
        oneri("c", "ilgileniliyor", "2026-10-04"),
      ],
      [
        isbirligi("x", "plan_bekliyor"),
        isbirligi("y", "aktif", 2),
        isbirligi("z", "aktif", 0),
        isbirligi("w", "tamamlandi"),
      ],
    );
    expect(b.ilgiler.map((o) => o.eslesme_id)).toEqual(["a"]);
    expect(b.planlar.map((i) => i.isbirligi_id)).toEqual(["x"]);
    expect(b.gecikenler.map((i) => i.isbirligi_id)).toEqual(["y"]);
    expect(kurumBekleyenSayisi(b)).toBe(3);
  });
});

describe("ihtiyacSayilari", () => {
  it("kapanmış eşleşmeleri saymaz, ilgiyi ayrı sayar", () => {
    const sayilar = ihtiyacSayilari([
      oneri("a", "onerildi", "2026-10-01", "i1"),
      oneri("b", "genc_ilgilendi", "2026-10-02", "i1"),
      oneri("c", "kapandi", "2026-10-03", "i1"),
      oneri("d", "reddedildi", "2026-10-03", "i1"),
      oneri("e", "onerildi", "2026-10-03", "i2"),
    ]);
    expect(sayilar.i1).toEqual({ aday: 2, ilgi: 1 });
    expect(sayilar.i2).toEqual({ aday: 1, ilgi: 0 });
  });

  it("sayım metni: aday yoksa boş", () => {
    expect(sayimMetni(undefined)).toBeNull();
    expect(sayimMetni({ aday: 0, ilgi: 0 })).toBeNull();
    expect(sayimMetni({ aday: 3, ilgi: 0 })).toBe("3 aday");
    expect(sayimMetni({ aday: 3, ilgi: 1 })).toBe("3 aday · 1 ilgi gösterdi");
  });
});

describe("adaySatirlari", () => {
  it("en son hareket önce, kapananlar sonda; etiket firma diliyle", () => {
    const satirlar = adaySatirlari([
      oneri("eski", "onerildi", "2026-10-01"),
      oneri("kapali", "kapandi", "2026-10-09"),
      oneri("yeni", "genc_ilgilendi", "2026-10-05"),
    ]);
    expect(satirlar.map((s) => s.anahtar)).toEqual(["yeni", "eski", "kapali"]);
    expect(satirlar[0]).toMatchObject({
      etiket: "İlgi gösterdi",
      baglanti: true,
      alt: "Firma",
      hedef: "/kurum/oneriler?ihtiyac=i1",
    });
    expect(satirlar[1].etiket).toBeNull();
    expect(satirlar[1].baglanti).toBe(false);
  });
});

describe("firmaEksikAdimlari", () => {
  const hesap = (ek: Partial<MeYaniti>) =>
    ({
      rol: "kurum",
      firma_karti_var: true,
      eksik_profil_alanlari: [],
      kvkk_onayli: true,
      ...ek,
    }) as MeYaniti;

  it("eksik yoksa boş", () => {
    expect(firmaEksikAdimlari(hesap({}))).toEqual([]);
  });

  it("firma kartı ve profil eksikleri ayrı satırlar", () => {
    const adimlar = firmaEksikAdimlari(
      hesap({ firma_karti_var: false, kvkk_onayli: false }),
    );
    expect(adimlar.map((a) => a.href)).toEqual([
      "/kurum/kart",
      "/kurum/profil",
    ]);
  });
});

describe("kurumOzetCumlesi", () => {
  it("en önemli durumu söyler", () => {
    expect(kurumOzetCumlesi(0, 0, null)).toMatch(/İlk ihtiyacınızı/);
    expect(kurumOzetCumlesi(2, 1, 4)).toBe("Yanıtınızı bekleyen 2 iş var.");
    expect(kurumOzetCumlesi(0, 1, 4)).toBe("İhtiyaçlarınıza uyan 4 aday var.");
    expect(kurumOzetCumlesi(0, 1, 0)).toMatch(/burada/);
  });
});
