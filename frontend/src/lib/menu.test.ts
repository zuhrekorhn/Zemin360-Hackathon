import { describe, expect, it } from "vitest";

import { menuBaglantilari } from "@/lib/menu";

const etiketler = (hesap: Parameters<typeof menuBaglantilari>[0]) =>
  menuBaglantilari(hesap).baglantilar.map((b) => `${b.etiket} ${b.yol}`);

describe("menuBaglantilari", () => {
  it("genç: Fırsatlar, Kartım, İş birliklerim; ayar Hesabım", () => {
    const kart = {
      id: "k1",
      rol_alani: "x",
      deneyim_seviyesi: "orta",
      kanit_bekleyen: false,
      embedding_var: true,
    };
    expect(etiketler({ rol: "genc", yetenek_karti: kart })).toEqual([
      "Fırsatlar /genc",
      "Kartım /kart/k1",
      "İş birliklerim /isbirliklerim",
    ]);
    expect(menuBaglantilari({ rol: "genc", yetenek_karti: kart }).ayar).toEqual(
      { yol: "/profil", etiket: "Hesabım" },
    );
  });

  it("kartı olmayan gencin Kartım'ı sohbete gider", () => {
    expect(etiketler({ rol: "genc", yetenek_karti: null })[1]).toBe(
      "Kartım /kesif",
    );
  });

  it("firma ve GİRVAK; bildirimler bağlantı değil, zil", () => {
    expect(etiketler({ rol: "kurum", yetenek_karti: null })).toEqual([
      "Panelim /kurum",
      "Yeni ihtiyaç /tanimlama",
      "Firma kartı /kurum/kart",
    ]);
    expect(menuBaglantilari({ rol: "girvak", yetenek_karti: null })).toEqual({
      baglantilar: [{ yol: "/girvak", etiket: "Panel" }],
      ayar: null,
    });
  });
});
