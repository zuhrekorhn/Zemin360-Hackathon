import { describe, expect, it } from "vitest";

import {
  bildirimHedefi,
  giristenSonra,
  guvenliSonra,
  kayittanSonra,
  panelYolu,
} from "@/lib/yonlendirme";

describe("panelYolu", () => {
  it("her rolün kendi paneli var", () => {
    expect(panelYolu("genc")).toBe("/genc");
    expect(panelYolu("kurum")).toBe("/kurum");
    expect(panelYolu("girvak")).toBe("/girvak");
  });
});

describe("guvenliSonra", () => {
  it("site içi yolu sorgusuyla birlikte kabul eder", () => {
    expect(guvenliSonra("/kart/123")).toBe("/kart/123");
    expect(guvenliSonra("/kurum/oneriler?ihtiyac=abc")).toBe(
      "/kurum/oneriler?ihtiyac=abc",
    );
  });

  it("açık yönlendirmeyi reddeder", () => {
    expect(guvenliSonra("https://kotu.site")).toBeNull();
    expect(guvenliSonra("//kotu.site")).toBeNull();
    expect(guvenliSonra("/\\kotu.site")).toBeNull();
    expect(guvenliSonra("kart/123")).toBeNull();
  });

  it("boşu ve giriş/kayıt sayfalarını reddeder (döngü olmasın)", () => {
    expect(guvenliSonra(null)).toBeNull();
    expect(guvenliSonra("")).toBeNull();
    expect(guvenliSonra("/giris?sonra=/genc")).toBeNull();
    expect(guvenliSonra("/kayit")).toBeNull();
  });
});

describe("giristenSonra", () => {
  it("güvenli sonra varsa oraya, yoksa panele", () => {
    expect(giristenSonra("genc", "/kesif")).toBe("/kesif");
    expect(giristenSonra("kurum", "//kotu.site")).toBe("/kurum");
    expect(giristenSonra("girvak", null)).toBe("/girvak");
  });
});

describe("bildirimHedefi", () => {
  it("bildirimi alan rolün paneline, ilgili bölüme götürür", () => {
    expect(bildirimHedefi("ilgi")).toBe("/genc#ilgiler");
    expect(bildirimHedefi("referans_yaniti")).toBe("/genc#kartlar");
    expect(bildirimHedefi("yeni_oneri")).toBe("/kurum#ihtiyaclar");
    expect(bildirimHedefi("kabul")).toBe("/kurum#isbirlikleri");
    expect(bildirimHedefi("red")).toBe("/kurum#oneriler");
  });

  it("bilinmeyen tür bildirim sayfasında kalır", () => {
    expect(bildirimHedefi("canlilik")).toBe("/bildirimler");
  });
});

describe("bildirimHedefi — iş birliği", () => {
  it("Takip bildirimi ve kabul, iş birliği sayfasına götürür", () => {
    expect(bildirimHedefi("adim_isaretlendi", "abc")).toBe("/isbirligi/abc");
    expect(bildirimHedefi("plan_onerildi", "abc")).toBe("/isbirligi/abc");
    expect(bildirimHedefi("kabul", "abc")).toBe("/isbirligi/abc");
  });

  it("iş birliği kimliği yoksa eski hedefler geçerli", () => {
    expect(bildirimHedefi("kabul", null)).toBe("/kurum#isbirlikleri");
    expect(bildirimHedefi("ilgi", "abc")).toBe("/genc#ilgiler");
  });
});

describe("bildirimHedefi — Canlılık", () => {
  it("iş birliği hatırlatmaları iş birliği sayfasına", () => {
    expect(bildirimHedefi("adim_gecikti", "abc")).toBe("/isbirligi/abc");
    expect(bildirimHedefi("plan_onaysiz", "abc")).toBe("/isbirligi/abc");
    expect(bildirimHedefi("isbirligi_hareketsiz", "abc")).toBe(
      "/isbirligi/abc",
    );
  });

  it("yanıtsız ilginin son hatırlatması alıcının rolüne göre", () => {
    expect(bildirimHedefi("ilgi_yanitsiz_2", null, "genc")).toBe(
      "/genc#ilgiler",
    );
    expect(bildirimHedefi("ilgi_yanitsiz_2", null, "kurum")).toBe(
      "/kurum#oneriler",
    );
  });

  it("öneri ve fırsat", () => {
    expect(bildirimHedefi("oneri_bekliyor")).toBe("/kurum#ihtiyaclar");
    // Genç akışında genç fırsatları görüyor (plan § 0, karar 1).
    expect(bildirimHedefi("yeni_firsat")).toBe("/genc#firsatlar");
    expect(bildirimHedefi("genc_ilgi")).toBe("/kurum#ihtiyaclar");
    expect(bildirimHedefi("firsat_kapandi")).toBe("/genc#ilgilerim");
    expect(bildirimHedefi("karsilikli_ilgi", "i1")).toBe("/isbirligi/i1");
    expect(bildirimHedefi("karsilikli_ilgi")).toBe("/genc#ilgilerim");
  });
});

describe("kayittanSonra", () => {
  it("genç onboarding için Keşif sohbetine gider", () => {
    expect(kayittanSonra("genc", null)).toBe("/kesif?ilk=1");
  });
  it("kurum paneline gider", () => {
    expect(kayittanSonra("kurum", null)).toBe("/kurum");
  });
  it("güvenli sonra öncelikli, güvensiz olan yok sayılır", () => {
    expect(kayittanSonra("genc", "/kart/1")).toBe("/kart/1");
    expect(kayittanSonra("genc", "//kotu.site")).toBe("/kesif?ilk=1");
  });
});
