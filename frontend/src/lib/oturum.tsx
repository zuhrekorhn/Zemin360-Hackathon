"use client";

/**
 * Giriş yapmış hesabın durumu (docs/faz-b-kimlik-ve-dongu.md § 1, § 7).
 *
 * Tek kaynak `GET /me`: rol, ad, kartlar ve okunmamış bildirim sayısı. Ne
 * zaman yeniden okunur:
 *   - token değişince (giriş, çıkış, 401 yüzünden silinme — lib/token.ts),
 *   - başka sekmede giriş/çıkış yapılınca (`storage` olayı),
 *   - sayfa değişince ve açık sayfada 60 saniyede bir (menüdeki rozet için).
 * Canlı bağlantı (websocket) yok, bilinçli.
 */

import { usePathname } from "next/navigation";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { ApiHatasi, type MeYaniti, me } from "@/lib/api";
import { type Hitap, hitapRolden } from "@/lib/hitap";
import {
  TOKEN_DEGISTI,
  tokenAnahtariMi,
  tokenOku,
  tokenSil,
} from "@/lib/token";

export type Oturum =
  | { durum: "yukleniyor" }
  | { durum: "girissiz" }
  | { durum: "girisli"; hesap: MeYaniti }
  // Backend'e ulaşılamadı: token silinmez, kullanıcı çıkış yapmış sayılmaz.
  | { durum: "baglanti_yok" };

type OturumBaglami = {
  oturum: Oturum;
  /** /me'yi yeniden okur (ör. kart onaylandıktan sonra panel güncel olsun). */
  tazele: () => Promise<void>;
  cikisYap: () => void;
};

const Baglam = createContext<OturumBaglami | null>(null);

const TAZELEME_ARALIGI_MS = 60_000;

async function oturumuOku(): Promise<Oturum> {
  if (!tokenOku()) return { durum: "girissiz" };
  try {
    return { durum: "girisli", hesap: await me() };
  } catch (sebep) {
    // 401'de token api.ts'de zaten silindi.
    if (sebep instanceof ApiHatasi && sebep.durumKodu === 401) {
      return { durum: "girissiz" };
    }
    return { durum: "baglanti_yok" };
  }
}

export function OturumSaglayici({ children }: { children: React.ReactNode }) {
  const [oturum, setOturum] = useState<Oturum>({ durum: "yukleniyor" });
  const pathname = usePathname();
  // Üst üste gelen okumalarda (sayfa değişimi + token olayı) yalnızca en
  // sonuncusunun sonucu yazılsın.
  const sira = useRef(0);

  const tazele = useCallback(async () => {
    const benim = ++sira.current;
    const yeni = await oturumuOku();
    if (benim === sira.current) setOturum(yeni);
  }, []);

  const cikisYap = useCallback(() => {
    // tokenSil TOKEN_DEGISTI yayar; dinleyici oturumu "girissiz" yapar.
    tokenSil();
  }, []);

  // Sayfa değişiminde (ilk açılış dahil) tazele.
  useEffect(() => {
    void tazele();
  }, [pathname, tazele]);

  useEffect(() => {
    const tokenDegisti = () => {
      // Girişten hemen sonra yönlendirilen sayfa, /me dönene kadar eski
      // "girişsiz" durumu görüp kullanıcıyı /giris'e geri atmasın.
      if (tokenOku()) setOturum({ durum: "yukleniyor" });
      void tazele();
    };
    const depoDegisti = (olay: StorageEvent) => {
      if (tokenAnahtariMi(olay.key)) void tazele();
    };
    const zamanlayici = window.setInterval(() => {
      if (document.visibilityState === "visible") void tazele();
    }, TAZELEME_ARALIGI_MS);

    window.addEventListener(TOKEN_DEGISTI, tokenDegisti);
    window.addEventListener("storage", depoDegisti);
    return () => {
      window.removeEventListener(TOKEN_DEGISTI, tokenDegisti);
      window.removeEventListener("storage", depoDegisti);
      window.clearInterval(zamanlayici);
    };
  }, [tazele]);

  const deger = useMemo(
    () => ({ oturum, tazele, cikisYap }),
    [oturum, tazele, cikisYap],
  );
  return <Baglam value={deger}>{children}</Baglam>;
}

export function useOturum(): OturumBaglami {
  const baglam = useContext(Baglam);
  if (!baglam)
    throw new Error("useOturum, OturumSaglayici içinde kullanılmalı");
  return baglam;
}

/** Görüntüleyene hitap: gence "sen", firmaya ve GİRVAK'a "siz" (rehber § 3). */
export function useHitap(): Hitap {
  const { oturum } = useOturum();
  return hitapRolden(oturum.durum === "girisli" ? oturum.hesap.rol : null);
}
