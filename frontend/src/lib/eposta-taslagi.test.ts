import { describe, expect, it } from "vitest";

import {
  gmailAdresi,
  MAILTO_SINIRI,
  type TaslakGirdisi,
  epostaTaslagi,
  kisalt,
  taslakYonu,
} from "@/lib/eposta-taslagi";

const TEMEL: Omit<TaslakGirdisi, "yon"> = {
  gonderenAdi: "Anadolu Tazele",
  aliciAdi: "Elif Yılmaz",
  problem: "Soğuk zincirde sıcaklık takibi",
  basariKriteri: "Sevkiyat kaybını %10 azaltmak.",
  calisma: "Sensör paneli",
};

function govde(girdi: TaslakGirdisi): string {
  const { href } = epostaTaslagi(girdi, "a@b.com");
  return decodeURIComponent(href.split("&body=")[1]);
}

describe("taslakYonu", () => {
  it("gönderen ilan sahibiyse ilan-*, aday tarafıysa *-ilan", () => {
    expect(taslakYonu("genc", "genc")).toBe("ilan-genc");
    expect(taslakYonu("genc", "firma")).toBe("ilan-firma");
    expect(taslakYonu("kurum", "genc")).toBe("genc-ilan");
    expect(taslakYonu("kurum", "firma")).toBe("firma-ilan");
  });
});

describe("epostaTaslagi", () => {
  it("firma → genç: sen diliyle, çalışma ve hedefle", () => {
    const g = govde({ ...TEMEL, yon: "ilan-genc" });
    expect(g).toContain("Merhaba Elif Yılmaz,");
    expect(g).toContain("Anadolu Tazele olarak Zemin360'ta");
    expect(g).toContain("“Sensör paneli” çalışman dikkatimizi çekti.");
    expect(g).toContain("Hedefimiz: Sevkiyat kaybını %10 azaltmak.");
    expect(g).toContain("Sana uygun gün");
  });

  it("genç → firma: siz diliyle", () => {
    const g = govde({
      ...TEMEL,
      yon: "genc-ilan",
      gonderenAdi: "Elif Yılmaz",
      aliciAdi: "Anadolu Tazele",
    });
    expect(g).toContain("Ben Elif Yılmaz.");
    expect(g).toContain("ihtiyacınız için eşleştik");
    expect(g).toContain("Size uygun bir zamanda");
    expect(g).not.toContain("Sana");
  });

  it("firma → firma: iki yönde de siz diliyle", () => {
    const ilan = govde({
      ...TEMEL,
      yon: "ilan-firma",
      aliciAdi: "Ayaz Sensör",
    });
    expect(ilan).toContain(
      "Ayaz Sensör olarak yaptıklarınız ihtiyacımızla örtüşüyor.",
    );
    const aday = govde({ ...TEMEL, yon: "firma-ilan" });
    expect(aday).toContain("ihtiyacınız için sizinle eşleştik");
    expect(aday).toContain("hedefinize nasıl katkı verebileceğimizi");
  });

  it("çalışma ve başarı ölçütü yoksa o cümleler düşer", () => {
    const g = govde({
      ...TEMEL,
      yon: "ilan-genc",
      calisma: null,
      basariKriteri: undefined,
    });
    expect(g).not.toContain("çalışman");
    expect(g).not.toContain("Hedefimiz");
  });

  it("hiçbir yönde 'pilot' kelimesi geçmez", () => {
    for (const yon of [
      "ilan-genc",
      "genc-ilan",
      "ilan-firma",
      "firma-ilan",
    ] as const) {
      const t = epostaTaslagi({ ...TEMEL, yon }, "a@b.com");
      expect(`${t.konu} ${t.govde}`.toLowerCase()).not.toContain("pilot");
    }
  });

  it("Türkçe harfleri ve satır sonlarını kodlar, adres olduğu gibi kalır", () => {
    const { href } = epostaTaslagi(
      { ...TEMEL, yon: "ilan-genc" },
      "elif@ornek.org",
    );
    expect(href.startsWith("mailto:elif@ornek.org?subject=")).toBe(true);
    expect(href).toContain("%0D%0A");
    expect(href).not.toMatch(/[ğüşıöçĞÜŞİÖÇ]/);
  });

  it("uzun metinde bağlantı sınırı aşılmaz; önce çalışma, sonra ölçüt düşer", () => {
    const uzun = "Çok uzun bir açıklama cümlesi ğüşiöç ".repeat(40);
    const t = epostaTaslagi(
      {
        ...TEMEL,
        yon: "ilan-genc",
        problem: uzun,
        basariKriteri: uzun,
        calisma: uzun,
      },
      "a@b.com",
    );
    expect(t.href.length).toBeLessThanOrEqual(MAILTO_SINIRI);
    const g = decodeURIComponent(t.href.split("&body=")[1]);
    expect(g).not.toContain("çalışman dikkatimizi");
    expect(g).not.toContain("Hedefimiz");
    expect(g).toContain("…");
  });

  it("sığan metin kırpılmaz", () => {
    const t = epostaTaslagi({ ...TEMEL, yon: "ilan-genc" }, "a@b.com");
    expect(t.href.length).toBeLessThanOrEqual(MAILTO_SINIRI);
    expect(decodeURIComponent(t.href)).toContain("çalışman dikkatimizi çekti");
  });
});

describe("kisalt", () => {
  it("kısa metni olduğu gibi bırakır, uzunu kelime sınırında keser", () => {
    expect(kisalt("kısa metin", 50)).toBe("kısa metin");
    const k = kisalt("bir iki üç dört beş altı yedi sekiz", 20);
    expect(k.endsWith("…")).toBe(true);
    expect(k.length).toBeLessThanOrEqual(20);
  });
});

describe("gmailAdresi", () => {
  it("alıcı, konu ve metni Gmail yazma adresine kodlar", () => {
    const govde = "Satır 1\nSatır 2";
    const adres = gmailAdresi("ayse@test.example", "Merhaba: tanışalım", govde);
    expect(
      adres.startsWith("https://mail.google.com/mail/?view=cm&fs=1&to="),
    ).toBe(true);
    const url = new URL(adres);
    expect(url.searchParams.get("to")).toBe("ayse@test.example");
    expect(url.searchParams.get("su")).toBe("Merhaba: tanışalım");
    expect(url.searchParams.get("body")).toBe(govde);
  });
});
