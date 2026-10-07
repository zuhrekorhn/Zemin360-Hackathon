import { describe, expect, it } from "vitest";

import type { MeYaniti } from "@/lib/api";
import {
  BOS_PROFIL_FORMU,
  type ProfilFormu,
  formuProfileCevir,
  kartTamamlamaCagrisi,
  onaydaProfilSorulmali,
  profilBandi,
  hesapGovdesi,
  hesapHatalari,
  profilFormunuDogrula,
  tercihGovdesi,
  tercihHatalari,
} from "@/lib/profil";

const GECERLI: ProfilFormu = {
  ...BOS_PROFIL_FORMU,
  sehir: "İstanbul",
  calisma_modelleri: ["hibrit"],
  kariyer_durumu: "ogrenci",
  musaitlikler: ["staj"],
};

describe("profilFormunuDogrula", () => {
  it("zorunlu alanlar dolu, opsiyoneller boşsa geçerli", () => {
    expect(profilFormunuDogrula(GECERLI, 2026)).toEqual([]);
  });

  it("boş form dört zorunlu alanı ister", () => {
    expect(profilFormunuDogrula(BOS_PROFIL_FORMU, 2026)).toHaveLength(4);
  });

  it("sınıf ve mezuniyet yılı aralık dışında", () => {
    const hatalar = profilFormunuDogrula(
      { ...GECERLI, sinif: "9", mezuniyet_yili: "2040" },
      2026,
    );
    expect(hatalar).toEqual([
      "Sınıf 1 ile 8 arasında olmalı.",
      "Mezuniyet yılı 1950 ile 2034 arasında olmalı.",
    ]);
  });

  it("şemasız adresi kabul eder, boşluklu adresi reddeder", () => {
    expect(
      profilFormunuDogrula({ ...GECERLI, github_url: "github.com/elif" }, 2026),
    ).toEqual([]);
    expect(
      profilFormunuDogrula({ ...GECERLI, portfolyo_url: "benim sitem" }, 2026),
    ).toEqual(["Portfolyo adresi geçerli bir web adresi değil."]);
  });
});

describe("tercihler ve hesap ayrı sayfalarda", () => {
  it("hatalar ikiye bölünür: tercihler üç, hesap bir zorunlu alan", () => {
    expect(tercihHatalari(BOS_PROFIL_FORMU)).toHaveLength(3);
    expect(hesapHatalari(BOS_PROFIL_FORMU, 2026)).toEqual(["Durumunu seç."]);
  });

  it("her sayfa yalnızca kendi alanlarını gönderir", () => {
    expect(Object.keys(tercihGovdesi(GECERLI)).sort()).toEqual([
      "calisma_modelleri",
      "musaitlik_baslangici",
      "musaitlikler",
      "sehir",
    ]);
    const hesap = hesapGovdesi(GECERLI);
    expect(hesap).not.toHaveProperty("sehir");
    expect(hesap).toHaveProperty("kariyer_durumu");
    expect(hesap).toHaveProperty("github_url");
  });
});

describe("formuProfileCevir", () => {
  it("boş opsiyonelleri null, sayıları sayı yapar", () => {
    expect(
      formuProfileCevir({ ...GECERLI, sinif: " 3 ", okul: "  " }),
    ).toMatchObject({ sinif: 3, okul: null, mezuniyet_yili: null });
  });
});

describe("profilBandi", () => {
  const hesap = (ek: Partial<MeYaniti>) =>
    ({
      rol: "genc",
      eksik_profil_alanlari: [],
      kvkk_onayli: true,
      firma_karti_var: false,
      eposta_dogrulandi: true,
      ...ek,
    }) as MeYaniti;

  it("eksik yoksa bant yok", () => {
    expect(profilBandi(hesap({}))).toBeNull();
  });

  it("eksik alanları ve KVKK onayını söyler", () => {
    expect(
      profilBandi(
        hesap({
          eksik_profil_alanlari: ["sehir", "musaitlikler"],
          kvkk_onayli: false,
        }),
      ),
    ).toBe(
      "Profilini tamamla: profilinde eksik bilgi var (şehir, müsaitlik); KVKK aydınlatma metnini onaylamadın.",
    );
  });

  it("kurumda bant yok", () => {
    expect(profilBandi(hesap({ rol: "kurum", kvkk_onayli: false }))).toBeNull();
  });
});

describe("onaydaProfilSorulmali", () => {
  it("filtre alanları kayıtta alındıysa sorulmaz", () => {
    expect(onaydaProfilSorulmali([])).toBe(false);
    expect(onaydaProfilSorulmali(["kariyer_durumu"])).toBe(false);
  });
  it("eski hesapta filtre alanı eksikse sorulur", () => {
    expect(onaydaProfilSorulmali(["sehir"])).toBe(true);
    expect(onaydaProfilSorulmali(["musaitlikler"])).toBe(true);
  });
});

describe("kartTamamlamaCagrisi", () => {
  const genc = (kartVar: boolean) =>
    ({
      rol: "genc",
      yetenek_karti: kartVar ? { id: "1" } : null,
    }) as MeYaniti;

  it("kartı olmayan gence çağrı", () => {
    expect(kartTamamlamaCagrisi(genc(false))).toBe(
      "Kartını tamamla, firmalar seni görebilsin.",
    );
  });
  it("kartı varsa ya da kurumsa yok", () => {
    expect(kartTamamlamaCagrisi(genc(true))).toBeNull();
    expect(
      kartTamamlamaCagrisi({
        rol: "kurum",
        yetenek_karti: null,
      } as unknown as MeYaniti),
    ).toBeNull();
  });
});
