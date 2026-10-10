/**
 * Üst menünün rol başına içeriği (docs/kimlik-ve-dongu.md § 7). Saf; testi
 * menu.test.ts'de. Bağlantılar sayfadır; hesap ayarı ve çıkış adın altındaki menüde.
 */

import type { MeYaniti } from "@/lib/api";
import { kartYolu, panelYolu } from "@/lib/yonlendirme";

export type MenuBaglantisi = { yol: string; etiket: string };

/**
 * Adresin hangi menü bağlantısına ait olduğu: en uzun eşleşen yol kazanır, yani
 * her zaman en çok biri etkindir. `/kurum/kart` hem "Panelim" (`/kurum`) hem
 * "Firma kartı"nın altında kalır; ikisi birden etkin görünmesin.
 */
export function etkinBaglanti(
  pathname: string,
  baglantilar: MenuBaglantisi[],
): string | null {
  const eslesenler = baglantilar.filter(
    (b) => pathname === b.yol || pathname.startsWith(`${b.yol}/`),
  );
  if (eslesenler.length === 0) return null;
  return eslesenler.reduce((en, b) => (b.yol.length > en.yol.length ? b : en))
    .yol;
}

export function menuBaglantilari(
  hesap: Pick<MeYaniti, "rol" | "yetenek_karti">,
): { baglantilar: MenuBaglantisi[]; ayar: MenuBaglantisi | null } {
  if (hesap.rol === "genc") {
    return {
      baglantilar: [
        { yol: panelYolu("genc"), etiket: "Fırsatlar" },
        // Gencin tek kartı var (docs/kararlar.md G17): "Yeni kart" değil, kendi kartı.
        { yol: kartYolu(hesap.yetenek_karti), etiket: "Kartım" },
        { yol: "/isbirliklerim", etiket: "İş birliklerim" },
      ],
      ayar: { yol: "/profil", etiket: "Hesabım" },
    };
  }
  if (hesap.rol === "kurum") {
    return {
      baglantilar: [
        { yol: panelYolu("kurum"), etiket: "Panelim" },
        { yol: "/tanimlama", etiket: "Yeni ihtiyaç" },
        { yol: "/kurum/kart", etiket: "Firma kartı" },
        { yol: "/isbirliklerim", etiket: "İş birliklerim" },
      ],
      ayar: { yol: "/kurum/profil", etiket: "Firma profili" },
    };
  }
  return {
    baglantilar: [
      { yol: panelYolu(hesap.rol), etiket: "Özet" },
      { yol: "/girvak/kararlar", etiket: "Karar bekleyenler" },
      { yol: "/girvak/isbirlikleri", etiket: "İş birlikleri" },
      { yol: "/girvak/canlilik", etiket: "Takılan süreçler" },
      { yol: "/girvak/sayilar", etiket: "Sayılar" },
    ],
    // Teknik sayfa ana menüde değil, hesap menüsünde (yalnızca bakım için).
    ayar: { yol: "/girvak/gozlem", etiket: "Sistem durumu" },
  };
}
