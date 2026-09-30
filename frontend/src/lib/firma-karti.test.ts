import { describe, expect, it } from "vitest";

import type { FirmaKartiYaniti, MeYaniti } from "@/lib/api";
import {
  degisenKartAlanlari,
  firmaKartiCagrisi,
  formuKartaCevir,
  kartFormunuDogrula,
  kartiForma,
  yetkinlikleriAyir,
} from "@/lib/firma-karti";

const KART: FirmaKartiYaniti = {
  id: "k",
  kurum_id: "f",
  firma_adi: "Market X",
  ne_yapiyoruz: "Talep tahmini yazılımı",
  yetkinlikler: ["talep tahmini", "stok"],
  onceki_isler: null,
  aranan_isbirligi: "Bir market zinciri",
  isbirligi_turleri: ["pilot"],
  versiyon: 2,
  embedding_var: true,
  olusturma_tarihi: "2026-09-30T10:00:00Z",
};

describe("yetkinlikleriAyir", () => {
  it("virgül ve satır sonuyla ayırır, tekrarı atar", () => {
    expect(yetkinlikleriAyir(" Veri  analizi, veri analizi\nML,, ")).toEqual([
      "Veri analizi",
      "ML",
    ]);
  });

  it("Türkçe büyük/küçük harfi tanır", () => {
    expect(yetkinlikleriAyir("İhracat, ihracat")).toEqual(["İhracat"]);
  });
});

describe("form dönüşümü", () => {
  it("kart forma ve geri, değişiklik yoksa boş gövde", () => {
    const form = kartiForma(KART);
    expect(form.yetkinlikler).toBe("talep tahmini, stok");
    expect(degisenKartAlanlari(KART, form)).toEqual({});
  });

  it("yalnızca değişen alanlar gönderilir", () => {
    const form = {
      ...kartiForma(KART),
      yetkinlikler: "talep tahmini, stok, fiyatlama",
      aranan_isbirligi: " ",
      isbirligi_turleri: ["yatirim", "pilot"],
    };
    expect(degisenKartAlanlari(KART, form)).toEqual({
      yetkinlikler: ["talep tahmini", "stok", "fiyatlama"],
      aranan_isbirligi: null,
      isbirligi_turleri: ["pilot", "yatirim"],
    });
  });

  it("taslaktan form: boş alanlar boş metin", () => {
    const form = kartiForma({
      ne_yapiyoruz: null,
      yetkinlikler: [],
      onceki_isler: null,
      aranan_isbirligi: null,
      isbirligi_turleri: [],
    });
    expect(formuKartaCevir(form).onceki_isler).toBeNull();
    expect(kartFormunuDogrula(form)).toEqual([
      "Firmanızın ne yaptığını yazın.",
      "En az bir yetkinlik yazın.",
    ]);
  });

  it("yetkinlik sayısı sınırı", () => {
    const form = {
      ...kartiForma(KART),
      yetkinlikler: Array.from({ length: 16 }, (_, i) => `y${i}`).join(","),
    };
    expect(kartFormunuDogrula(form)).toEqual([
      "En çok 15 yetkinlik yazabilirsiniz.",
    ]);
  });
});

describe("firmaKartiCagrisi", () => {
  const hesap = (ek: Partial<MeYaniti>): MeYaniti => ({
    hesap_id: "h",
    email: "a@b.com",
    rol: "kurum",
    ad: "Market X",
    kullanici_id: null,
    kurum_id: "f",
    yetenek_karti: null,
    ihtiyac_kartlari: [],
    okunmamis_bildirim: 0,
    eksik_profil_alanlari: [],
    kvkk_onayli: true,
    firma_karti_var: false,
    ...ek,
  });

  it("kartı olmayan firmaya çağrı, olana ve gence yok", () => {
    expect(firmaKartiCagrisi(hesap({}))).toContain("Firma kartınızı oluşturun");
    expect(firmaKartiCagrisi(hesap({ firma_karti_var: true }))).toBeNull();
    expect(firmaKartiCagrisi(hesap({ rol: "genc" }))).toBeNull();
  });
});
