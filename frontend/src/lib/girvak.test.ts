import { describe, expect, it } from "vitest";

import type { GirvakIsbirligi, GirvakOzet } from "@/lib/api";
import {
  alanKartlari,
  filtreSayilari,
  filtrele,
  filtreyeUyar,
  yuzde,
  yuzdeMetni,
} from "@/lib/girvak";

const OZET: GirvakOzet = {
  kesif: { kayitli_genc: 12, kart_olusturan_genc: 9, firsat_goren_genc: 5 },
  dogruluk: { calisma: 20, degerlendirilen_calisma: 15, bekleyen_inceleme: 2 },
  eslesme: { oneri_toplam: 30, karsilikli_ilgi: 6 },
  ag: { takilan_surec: 3, hatirlatma_30_gun: 8 },
  tanim: { ihtiyac: 7, olculebilir_ihtiyac: 4 },
  takip: { isbirligi: 6, tamamlanan: 2, gecikmis_adim: 1 },
};

describe("yuzde", () => {
  it("yuvarlar, taşmaz, toplam yoksa null", () => {
    expect(yuzde(15, 20)).toBe(75);
    expect(yuzde(1, 3)).toBe(33);
    expect(yuzde(5, 4)).toBe(100);
    expect(yuzde(0, 0)).toBeNull();
    expect(yuzdeMetni(15, 20)).toBe("%75");
    expect(yuzdeMetni(0, 0)).toBe("—");
  });
});

describe("alanKartlari", () => {
  const kartlar = alanKartlari(OZET);

  it("brifteki altı alan, aynı adlarla ve sırayla", () => {
    expect(kartlar.map((k) => [k.no, k.ad])).toEqual([
      ["01", "Genç Yeteneklerin Keşfi"],
      ["02", "Profil ve Portfolyo Doğruluğu"],
      ["03", "Kurum–Kişi Eşleşmesi"],
      ["04", "Yaşayan Bir Ağ"],
      ["05", "İhtiyaçların Net Tanımı"],
      ["06", "Şeffaf İş Birliği Takibi"],
    ]);
  });

  it("ana sayılar backend sayılarıyla birebir", () => {
    expect(kartlar.map((k) => k.sayi)).toEqual([
      "9",
      "%75",
      "6",
      "3",
      "7",
      "6",
    ]);
  });

  it("cümleler sayıları doğru yerleştirir", () => {
    expect(kartlar[0].aciklama).toBe(
      "12 genç kayıtlı; 5 genç en az bir fırsat gördü.",
    );
    expect(kartlar[1].aciklama).toContain("2 inceleme sizi bekliyor");
    expect(kartlar[2].aciklama).toBe(
      "30 öneriden 6 tanesinde iki taraf da ilgilendi.",
    );
    expect(kartlar[5].aciklama).toBe("2 tamamlandı; 1 gecikmiş adım var.");
  });

  it("bekleyen inceleme ve takılan süreç yoksa bunu söyler", () => {
    const bos = alanKartlari({
      ...OZET,
      dogruluk: {
        calisma: 0,
        degerlendirilen_calisma: 0,
        bekleyen_inceleme: 0,
      },
      ag: { takilan_surec: 0, hatirlatma_30_gun: 0 },
    });
    expect(bos[1].sayi).toBe("—");
    expect(bos[1].aciklama).toContain("Bekleyen inceleme yok");
    expect(bos[3].aciklama).toContain("Şu an takılan süreç yok");
  });

  it("her kart ayrıntı sayfasına bağlanır; e-posta yok", () => {
    expect(kartlar.map((k) => k.yol)).toEqual([
      "/girvak/sayilar",
      "/girvak/kararlar",
      "/girvak/sayilar",
      "/girvak/canlilik",
      "/girvak/sayilar",
      "/girvak/isbirlikleri",
    ]);
    expect(JSON.stringify(kartlar)).not.toContain("@");
  });
});

const isb = (durum: string, geciken = 0): GirvakIsbirligi =>
  ({
    isbirligi_id: durum + geciken,
    durum,
    ilerleme: { tamamlanan: 0, toplam: 3, geciken },
  }) as GirvakIsbirligi;

describe("iş birlikleri filtreleri", () => {
  const liste = [
    isb("plan_bekliyor"),
    isb("aktif"),
    isb("aktif", 2),
    isb("tamamlandi"),
    isb("sonlandi"),
  ];

  it("her filtre doğru kümeyi seçer; gecikmiş süren iş birliğinin alt kümesi", () => {
    expect(filtrele(liste, "hepsi")).toHaveLength(5);
    expect(filtrele(liste, "plan_bekliyor")).toHaveLength(1);
    expect(filtrele(liste, "suren")).toHaveLength(2);
    expect(filtrele(liste, "gecikmis")).toHaveLength(1);
    expect(filtrele(liste, "tamamlanan")).toHaveLength(1);
    expect(filtrele(liste, "sonlanan")).toHaveLength(1);
  });

  it("gecikmiş adım yalnızca süren iş birliğinde sayılır", () => {
    expect(filtreyeUyar(isb("tamamlandi", 1), "gecikmis")).toBe(false);
  });

  it("düğme sayıları", () => {
    expect(filtreSayilari(liste)).toEqual({
      hepsi: 5,
      plan_bekliyor: 1,
      suren: 2,
      gecikmis: 1,
      tamamlanan: 1,
      sonlanan: 1,
    });
  });
});
