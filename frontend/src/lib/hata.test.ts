import { describe, expect, it } from "vitest";

import { ApiHatasi } from "@/lib/api";
import {
  HIZ_SINIRI_MESAJI,
  MESGUL_MESAJI,
  hatayaCevir,
  tekrarDenenebilirMi,
} from "@/lib/hata";

/**
 * Gerçek vaka: backend'in doğru cümlesi frontend'de eziliyordu ve mantık
 * iki sayfada kopyalanmıştı. 429 ücretli katmanda hız sınırı (dakikalık),
 * 503 sağlayıcı arızası; ikisi farklı cümle.
 */
describe("hatayaCevir", () => {
  it("429'da hız sınırı cümlesi, kota demez", () => {
    const hata = hatayaCevir(new ApiHatasi("İstek başarısız: 429", 429));
    expect(hata.metin).toBe(HIZ_SINIRI_MESAJI);
    expect(hata.metin).not.toMatch(/kota/i);
    expect(hata.kota).toBe(true);
  });

  it("503'te yoğunluk der — hız sınırından ayrı bir durum", () => {
    const hata = hatayaCevir(new ApiHatasi("İstek başarısız: 503", 503));
    expect(hata.metin).toBe(MESGUL_MESAJI);
    expect(hata.kota).toBe(false);
  });

  it("backend'in kendi cümlesini korur", () => {
    const backend =
      "Dil modeli şu an çok fazla istek alıyor. Biraz sonra tekrar dene. Sohbetin kayıtlı.";
    const hata = hatayaCevir(new ApiHatasi(backend, 429, backend));
    expect(hata.metin).toBe(backend);
    expect(hata.kota).toBe(true);
  });

  it("diğer durum kodlarında backend cümlesi aynen geçer", () => {
    const hata = hatayaCevir(
      new ApiHatasi("Taslak henüz hazır değil", 409, "Taslak henüz hazır değil"),
    );
    expect(hata).toEqual({ metin: "Taslak henüz hazır değil", kota: false });
  });

  it("ağ hatası mesajı olduğu gibi gösterilir", () => {
    const hata = hatayaCevir(new ApiHatasi("Backend'e ulaşılamadı (x)"));
    expect(hata.metin).toContain("ulaşılamadı");
  });

  it("ApiHatasi olmayan istisnada iç ayrıntı sızmaz", () => {
    const hata = hatayaCevir(new TypeError("undefined is not a function"));
    expect(hata.metin).not.toContain("undefined");
  });
});

describe("tekrarDenenebilirMi", () => {
  it("ağ hatası, 429 ve 503 geçici", () => {
    expect(tekrarDenenebilirMi(new ApiHatasi("ağ"))).toBe(true);
    expect(tekrarDenenebilirMi(new ApiHatasi("kota", 429))).toBe(true);
    expect(tekrarDenenebilirMi(new ApiHatasi("yoğun", 503))).toBe(true);
  });

  it("404 ve 409 kalıcı", () => {
    expect(tekrarDenenebilirMi(new ApiHatasi("yok", 404))).toBe(false);
    expect(tekrarDenenebilirMi(new ApiHatasi("durum", 409))).toBe(false);
  });
});
