"use client";

import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";

import { GirisKapisi } from "@/components/giris-kapisi";
import { Sayfa, SayfaBasligi } from "@/components/sayfa";
import { HataKutusu } from "@/components/sohbet";
import { type BagliHesap, oauthTamamla } from "@/lib/api";
import { type Hata, hatayaCevir } from "@/lib/hata";
import { platformAdi } from "@/lib/hesap-baglama";

/**
 * OAuth sağlayıcısının döndüğü sayfa (docs/plans/dogrulama-iyilestirme.md § 6.1).
 *
 * Sağlayıcı `?code&state` ile buraya yönlendirir; sayfa ikisini giriş yapmış
 * gencin token'ıyla backend'e iletir. Durum bağlantıyı başlatan hesaba
 * bağlıdır: başka bir hesapla açılırsa backend reddeder. Kod tek kullanımlık
 * olduğu için istek yalnızca ilk açılışta gider.
 */
export default function HesapBaglamaDonusu() {
  return (
    <GirisKapisi roller={["genc"]}>
      <Suspense fallback={null}>
        <Donus />
      </Suspense>
    </GirisKapisi>
  );
}

function Donus() {
  const { saglayici } = useParams<{ saglayici: string }>();
  const parametreler = useSearchParams();
  const kod = parametreler.get("code");
  const durum = parametreler.get("state");
  const reddedildi = parametreler.get("error") !== null;
  const [hesap, setHesap] = useState<BagliHesap | null>(null);
  const [hata, setHata] = useState<Hata | null>(
    reddedildi || !kod || !durum
      ? {
          metin: reddedildi
            ? "Bağlantıyı onaylamadın; hesabın bağlanmadı."
            : "Bağlantı tamamlanamadı. Profilinden yeniden başlat.",
          kota: false,
        }
      : null,
  );
  const gonderildi = useRef(false);
  const ad = platformAdi(saglayici);

  useEffect(() => {
    if (gonderildi.current || !kod || !durum || reddedildi) return;
    gonderildi.current = true;
    oauthTamamla(saglayici, kod, durum)
      .then(setHesap)
      .catch((sebep) => setHata(hatayaCevir(sebep)));
  }, [saglayici, kod, durum, reddedildi]);

  return (
    <Sayfa>
      <SayfaBasligi baslik={`${ad} hesabını bağla`} />

      {!hesap && !hata ? (
        <p className="flex items-center gap-2 text-sm text-muted-foreground">
          <span
            aria-hidden="true"
            className="size-2 rounded-full bg-baglanti motion-safe:animate-pulse"
          />
          Bağlanıyor…
        </p>
      ) : null}

      {hesap ? (
        <p role="status" className="text-pretty">
          {ad} hesabın ({hesap.kullanici_adi}) bağlandı. Bu hesaptaki
          çalışmaların birkaç dakika içinde yeniden değerlendirilecek.
        </p>
      ) : null}

      {hata ? <HataKutusu hata={hata} /> : null}

      <Link href="/profil#hesaplar" className="text-sm text-baglanti underline">
        Profiline dön
      </Link>
    </Sayfa>
  );
}
