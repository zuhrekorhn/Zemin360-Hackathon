import { describe, expect, it } from "vitest";

import { type AlanAdiIpucu, ipucuMetni } from "@/lib/firma-dogrulama";

describe("ipucuMetni", () => {
  it("yalnızca uyuşan alan adı olumlu", () => {
    const ipuclari: AlanAdiIpucu[] = [
      "uyusuyor",
      "uyusmuyor",
      "ucretsiz_eposta",
      "site_yok",
      "eposta_yok",
    ];
    expect(
      ipuclari.filter((ipucu) => ipucuMetni(ipucu, "ornek.com").olumlu),
    ).toEqual(["uyusuyor"]);
  });

  it("alan adını cümleye koyar", () => {
    expect(ipucuMetni("uyusuyor", "marketx.com").metin).toBe(
      "E-posta adresi (@marketx.com) web sitesiyle uyuşuyor.",
    );
    expect(ipucuMetni("ucretsiz_eposta", "gmail.com").metin).toContain(
      "gmail.com",
    );
  });
});
