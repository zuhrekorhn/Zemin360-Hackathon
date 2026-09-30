/**
 * İş birliği sayfasının saf görünüm kuralları (docs/faz-c-takip.md § 8).
 * Kural backend'de (app/agents/takip_durumu.py); burada yalnızca "ekranda ne
 * yazsın" var. Testleri takip.test.ts'de.
 */

import type { IsbirligiDetayi, MilestoneYaniti, Rol } from "@/lib/api";
import { type Hitap, hitapla } from "@/lib/hitap";

export type Taraf = "genc" | "kurum";

/** Bu hesap iş birliğinin hangi tarafı? GİRVAK için null (yalnızca okur). */
export function tarafim(rol: Rol): Taraf | null {
  return rol === "genc" || rol === "kurum" ? rol : null;
}

export function karsiTarafAdi(detay: IsbirligiDetayi, taraf: Taraf): string {
  return taraf === "genc" ? detay.kurum_adi : detay.aday_adi;
}

export type AdimGorunumu = {
  /** Ekranda adımın altındaki durum cümlesi. */
  metin: string;
  tamamlandi: boolean;
  /** Ben işaretledim mi (geri alabilirim)? */
  benIsaretledim: boolean;
  /** Karşı taraf işaretledi, sıra bende mi? */
  siraBende: boolean;
};

export function adimGorunumu(
  adim: MilestoneYaniti,
  detay: IsbirligiDetayi,
  taraf: Taraf | null,
  hitap: Hitap = "sen",
): AdimGorunumu {
  const genc = adim.genc_isaret !== null;
  const kurum = adim.kurum_isaret !== null;
  if (genc && kurum) {
    return {
      metin: "İki taraf da tamamlandı dedi.",
      tamamlandi: true,
      benIsaretledim: true,
      siraBende: false,
    };
  }
  if (taraf === null) {
    // GİRVAK: taraf adlarıyla, yönsüz.
    const metin = genc
      ? `${detay.aday_adi} tamamlandı dedi; ${detay.kurum_adi} tarafının onayı bekleniyor.`
      : kurum
        ? `${detay.kurum_adi} tamamlandı dedi; ${detay.aday_adi} tarafının onayı bekleniyor.`
        : "Sürüyor.";
    return {
      metin,
      tamamlandi: false,
      benIsaretledim: false,
      siraBende: false,
    };
  }
  const ben = taraf === "genc" ? genc : kurum;
  const karsi = taraf === "genc" ? kurum : genc;
  const karsiAd = karsiTarafAdi(detay, taraf);
  if (ben) {
    return {
      metin: `${hitapla(hitap, "Sen tamamlandı dedin", "Siz tamamlandı dediniz")}; ${karsiAd} tarafının onayı bekleniyor.`,
      tamamlandi: false,
      benIsaretledim: true,
      siraBende: false,
    };
  }
  if (karsi) {
    return {
      metin: `${karsiAd} tamamlandı dedi; ${hitapla(hitap, "senin onayın", "sizin onayınız")} bekleniyor.`,
      tamamlandi: false,
      benIsaretledim: false,
      siraBende: true,
    };
  }
  return {
    metin: "Sürüyor.",
    tamamlandi: false,
    benIsaretledim: false,
    siraBende: false,
  };
}

export type PlanOnayGorunumu = {
  metin: string;
  benOnayladim: boolean;
};

/** Taslak plandaki onay durumu cümlesi. */
export function planOnayGorunumu(
  detay: IsbirligiDetayi,
  taraf: Taraf | null,
  hitap: Hitap = "sen",
): PlanOnayGorunumu {
  const genc = detay.genc_plan_onayi !== null;
  const kurum = detay.kurum_plan_onayi !== null;
  if (taraf === null) {
    const onaylayanlar = [
      genc ? detay.aday_adi : null,
      kurum ? detay.kurum_adi : null,
    ].filter(Boolean);
    return {
      metin: onaylayanlar.length
        ? `Onaylayan: ${onaylayanlar.join(", ")}.`
        : "Henüz kimse onaylamadı.",
      benOnayladim: false,
    };
  }
  const ben = taraf === "genc" ? genc : kurum;
  const karsi = taraf === "genc" ? kurum : genc;
  const karsiAd = karsiTarafAdi(detay, taraf);
  if (ben && karsi)
    return { metin: "İki taraf da onayladı.", benOnayladim: true };
  if (ben) {
    return {
      metin: `${hitapla(hitap, "Sen onayladın", "Siz onayladınız")}; ${karsiAd} tarafının onayı bekleniyor.`,
      benOnayladim: true,
    };
  }
  if (karsi) {
    return {
      metin: `${karsiAd} planı onayladı; ${hitapla(hitap, "senin onayın", "sizin onayınız")} bekleniyor.`,
      benOnayladim: false,
    };
  }
  return {
    metin:
      "Plan iki taraf da onaylayınca başlar. Düzenleme yapılırsa iki onay da sıfırlanır.",
    benOnayladim: false,
  };
}

export const ISBIRLIGI_DURUM_ETIKETLERI: Record<string, string> = {
  plan_bekliyor: "Plan onay bekliyor",
  aktif: "Sürüyor",
  tamamlandi: "Tamamlandı",
};

/** Panel satırı: "2/4 adım · 1 gecikmiş" ya da plan durumu. */
export function ilerlemeMetni(
  durum: string,
  ilerleme: { tamamlanan: number; toplam: number; geciken: number },
): string {
  if (durum === "plan_bekliyor") {
    return ilerleme.toplam === 0
      ? "Plan henüz yok"
      : `Plan taslağı · ${ilerleme.toplam} adım`;
  }
  const parcalar = [`${ilerleme.tamamlanan}/${ilerleme.toplam} adım`];
  if (ilerleme.geciken > 0) parcalar.push(`${ilerleme.geciken} gecikmiş`);
  return parcalar.join(" · ");
}
