/**
 * Üst menünün rol başına içeriği (docs/kimlik-ve-dongu.md § 7). Saf; testi
 * menu.test.ts'de. Bağlantılar sayfadır; hesap ayarı ve çıkış adın altındaki menüde.
 */

import type { MeYaniti } from "@/lib/api";
import { kartYolu, panelYolu } from "@/lib/yonlendirme";

export type MenuBaglantisi = { yol: string; etiket: string };

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
      ],
      ayar: { yol: "/kurum/profil", etiket: "Firma profili" },
    };
  }
  return {
    baglantilar: [{ yol: panelYolu(hesap.rol), etiket: "Panel" }],
    ayar: null,
  };
}
