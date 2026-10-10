import { describe, expect, it } from "vitest";

import {
  alicilarMetni,
  hedefBasligi,
  hedefYuzdesi,
  pasifSureMetni,
  turEtiketi,
} from "@/lib/canlilik";

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

describe("hedefYuzdesi", () => {
  it("oran, yuvarlama ve tavan", () => {
    expect(hedefYuzdesi(0, 80)).toBe(0);
    expect(hedefYuzdesi(20, 80)).toBe(25);
    expect(hedefYuzdesi(1, 3)).toBe(33);
    expect(hedefYuzdesi(12, 10)).toBe(100); // hedef aşıldı: çizgi taşmaz
    expect(hedefYuzdesi(3, 0)).toBe(0);
  });
});

describe("hedefBasligi", () => {
  it("programın kendi adıyla", () => {
    expect(hedefBasligi(80, "startup başvurusu")).toBe("80 startup başvurusu");
  });
});
