"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { FormAlani, HataKutusu } from "@/components/sohbet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { girisYap } from "@/lib/api";
import { type Hata, hatayaCevir } from "@/lib/hata";
import { useOturum } from "@/lib/oturum";
import { tokenYaz } from "@/lib/token";
import { giristenSonra } from "@/lib/yonlendirme";

/**
 * Giriş (docs/faz-b-kimlik-ve-dongu.md § 1, § 7).
 *
 * `?sonra=<yol>`: giriş gerektiren bir sayfadan gelindiyse girişten sonra
 * oraya dönülür; yoksa rolün paneline. Zaten giriş yapmışsa form gösterilmez.
 */

export default function GirisSayfasi() {
  return (
    <Suspense fallback={null}>
      <GirisFormu />
    </Suspense>
  );
}

function GirisFormu() {
  const sonra = useSearchParams().get("sonra");
  const router = useRouter();
  const { oturum } = useOturum();

  const [email, setEmail] = useState("");
  const [sifre, setSifre] = useState("");
  const [bekleniyor, setBekleniyor] = useState(false);
  const [hata, setHata] = useState<Hata | null>(null);

  useEffect(() => {
    if (oturum.durum === "girisli") {
      router.replace(giristenSonra(oturum.hesap.rol, sonra));
    }
  }, [oturum, router, sonra]);

  async function gonder(olay: React.FormEvent) {
    olay.preventDefault();
    if (bekleniyor) return;
    setHata(null);
    setBekleniyor(true);
    try {
      const yanit = await girisYap(email.trim(), sifre);
      tokenYaz(yanit.token);
      router.replace(giristenSonra(yanit.rol, sonra));
    } catch (sebep) {
      setHata(hatayaCevir(sebep));
      setBekleniyor(false);
    }
  }

  const kayitYolu = sonra
    ? `/kayit?sonra=${encodeURIComponent(sonra)}`
    : "/kayit";

  return (
    <main className="mx-auto flex w-full max-w-md flex-1 flex-col gap-8 px-4 py-10 sm:px-6 sm:py-16">
      <header className="flex flex-col gap-2">
        <h1 className="font-heading text-2xl font-semibold text-ana sm:text-3xl">
          Giriş yap
        </h1>
        {sonra ? (
          <p className="text-sm text-pretty text-muted-foreground">
            Bu sayfa için giriş yapman gerekiyor; girişten sonra kaldığın yere
            dönersin.
          </p>
        ) : null}
      </header>

      <form className="flex flex-col gap-4" onSubmit={gonder}>
        <FormAlani etiket="E-posta" htmlFor="email">
          <Input
            id="email"
            type="email"
            value={email}
            onChange={(olay) => setEmail(olay.target.value)}
            required
            autoComplete="email"
          />
        </FormAlani>
        <FormAlani etiket="Şifre" htmlFor="sifre">
          <Input
            id="sifre"
            type="password"
            value={sifre}
            onChange={(olay) => setSifre(olay.target.value)}
            required
            autoComplete="current-password"
          />
        </FormAlani>

        {hata ? <HataKutusu hata={hata} /> : null}

        <Button type="submit" size="lg" disabled={bekleniyor} className="w-fit">
          {bekleniyor ? "Giriş yapılıyor…" : "Giriş yap"}
        </Button>
      </form>

      <p className="text-sm text-muted-foreground">
        Hesabın yok mu?{" "}
        <Link href={kayitYolu} className="text-baglanti underline">
          Kayıt ol
        </Link>
      </p>
    </main>
  );
}
