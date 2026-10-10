import { describe, expect, it } from "vitest";

import { alicilarMetni, pasifSureMetni, turEtiketi } from "@/lib/canlilik";

describe("turEtiketi", () => {
  it("bilinen türler Türkçe etiketle, bilinmeyen olduğu gibi", () => {
    expect(turEtiketi("adim_gecikti")).toBe("Gecikmiş adım");
    expect(turEtiketi("yeni_firsat")).toBe("Gence yeni fırsat bildirimi");
    expect(turEtiketi("bilinmeyen")).toBe("bilinmeyen");
  });
});

describe("alicilarMetni", () => {
  it("tek ve iki alıcı", () => {
    expect(alicilarMetni(["kurum"])).toBe("firma");
    expect(alicilarMetni(["genc", "kurum"])).toBe("genç ve firma");
  });
});

describe("pasifSureMetni", () => {
  it("gecikmede hedeften, diğerlerinde hareketten beri", () => {
    expect(pasifSureMetni("adim_gecikti", 3)).toBe("hedef tarihi 3 gün geçti");
    expect(pasifSureMetni("oneri_bekliyor", 8)).toBe("8 gündür ilerleme yok");
  });
});
