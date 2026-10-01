import { describe, expect, it } from "vitest";

import {
  kalanSure,
  kodYonergesi,
  platformAdi,
  profilOrnegi,
  yontemEtiketi,
} from "@/lib/hesap-baglama";

describe("hesap bağlama metinleri", () => {
  it("platform adı ve örnek adres; bilinmeyen platform adıyla kalır", () => {
    expect(platformAdi("kisisel_site")).toBe("Kişisel site");
    expect(platformAdi("bilinmeyen")).toBe("bilinmeyen");
    expect(profilOrnegi("medium")).toBe("ör. medium.com/@kullaniciadin");
  });

  it("kod yönergesi platforma göre yeri söyler", () => {
    const metin = kodYonergesi("youtube", "z360-abcd1234");
    expect(metin).toContain("z360-abcd1234 kodunu YouTube kanal açıklamana ekle");
  });

  it("yöntem etiketi", () => {
    expect(yontemEtiketi("oauth")).toBe("Giriş yaparak bağlandı");
    expect(yontemEtiketi("elle")).toBe("GİRVAK doğruladı");
  });

  it("kalan süre", () => {
    const simdi = new Date("2026-10-02T10:00:00Z");
    expect(kalanSure("2026-10-04T09:30:00Z", simdi)).toBe("47 saat daha geçerli");
    expect(kalanSure("2026-10-02T10:30:00Z", simdi)).toBe("1 saatten az kaldı");
    expect(kalanSure("2026-10-02T09:00:00Z", simdi)).toBeNull();
  });
});
