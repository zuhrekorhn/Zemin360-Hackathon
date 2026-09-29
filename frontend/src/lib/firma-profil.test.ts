import { describe, expect, it } from "vitest";

import type { FirmaProfil, MeYaniti } from "@/lib/api";
import {
  BOS_FIRMA_FORMU,
  firmaFormunuDogrula,
  firmaProfilBandi,
  firmaProfilindenForma,
  formuFirmaProfilineCevir,
  onaydaFirmaBilgisiSorulmali,
} from "@/lib/firma-profil";

const GECERLI = {
  ...BOS_FIRMA_FORMU,
  tur: "girisim" as const,
  sektor: " Perakende ",
  sehir: "İstanbul",
};

function hesap(ek: Partial<MeYaniti> = {}): MeYaniti {
  return {
    hesap_id: "h",
    email: "a@b.com",
    rol: "kurum",
    ad: "Market X",
    kullanici_id: null,
    kurum_id: "k",
    yetenek_kartlari: [],
    ihtiyac_kartlari: [],
    okunmamis_bildirim: 0,
    eksik_profil_alanlari: [],
    kvkk_onayli: true,
    ...ek,
  };
}

describe("firmaFormunuDogrula", () => {
  it("zorunlu alanlar dolu ise geçerli", () => {
    expect(firmaFormunuDogrula(GECERLI, 2026)).toEqual([]);
  });

  it("zorunlu alanları ister", () => {
    expect(firmaFormunuDogrula(BOS_FIRMA_FORMU, 2026)).toEqual([
      "Firma türünü seçin.",
      "Sektörü yazın.",
      "Şehri seçin.",
    ]);
  });

  it("kuruluş yılı aralıkta olmalı", () => {
    expect(
      firmaFormunuDogrula({ ...GECERLI, kurulus_yili: "2027" }, 2026),
    ).toEqual(["Kuruluş yılı 1900 ile 2026 arasında olmalı."]);
    expect(
      firmaFormunuDogrula({ ...GECERLI, kurulus_yili: "abc" }, 2026),
    ).toHaveLength(1);
    expect(
      firmaFormunuDogrula({ ...GECERLI, kurulus_yili: "2019" }, 2026),
    ).toEqual([]);
  });

  it("web sitesi ve tanıtım uzunluğu", () => {
    expect(
      firmaFormunuDogrula({ ...GECERLI, web_sitesi: "market x" }, 2026),
    ).toEqual(["Web sitesi geçerli bir adres değil."]);
    expect(
      firmaFormunuDogrula({ ...GECERLI, web_sitesi: "marketx.com" }, 2026),
    ).toEqual([]);
    expect(
      firmaFormunuDogrula({ ...GECERLI, tanitim: "a".repeat(301) }, 2026),
    ).toEqual(["Tanıtım en çok 300 karakter olmalı."]);
  });
});

describe("formuFirmaProfilineCevir", () => {
  it("boşlukları kırpar, boşları null yapar", () => {
    expect(
      formuFirmaProfilineCevir({ ...GECERLI, kurulus_yili: "2019" }),
    ).toEqual({
      tur: "girisim",
      sektor: "Perakende",
      sehir: "İstanbul",
      web_sitesi: null,
      calisan_araligi: null,
      kurulus_yili: 2019,
      tanitim: null,
      yetkili_ad: null,
      yetkili_gorev: null,
    });
  });

  it("kayıtlı profil forma ve geri döner", () => {
    const profil: FirmaProfil = {
      ad: "Market X",
      email: "a@marketx.com",
      tur: "kurumsal",
      sektor: "Perakende",
      sehir: "İzmir",
      web_sitesi: "https://marketx.com",
      calisan_araligi: "250+",
      kurulus_yili: 1990,
      tanitim: "Zincir market.",
      yetkili_ad: "Ayşe",
      yetkili_gorev: "İnovasyon müdürü",
      kvkk_onay_tarihi: null,
      eksik_alanlar: [],
    };
    const { ad, email, kvkk_onay_tarihi, eksik_alanlar, ...geri } = profil;
    void ad;
    void email;
    void kvkk_onay_tarihi;
    void eksik_alanlar;
    expect(formuFirmaProfilineCevir(firmaProfilindenForma(profil))).toEqual(
      geri,
    );
  });
});

describe("firmaProfilBandi", () => {
  it("tam profilde bant yok", () => {
    expect(firmaProfilBandi(hesap())).toBeNull();
  });

  it("gence ve GİRVAK'a firma bandı gösterilmez", () => {
    expect(
      firmaProfilBandi(
        hesap({ rol: "genc", eksik_profil_alanlari: ["sehir"] }),
      ),
    ).toBeNull();
    expect(firmaProfilBandi(hesap({ rol: "girvak", kvkk_onayli: false }))).toBe(
      null,
    );
  });

  it("eksikleri ve KVKK'yı sayar", () => {
    expect(
      firmaProfilBandi(
        hesap({ eksik_profil_alanlari: ["tur", "sehir"], kvkk_onayli: false }),
      ),
    ).toBe(
      "Profilinizi tamamlayın: profilinizde eksik bilgi var (firma türü, şehir); KVKK aydınlatma metnini onaylamadınız.",
    );
  });
});

describe("onaydaFirmaBilgisiSorulmali", () => {
  it("yalnızca sektör ya da şehir eksikse", () => {
    expect(onaydaFirmaBilgisiSorulmali([])).toBe(false);
    expect(onaydaFirmaBilgisiSorulmali(["tur"])).toBe(false);
    expect(onaydaFirmaBilgisiSorulmali(["sehir"])).toBe(true);
    expect(onaydaFirmaBilgisiSorulmali(["sektor", "tur"])).toBe(true);
  });
});
