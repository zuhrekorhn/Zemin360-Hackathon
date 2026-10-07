"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";

import { Sayfa, SayfaBasligi } from "@/components/sayfa";
import { HataKutusu } from "@/components/sohbet";
import { epostaDogrula } from "@/lib/api";
import { type Hata, hatayaCevir, tekrarDenenebilirMi } from "@/lib/hata";
import { useOturum } from "@/lib/oturum";
import { panelYolu } from "@/lib/yonlendirme";

/**
 * Kayıt e-postasındaki bağlantının açtığı sayfa
 * (docs/dogrulama.md § 6.3). Giriş gerekmez: e-posta başka
 * bir cihazda açılabilir, kimliği bağlantı taşır. Aynı bağlantının ikinci
 * açılışı da başarılıdır. Ziyaretçiye "sen" (rehber § 3).
 */

export default function EpostaDogrulaSayfasi() {
  return (
    <Suspense fallback={null}>
      <Dogrulama />
    </Suspense>
  );
}

function Dogrulama() {
  const token = useSearchParams().get("token");
  const { oturum, tazele } = useOturum();
  const [durum, setDurum] = useState<"bekliyor" | "dogrulandi" | "hata">(
    token ? "bekliyor" : "hata",
  );
  const [hata, setHata] = useState<Hata | null>(
    token
      ? null
      : {
          metin:
            "Bu adreste doğrulama kodu yok. E-postadaki bağlantıyı olduğu gibi aç.",
          kota: false,
        },
  );
  const [tekrarDenenir, setTekrarDenenir] = useState(false);
  const baslatildi = useRef(false);

  async function dogrula(kod: string) {
    setDurum("bekliyor");
    setHata(null);
    try {
      await epostaDogrula(kod);
      setDurum("dogrulandi");
      // Açık oturum varsa panel bandı hemen kalksın.
      void tazele();
    } catch (sebep) {
      setHata(hatayaCevir(sebep));
      setTekrarDenenir(tekrarDenenebilirMi(sebep));
      setDurum("hata");
    }
  }

  useEffect(() => {
    if (baslatildi.current || !token) return;
    baslatildi.current = true;
    void dogrula(token);
    // Yalnızca ilk açılışta; tekrar "Tekrar dene" ile.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const panel =
    oturum.durum === "girisli" ? panelYolu(oturum.hesap.rol) : "/giris";

  return (
    <Sayfa>
      <SayfaBasligi baslik="E-posta doğrulama" />

      {durum === "bekliyor" ? (
        <p className="flex items-center gap-2 text-sm text-muted-foreground">
          <span
            aria-hidden="true"
            className="size-2 rounded-full bg-baglanti motion-safe:animate-pulse"
          />
          Doğrulanıyor…
        </p>
      ) : null}

      {durum === "dogrulandi" ? (
        <div role="status" className="flex flex-col gap-3 text-pretty">
          <p>E-posta adresin doğrulandı. Teşekkürler!</p>
          <Link href={panel} className="text-baglanti underline">
            {oturum.durum === "girisli" ? "Panele dön" : "Giriş yap"}
          </Link>
        </div>
      ) : null}

      {hata ? (
        <HataKutusu
          hata={hata}
          tekrarDene={
            tekrarDenenir && token ? () => void dogrula(token) : undefined
          }
        />
      ) : null}
    </Sayfa>
  );
}
