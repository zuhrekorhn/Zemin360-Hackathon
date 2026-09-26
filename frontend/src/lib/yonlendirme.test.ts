import { describe, expect, it } from "vitest";

import { giristenSonra, guvenliSonra, panelYolu } from "@/lib/yonlendirme";

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
