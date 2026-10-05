import { describe, expect, it } from "vitest";

import type { IncelemeSatiri } from "@/lib/api";
import {
  ayrintiSatirlari,
  incelenecekBelgeler,
  karsilastirilacakKartlar,
  kararEtiketleri,
  turEtiketi,
} from "@/lib/inceleme";

function satir(tur: string, ayrinti: Record<string, unknown>): IncelemeSatiri {
  return {
    id: "1",
    tur,
    durum: "acik",
    olusturma_tarihi: "2026-10-02T10:00:00Z",
    kapanma_tarihi: null,
    girvak_notu: null,
    genc_adi: "Elif",
    kart_id: null,
    somut_cikti_id: null,
    cikti_basligi: null,
    ayrinti,
  };
}

describe("inceleme metinleri", () => {
  it("türün etiketi, bilinmeyen tür için genel etiket", () => {
    expect(turEtiketi("itiraz_siniri")).toBe("İtiraz hakkı doldu");
    expect(turEtiketi("yeni_bir_tur")).toBe("İnceleme");
  });

  it("talepte onay/ret, sinyalde sorun yok / doğrulanamadı", () => {
    expect(kararEtiketleri("ad_degisikligi")).toEqual({
      kapandi: "Onayla",
      dogrulanamadi: "Reddet",
    });
    expect(kararEtiketleri("itiraz_siniri").kapandi).toBe("Sorun yok");
  });

  it("ayrıntı türe göre okunur", () => {
    expect(
      ayrintiSatirlari(
        satir("ad_degisikligi", {
          eski_ad: "Elif Yılmaz",
          yeni_ad: "Elif Kaya",
          gerekce: "Evlilik",
        }),
      ),
    ).toEqual(["Elif Yılmaz → Elif Kaya", "Gerekçe: Evlilik"]);
    expect(
      ayrintiSatirlari(satir("itiraz_siniri", { itiraz_notlari: ["a", 3] })),
    ).toEqual(["İtiraz notu: a"]);
    expect(ayrintiSatirlari(satir("belge_tutarsiz", { x: 1 }))).toEqual([]);
  });

  it("doğrulama kodu: hesap, profil ve aranacak kod; karar düğmeleri", () => {
    expect(
      ayrintiSatirlari(
        satir("profil_kodu_elle", {
          platform: "behance",
          kullanici_adi: "elif",
          profil_adresi: "https://www.behance.net/elif",
          kod: "z360-abcd1234",
        }),
      ),
    ).toEqual([
      "Hesap: Behance · elif",
      "Profil: https://www.behance.net/elif",
      "Aranacak kod: z360-abcd1234",
    ]);
    expect(kararEtiketleri("profil_kodu_elle").kapandi).toBe(
      "Kod profilde, bağla",
    );
  });
});

describe("e-Devlet barkodu ve aynı belge", () => {
  it("barkodu ve indirilecek belgeleri gösterir", () => {
    const s = satir("edevlet_barkodu", {
      parcalar: [{ parca_id: "p1", barkod: "YOK-ABCD-1234" }],
    });
    expect(ayrintiSatirlari(s)[0]).toContain("YOK-ABCD-1234");
    expect(incelenecekBelgeler(s)).toEqual(["p1"]);
    expect(kararEtiketleri("edevlet_barkodu").kapandi).toBe("Belge doğrulandı");
    expect(incelenecekBelgeler(satir("itiraz_siniri", {}))).toEqual([]);
  });

  it("aynı doğrulama adresinin hangi adres olduğunu yazar", () => {
    const s = satir("ayni_belge_iki_hesapta", {
      eslesmeler: [{ adres: "https://credly.com/badges/1" }],
    });
    expect(ayrintiSatirlari(s)[0]).toContain("https://credly.com/badges/1");
  });
});

describe("aynı çalışma başka hesapta", () => {
  it("eşleşmenin nedenini ve öteki kartı verir", () => {
    const s = satir("ayni_iddia_cok_hesapta", {
      eslesmeler: [
        { neden: "adres", adres: "https://github.com/a/b", diger_kart_id: "k2" },
        { neden: "gorsel", dosya_adi: "afis.png", diger_kart_id: "k2" },
        { neden: "dosya", dosya_adi: "rapor.pdf", diger_kart_id: "k3" },
      ],
    });
    expect(ayrintiSatirlari(s)).toEqual([
      "Aynı link başka bir hesapta da var: https://github.com/a/b",
      "Benzer görsel başka bir hesapta da var: afis.png",
      "Aynı dosya başka bir hesapta da var: rapor.pdf",
    ]);
    expect(karsilastirilacakKartlar(s)).toEqual(["k2", "k3"]);
    expect(karsilastirilacakKartlar(satir("itiraz_siniri", {}))).toEqual([]);
  });
});

describe("şüpheli referans yanıtı", () => {
  it("sinyalleri tek satırda okur", () => {
    const s = satir("referans_supheli", {
      referanslar: [
        {
          sinyaller: ["ip_genc_ile_ayni", "hizli_yanit", "cok_gence_yanit"],
          form_suresi_sn: 8,
          genc_sayisi: 4,
        },
        { sinyaller: ["form_acilmadan"] },
      ],
    });
    expect(ayrintiSatirlari(s)).toEqual([
      "Referans yanıtı: genç ile aynı internet bağlantısından yanıtlanmış · form 8 saniyede gönderilmiş · bu kişi 4 farklı gence referans vermiş",
      "Referans yanıtı: form sayfası açılmadan gönderilmiş",
    ]);
  });
});
