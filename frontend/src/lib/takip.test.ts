import { describe, expect, it } from "vitest";

import type { IsbirligiDetayi, MilestoneYaniti } from "@/lib/api";
import {
  adimGorunumu,
  ilerlemeMetni,
  planOnayGorunumu,
  tarafim,
} from "@/lib/takip";

const DETAY = {
  genc_adi: "Elif",
  // Karşı tarafın adı aday tarafından okunur (genç ya da ortak firma).
  aday_adi: "Elif",
  kurum_adi: "Koop",
  genc_plan_onayi: null,
  kurum_plan_onayi: null,
} as IsbirligiDetayi;

function adim(genc: boolean, kurum: boolean): MilestoneYaniti {
  return {
    genc_isaret: genc ? "2026-10-01T10:00:00Z" : null,
    kurum_isaret: kurum ? "2026-10-01T10:00:00Z" : null,
  } as MilestoneYaniti;
}

describe("tarafim", () => {
  it("genç ve kurum taraftır, GİRVAK değildir", () => {
    expect(tarafim("genc")).toBe("genc");
    expect(tarafim("kurum")).toBe("kurum");
    expect(tarafim("girvak")).toBeNull();
  });
});

describe("adimGorunumu", () => {
  it("iki işaret: tamamlandı", () => {
    const g = adimGorunumu(adim(true, true), DETAY, "genc");
    expect(g.tamamlandi).toBe(true);
    expect(g.siraBende).toBe(false);
  });

  it("ben işaretledim: karşı tarafın onayı bekleniyor, geri alabilirim", () => {
    const g = adimGorunumu(adim(true, false), DETAY, "genc");
    expect(g.benIsaretledim).toBe(true);
    expect(g.metin).toContain("Koop tarafının onayı bekleniyor");
  });

  it("karşı taraf işaretledi: sıra bende", () => {
    const g = adimGorunumu(adim(true, false), DETAY, "kurum");
    expect(g.siraBende).toBe(true);
    expect(g.metin).toBe("Elif tamamlandı dedi; senin onayın bekleniyor.");
  });

  it("firmaya siz diye yazar", () => {
    const g = adimGorunumu(adim(true, false), DETAY, "kurum", "siz");
    expect(g.metin).toBe("Elif tamamlandı dedi; sizin onayınız bekleniyor.");
  });

  it("GİRVAK yönsüz görür, eylemi yoktur", () => {
    const g = adimGorunumu(adim(false, true), DETAY, null);
    expect(g.metin).toContain("Koop tamamlandı dedi");
    expect(g.benIsaretledim || g.siraBende).toBe(false);
  });
});

describe("planOnayGorunumu", () => {
  it("kimse onaylamadı: düzenlemenin onayları sıfırladığını söyler", () => {
    expect(planOnayGorunumu(DETAY, "genc").metin).toContain("sıfırlanır");
  });

  it("karşı taraf onayladı: sıra bende", () => {
    const d = { ...DETAY, kurum_plan_onayi: "2026-10-01T10:00:00Z" };
    const g = planOnayGorunumu(d, "genc");
    expect(g.benOnayladim).toBe(false);
    expect(g.metin).toBe("Koop planı onayladı; senin onayın bekleniyor.");
  });

  it("ben onayladım", () => {
    const d = { ...DETAY, genc_plan_onayi: "2026-10-01T10:00:00Z" };
    expect(planOnayGorunumu(d, "genc").benOnayladim).toBe(true);
  });
});

describe("ilerlemeMetni", () => {
  it("plan durumları ve aktif ilerleme", () => {
    const bos = { tamamlanan: 0, toplam: 0, geciken: 0 };
    expect(ilerlemeMetni("plan_bekliyor", bos)).toBe("Plan henüz yok");
    expect(ilerlemeMetni("plan_bekliyor", { ...bos, toplam: 4 })).toBe(
      "Plan taslağı · 4 adım",
    );
    expect(
      ilerlemeMetni("aktif", { tamamlanan: 2, toplam: 4, geciken: 1 }),
    ).toBe("2/4 adım · 1 gecikmiş");
    expect(
      ilerlemeMetni("tamamlandi", { tamamlanan: 4, toplam: 4, geciken: 0 }),
    ).toBe("4/4 adım");
  });
});
