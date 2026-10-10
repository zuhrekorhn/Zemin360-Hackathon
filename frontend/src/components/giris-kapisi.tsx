"use client";

/**
 * Giriş gerektiren sayfaların kapısı (docs/kimlik-ve-dongu.md § 7).
 *
 *   - Girişsiz açılırsa `/giris?sonra=<yol>`'a gider; girişten sonra geri döner.
 *   - Rolü uymayan sayfa (ör. kurumun /kesif'i açması) kendi paneline gider.
 *   - Kapı açılana kadar içerik hiç çizilmez: sayfanın açılış efektleri
 *     (ör. Keşif'in sohbeti başlatması) token'sız istek atmasın.
 *
 * Yetkinin asıl sahibi backend (401/403/404); bu kapı kullanıcıyı doğru
 * yere götürmek için.
 */

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { type Genislik, SayfaDurumu } from "@/components/sayfa";
import type { MeYaniti, Rol } from "@/lib/api";
import { cikisYeniMi } from "@/lib/cikis";
import { useOturum } from "@/lib/oturum";
import { panelYolu } from "@/lib/yonlendirme";

export function GirisKapisi({
  roller,
  genislik,
  children,
}: {
  /** Verilmezse giriş yapmış her rol girebilir. */
  roller?: Rol[];
  /** Kapı açılana kadarki durum sayfanın kendi genişliğinde çizilsin. */
  genislik?: Genislik;
  children: React.ReactNode;
}) {
  const { oturum, tazele } = useOturum();
  const router = useRouter();

  const izinli =
    oturum.durum === "girisli" &&
    (!roller || roller.includes(oturum.hesap.rol));

  useEffect(() => {
    if (oturum.durum === "girissiz") {
      // Bilinçli çıkışta ana sayfaya geçiş sürüyor; sonraki girişe adres bırakma.
      if (cikisYeniMi()) return;
      const yol = window.location.pathname + window.location.search;
      router.replace(`/giris?sonra=${encodeURIComponent(yol)}`);
    } else if (oturum.durum === "girisli" && !izinli) {
      router.replace(panelYolu(oturum.hesap.rol));
    }
  }, [oturum, izinli, router]);

  if (izinli) return <>{children}</>;

  if (oturum.durum === "baglanti_yok") {
    return (
      <SayfaDurumu
        genislik={genislik}
        hata={{
          metin: "Şu an bağlantı kuramadık; oturum kontrol edilemedi.",
          kota: false,
        }}
        tekrarDene={() => void tazele()}
      />
    );
  }

  return <SayfaDurumu genislik={genislik} />;
}

/** Kapının içinde: giriş yapmış hesap. Kapı dışında çağrılırsa hata. */
export function useGirisliHesap(): MeYaniti {
  const { oturum } = useOturum();
  if (oturum.durum !== "girisli") {
    throw new Error("useGirisliHesap yalnızca GirisKapisi içinde kullanılır");
  }
  return oturum.hesap;
}
