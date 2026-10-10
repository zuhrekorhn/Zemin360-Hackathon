import { describe, expect, it } from "vitest";

import type { ServisDurumu } from "@/lib/api";
import {
  erisimEtiketi,
  platformEtiketi,
  servisEtiketi,
  servisOzeti,
  servisSayilari,
  sureYaz,
  yuzdeYaz,
} from "@/lib/gozlem";

function servis(ek: Partial<ServisDurumu>): ServisDurumu {
  return {
    servis: "eposta",
    kip: "resend",
    basari_sayisi: 0,
    hata_sayisi: 0,
    son_basari: null,
    son_hata: null,
    son_hata_turu: null,
    ...ek,
  };
}

describe("etiketler", () => {
  it("bilinen değerler Türkçe, bilinmeyen olduğu gibi", () => {
    expect(erisimEtiketi("giris_gerekli")).toBe("Giriş istedi");
    expect(erisimEtiketi("yeni_durum")).toBe("yeni_durum");
    expect(platformEtiketi("web")).toBe("Diğer siteler");
    expect(platformEtiketi("youtube")).toBe("YouTube");
    expect(servisEtiketi("oauth")).toBe("Hesap bağlama (GitHub vb.)");
    expect(servisEtiketi("baska")).toBe("baska");
  });
});

describe("yuzdeYaz ve sureYaz", () => {
  it("oranı yüzdeye, süreyi okunur birime çevirir", () => {
    expect(yuzdeYaz(0.8)).toBe("%80");
    expect(yuzdeYaz(0.6667)).toBe("%67");
    expect(sureYaz(850)).toBe("850 ms");
    expect(sureYaz(3200)).toBe("3,2 sn");
  });
});

describe("servisOzeti", () => {
  it("kapalı bayrak sorun değildir", () => {
    expect(servisOzeti(servis({ kip: "kapali" }))).toEqual({
      etiket: "Kapalı",
      sorunlu: false,
    });
  });

  it("son çağrı hataysa sorunlu, sonradan başarı gelirse çalışıyor", () => {
    const hataliSon = servis({
      basari_sayisi: 5,
      hata_sayisi: 1,
      son_basari: "2026-10-05T10:00:00Z",
      son_hata: "2026-10-05T11:00:00Z",
    });
    expect(servisOzeti(hataliSon)).toEqual({
      etiket: "Son denemede hata",
      sorunlu: true,
    });
    const duzeldi = { ...hataliSon, son_basari: "2026-10-05T12:00:00Z" };
    expect(servisOzeti(duzeldi)).toEqual({
      etiket: "Çalışıyor",
      sorunlu: false,
    });
  });

  it("hiç çağrı yoksa henüz çağrılmadı", () => {
    expect(servisOzeti(servis({}))).toEqual({
      etiket: "Henüz kullanılmadı",
      sorunlu: false,
    });
  });

  it("sayılar", () => {
    expect(servisSayilari(servis({ basari_sayisi: 12, hata_sayisi: 1 }))).toBe(
      "12 başarılı, 1 hatalı",
    );
  });
});
