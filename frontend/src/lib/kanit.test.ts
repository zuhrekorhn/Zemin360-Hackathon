import { describe, expect, it } from "vitest";

import type { GuvenSkoru, KanitParcasi } from "@/lib/api";

import {
  degerlendirildiMi,
  dosyaBoyutu,
  dosyaParcalari,
  girvakIncelemesiMetni,
  kanitAdresi,
  kanitLinkleri,
  okunamayanSecenekleri,
} from "./kanit";

const skor = (degisiklik: Partial<GuvenSkoru> = {}): GuvenSkoru => ({
  kanit_orijinalligi: null,
  sonuc_olculebilirligi: null,
  rol_netligi: null,
  ucuncu_taraf_onayi: null,
  gerekce_metni: null,
  ...degisiklik,
});

describe("kanitAdresi", () => {
  it("şemasız linke https ekler, şemalıyı korur", () => {
    expect(kanitAdresi("github.com/elif/x")).toBe("https://github.com/elif/x");
    expect(kanitAdresi("//github.com/x")).toBe("https://github.com/x");
    expect(kanitAdresi("http://ornek.org")).toBe("http://ornek.org");
  });
});

describe("kanitLinkleri", () => {
  it("yalnızca adresi olan link parçalarını, sırasıyla verir", () => {
    const linkler = kanitLinkleri([
      { id: "1", tur: "link", url: "a.org" },
      { id: "2", tur: "dosya", url: null },
      { id: "3", tur: "link", url: "b.org" },
    ]);
    expect(linkler.map((p) => p.url)).toEqual(["a.org", "b.org"]);
  });
});

describe("degerlendirildiMi", () => {
  it("gösterge yoksa ya da yalnızca referans doluysa hayır", () => {
    expect(degerlendirildiMi(null)).toBe(false);
    expect(degerlendirildiMi(skor({ ucuncu_taraf_onayi: 3 }))).toBe(false);
  });

  it("kanıt, sonuç ya da rolden biri doluysa evet (0 da bir sonuçtur)", () => {
    expect(degerlendirildiMi(skor({ kanit_orijinalligi: 0 }))).toBe(true);
    expect(degerlendirildiMi(skor({ rol_netligi: 2 }))).toBe(true);
  });
});

describe("dosya parçaları", () => {
  const parca = (
    tur: string,
    ek: Partial<KanitParcasi> = {},
  ): KanitParcasi => ({
    id: tur,
    tur,
    url: tur === "link" ? "github.com/x" : null,
    ...ek,
  });

  it("dosya ve görseli ayırır, boyutu okunur yazar", () => {
    expect(
      dosyaParcalari([parca("link"), parca("dosya"), parca("gorsel")]).map(
        (p) => p.tur,
      ),
    ).toEqual(["dosya", "gorsel"]);
    expect(dosyaBoyutu(512)).toBe("1 KB");
    expect(dosyaBoyutu(340 * 1024)).toBe("340 KB");
    expect(dosyaBoyutu(1.25 * 1024 * 1024)).toBe("1,3 MB");
    expect(dosyaBoyutu(null)).toBeNull();
  });

  it("okunamayan linke duruma göre seçenek kutusu, okunana hiçbir şey", () => {
    expect(okunamayanSecenekleri(parca("link", { erisim: "acik" }))).toBeNull();
    expect(
      okunamayanSecenekleri(parca("dosya", { erisim: "icerik_yok" })),
    ).toBeNull();
    const drive = okunamayanSecenekleri(
      parca("link", {
        erisim: "giris_gerekli",
        url: "https://docs.google.com/d/1",
      }),
    );
    expect(drive?.mesaj).toContain("Bağlantıya sahip olan herkes");
    const linkedin = okunamayanSecenekleri(
      parca("link", { erisim: "giris_gerekli", url: "linkedin.com/in/x" }),
    );
    expect(linkedin?.secenekler).toContain("PDF olarak yükle");
    expect(
      okunamayanSecenekleri(parca("link", { erisim: "engellendi" }))
        ?.hesapBagla,
    ).toBe(true);
    expect(
      okunamayanSecenekleri(parca("link", { erisim: "bulunamadi" }))?.mesaj,
    ).toBe("Bu adreste bir sayfa yok.");
  });

  it("e-Devlet incelemesi cümlesi", () => {
    expect(girvakIncelemesiMetni("bekliyor")).toContain("incelemesinde");
    expect(girvakIncelemesiMetni("onaylandi")).toContain("doğruladı");
    expect(girvakIncelemesiMetni(null)).toBeNull();
  });
});
