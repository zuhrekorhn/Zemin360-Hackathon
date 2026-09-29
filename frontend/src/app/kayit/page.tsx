"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { FirmaProfilAlanlari } from "@/components/firma-profil-alanlari";
import { GencProfilAlanlari } from "@/components/genc-profil-alanlari";
import { FormAlani, HataKutusu } from "@/components/sohbet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { kayitOl } from "@/lib/api";
import {
  BOS_FIRMA_FORMU,
  firmaFormunuDogrula,
  formuFirmaProfilineCevir,
} from "@/lib/firma-profil";
import { type Hata, hatayaCevir } from "@/lib/hata";
import { useOturum } from "@/lib/oturum";
import {
  BOS_PROFIL_FORMU,
  formuProfileCevir,
  profilFormunuDogrula,
} from "@/lib/profil";
import { tokenYaz } from "@/lib/token";
import { cn } from "@/lib/utils";
import { giristenSonra, kayittanSonra } from "@/lib/yonlendirme";

/**
 * Kayıt (docs/faz-b-kimlik-ve-dongu.md § 2, § 7).
 *
 * Rol kayıtta seçilir: genç ya da kurum. GİRVAK açık kayıtla açılamaz.
 * Kayıtla birlikte giriş yapılmış olur. Genç kayıtta yapısal profil alanlarını
 * (şehir, çalışma modeli, müsaitlik, durum…) ve KVKK onayını verir
 * (docs/plans/genc-akisi.md § 5.1); yetkinlikler Keşif sohbetinde toplanır.
 * Firma kayıtta türünü, sektörünü, şehrini ve isteğe bağlı tanıtım bilgilerini
 * verir; KVKK onayı iki rol için de zorunlu (docs/plans/firma-akisi.md § 0
 * kararlar 1-2). Ana sayfadaki düğmeler `?rol=` ile gelir.
 */

const SIFRE_EN_AZ = 8;

type KayitRolu = "genc" | "kurum";

const ROLLER: { deger: KayitRolu; baslik: string; aciklama: string }[] = [
  {
    deger: "genc",
    baslik: "Gencim",
    aciklama:
      "Yaptıklarımı yetenek kartına dönüştürüp kurumlarla buluşmak istiyorum.",
  },
  {
    deger: "kurum",
    baslik: "Kurum adına",
    aciklama:
      "Bir ihtiyacımızı tanımlayıp ona uygun genç yetenekleri bulmak istiyoruz.",
  },
];

export default function KayitSayfasi() {
  return (
    <Suspense fallback={null}>
      <KayitFormu />
    </Suspense>
  );
}

function KayitFormu() {
  const parametreler = useSearchParams();
  const sonra = parametreler.get("sonra");
  const router = useRouter();
  const { oturum } = useOturum();

  const baslangicRolu = parametreler.get("rol");
  const [rol, setRol] = useState<KayitRolu | null>(
    baslangicRolu === "genc" || baslangicRolu === "kurum"
      ? baslangicRolu
      : null,
  );
  const [ad, setAd] = useState("");
  const [email, setEmail] = useState("");
  const [sifre, setSifre] = useState("");
  const [profil, setProfil] = useState(BOS_PROFIL_FORMU);
  const [firma, setFirma] = useState(BOS_FIRMA_FORMU);
  const [kvkkOnay, setKvkkOnay] = useState(false);
  const [bekleniyor, setBekleniyor] = useState(false);
  const [hata, setHata] = useState<Hata | null>(null);

  useEffect(() => {
    if (oturum.durum === "girisli") {
      router.replace(giristenSonra(oturum.hesap.rol, sonra));
    }
  }, [oturum, router, sonra]);

  async function gonder(olay: React.FormEvent) {
    olay.preventDefault();
    if (bekleniyor || !rol) return;
    setHata(null);
    const hatalar =
      rol === "genc"
        ? profilFormunuDogrula(profil)
        : firmaFormunuDogrula(firma);
    if (!kvkkOnay)
      hatalar.push(
        rol === "genc"
          ? "KVKK aydınlatma metnini onayla."
          : "KVKK aydınlatma metnini onaylayın.",
      );
    if (hatalar.length > 0) {
      setHata({ metin: hatalar.join(" "), kota: false });
      return;
    }
    setBekleniyor(true);
    try {
      const yanit = await kayitOl({
        email: email.trim(),
        sifre,
        rol,
        ad: ad.trim(),
        kvkk_onay: kvkkOnay,
        ...(rol === "genc"
          ? { genc_profili: formuProfileCevir(profil) }
          : { firma_profili: formuFirmaProfilineCevir(firma) }),
      });
      tokenYaz(yanit.token);
      // Genç doğrudan Keşif sohbetine (onboarding), kurum paneline.
      router.replace(kayittanSonra(yanit.rol, sonra));
    } catch (sebep) {
      setHata(hatayaCevir(sebep));
      setBekleniyor(false);
    }
  }

  const girisYolu = sonra
    ? `/giris?sonra=${encodeURIComponent(sonra)}`
    : "/giris";

  return (
    <main className="mx-auto flex w-full max-w-xl flex-1 flex-col gap-8 px-4 py-10 sm:px-6 sm:py-16">
      <header className="flex flex-col gap-2">
        <h1 className="font-heading text-2xl font-semibold text-ana sm:text-3xl">
          Kayıt ol
        </h1>
        <p className="text-sm text-pretty text-muted-foreground">
          {rol === "genc"
            ? "Kayıttan sonra kısa bir sohbetle yetenek kartını oluşturacağız."
            : "Kayıttan sonra doğrudan paneline geçersin."}
        </p>
      </header>

      <form className="flex flex-col gap-5" onSubmit={gonder}>
        <fieldset className="flex flex-col gap-2">
          <legend className="mb-1 text-sm font-medium">
            Kim olarak katılıyorsun?
          </legend>
          <div className="grid gap-2 sm:grid-cols-2">
            {ROLLER.map((secenek) => (
              <label
                key={secenek.deger}
                className={cn(
                  "flex cursor-pointer flex-col gap-1 rounded-lg border px-4 py-3 text-sm",
                  rol === secenek.deger
                    ? "border-ana bg-card ring-1 ring-ana"
                    : "border-kenar hover:border-ana/40",
                )}
              >
                <span className="flex items-center gap-2 font-medium">
                  <input
                    type="radio"
                    name="rol"
                    value={secenek.deger}
                    checked={rol === secenek.deger}
                    onChange={() => setRol(secenek.deger)}
                    required
                    className="accent-ana"
                  />
                  {secenek.baslik}
                </span>
                <span className="text-pretty text-muted-foreground">
                  {secenek.aciklama}
                </span>
              </label>
            ))}
          </div>
        </fieldset>

        <FormAlani
          etiket={rol === "kurum" ? "Kurumun adı" : "Adın"}
          htmlFor="ad"
        >
          <Input
            id="ad"
            value={ad}
            onChange={(olay) => setAd(olay.target.value)}
            required
            autoComplete={rol === "kurum" ? "organization" : "name"}
          />
        </FormAlani>
        {rol === "genc" ? (
          <p className="-mt-3 text-xs text-pretty text-muted-foreground">
            Adın kartında kurumlara görünür. E-postan ise yalnızca bir kurumun
            ilgisini kabul ettiğinde paylaşılır.
          </p>
        ) : null}

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
            minLength={SIFRE_EN_AZ}
            autoComplete="new-password"
          />
        </FormAlani>
        <p className="-mt-3 text-xs text-muted-foreground">
          En az {SIFRE_EN_AZ} karakter.
        </p>

        {rol === "genc" ? (
          <GencProfilAlanlari form={profil} onDegis={setProfil} />
        ) : null}
        {rol === "kurum" ? (
          <FirmaProfilAlanlari form={firma} onDegis={setFirma} />
        ) : null}

        {rol ? (
          <>
            <label className="flex items-start gap-2 text-sm text-pretty">
              <input
                type="checkbox"
                checked={kvkkOnay}
                onChange={(olay) => setKvkkOnay(olay.target.checked)}
                required
                className="mt-0.5 accent-ana"
              />
              <span>
                <Link
                  href="/kvkk"
                  target="_blank"
                  className="text-baglanti underline"
                >
                  KVKK aydınlatma metnini
                </Link>{" "}
                okudum; verilerimin bu metinde anlatılan amaçlarla işlenmesini
                onaylıyorum.
              </span>
            </label>
          </>
        ) : null}

        {hata ? <HataKutusu hata={hata} /> : null}

        <Button
          type="submit"
          size="lg"
          disabled={bekleniyor || !rol}
          className="w-fit"
        >
          {bekleniyor ? "Kayıt olunuyor…" : "Kayıt ol"}
        </Button>
      </form>

      <p className="text-sm text-muted-foreground">
        Zaten hesabın var mı?{" "}
        <Link href={girisYolu} className="text-baglanti underline">
          Giriş yap
        </Link>
      </p>
    </main>
  );
}
