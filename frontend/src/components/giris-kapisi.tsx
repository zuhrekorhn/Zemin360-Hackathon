"use client";

/**
 * Giriş gerektiren sayfaların kapısı (docs/faz-b-kimlik-ve-dongu.md § 7).
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

import { HataKutusu } from "@/components/sohbet";
import type { MeYaniti, Rol } from "@/lib/api";
import { useOturum } from "@/lib/oturum";
import { panelYolu } from "@/lib/yonlendirme";

export function GirisKapisi({
  roller,
  children,
}: {
  /** Verilmezse giriş yapmış her rol girebilir. */
  roller?: Rol[];
  children: React.ReactNode;
}) {
  const { oturum, tazele } = useOturum();
  const router = useRouter();

  const izinli =
    oturum.durum === "girisli" &&
    (!roller || roller.includes(oturum.hesap.rol));

  useEffect(() => {
    if (oturum.durum === "girissiz") {
      const yol = window.location.pathname + window.location.search;
      router.replace(`/giris?sonra=${encodeURIComponent(yol)}`);
    } else if (oturum.durum === "girisli" && !izinli) {
      router.replace(panelYolu(oturum.hesap.rol));
    }
  }, [oturum, izinli, router]);

  if (izinli) return <>{children}</>;

  if (oturum.durum === "baglanti_yok") {
    return (
      <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-4 px-4 py-10 sm:px-6 sm:py-16">
        <HataKutusu
          hata={{
            metin: "Backend'e ulaşılamadı; oturumun kontrol edilemedi.",
            kota: false,
          }}
          tekrarDene={() => void tazele()}
        />
      </main>
    );
  }

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col px-4 py-10 sm:px-6 sm:py-16">
      <p className="text-sm text-muted-foreground" role="status">
        Yükleniyor…
      </p>
    </main>
  );
}

/** Kapının içinde: giriş yapmış hesap. Kapı dışında çağrılırsa hata. */
export function useGirisliHesap(): MeYaniti {
  const { oturum } = useOturum();
  if (oturum.durum !== "girisli") {
    throw new Error("useGirisliHesap yalnızca GirisKapisi içinde kullanılır");
  }
  return oturum.hesap;
}
