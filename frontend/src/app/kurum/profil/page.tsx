"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { DogrulanmisFirma } from "@/components/dogrulanmis-firma";
import { FirmaProfilAlanlari } from "@/components/firma-profil-alanlari";
import { GirisKapisi } from "@/components/giris-kapisi";
import { FormAlani, HataKutusu } from "@/components/sohbet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  type FirmaProfil,
  firmaProfiliGetir,
  firmaProfiliGuncelle,
} from "@/lib/api";
import {
  BOS_FIRMA_FORMU,
  firmaFormunuDogrula,
  firmaProfilindenForma,
  formuFirmaProfilineCevir,
} from "@/lib/firma-profil";
import { type Hata, hatayaCevir } from "@/lib/hata";
import { useOturum } from "@/lib/oturum";

/**
 * Firmanın profil düzenleme sayfası (docs/plans/firma-akisi.md § 0 kararlar 2, 9).
 *
 * Kayıt formundaki alanlar; yalnızca kendi profili (token'ın firması). Bu
 * alanlardan önce açılmış firma hesapları paneldeki banttan buraya gelir ve
 * eksikleri ile KVKK onayını burada tamamlar. Firmaya "siz".
 */
export default function FirmaProfilSayfasi() {
  return (
    <GirisKapisi roller={["kurum"]}>
      <FirmaProfilIcerigi />
    </GirisKapisi>
  );
}

function FirmaProfilIcerigi() {
  const { tazele } = useOturum();
  const [profil, setProfil] = useState<FirmaProfil | null>(null);
  const [ad, setAd] = useState("");
  const [form, setForm] = useState(BOS_FIRMA_FORMU);
  const [kvkkOnay, setKvkkOnay] = useState(false);
  const [bekleniyor, setBekleniyor] = useState(false);
  const [kaydedildi, setKaydedildi] = useState(false);
  const [hata, setHata] = useState<Hata | null>(null);
  const okundu = useRef(false);

  function yukle(yeni: FirmaProfil) {
    setProfil(yeni);
    setAd(yeni.ad);
    setForm(firmaProfilindenForma(yeni));
  }

  useEffect(() => {
    if (okundu.current) return;
    okundu.current = true;
    firmaProfiliGetir()
      .then(yukle)
      .catch((sebep) => setHata(hatayaCevir(sebep)));
  }, []);

  async function kaydet(olay: React.FormEvent) {
    olay.preventDefault();
    if (bekleniyor || !profil) return;
    setHata(null);
    setKaydedildi(false);
    const hatalar = firmaFormunuDogrula(form);
    if (!ad.trim()) hatalar.unshift("Firma adı boş olamaz.");
    if (hatalar.length > 0) {
      setHata({ metin: hatalar.join(" "), kota: false });
      return;
    }
    setBekleniyor(true);
    try {
      const yeni = await firmaProfiliGuncelle({
        ...formuFirmaProfilineCevir(form),
        ad: ad.trim(),
        ...(kvkkOnay ? { kvkk_onay: true } : {}),
      });
      yukle(yeni);
      setKaydedildi(true);
      // Paneldeki bant ve menü /me'den okunuyor.
      void tazele();
    } catch (sebep) {
      setHata(hatayaCevir(sebep));
    } finally {
      setBekleniyor(false);
    }
  }

  if (!profil) {
    return (
      <main className="mx-auto w-full max-w-xl flex-1 px-4 py-10 sm:px-6">
        {hata ? (
          <HataKutusu hata={hata} />
        ) : (
          <p className="text-sm text-muted-foreground" role="status">
            Yükleniyor…
          </p>
        )}
      </main>
    );
  }

  return (
    <main className="mx-auto flex w-full max-w-xl flex-1 flex-col gap-8 px-4 py-10 sm:px-6 sm:py-16">
      <header className="flex flex-col gap-2">
        <h1 className="font-heading text-2xl font-semibold text-ana sm:text-3xl">
          Firma profili
        </h1>
        <p className="text-sm text-pretty text-muted-foreground">
          Firmanızın temel bilgileri. İletişim e-postanız
          {profil.email ? ` (${profil.email})` : ""} yalnızca karşılıklı ilgi
          oluşunca paylaşılır.
        </p>
      </header>

      <p className="flex flex-wrap items-center gap-2 text-sm">
        {profil.dogrulandi ? (
          <DogrulanmisFirma dogrulandi />
        ) : (
          <span className="text-muted-foreground">
            Doğrulama bekleniyor. Program ekibi firmanızı doğrulayınca adınızın
            yanında “Doğrulanmış firma” işareti görünür. Web sitenizi
            değiştirirseniz doğrulama yeniden yapılır.
          </span>
        )}
      </p>

      <form className="flex flex-col gap-6" onSubmit={kaydet}>
        <FormAlani etiket="Firma adı" htmlFor="ad">
          <Input
            id="ad"
            value={ad}
            onChange={(olay) => setAd(olay.target.value)}
            required
            autoComplete="organization"
          />
        </FormAlani>

        <FirmaProfilAlanlari form={form} onDegis={setForm} />

        {profil.kvkk_onay_tarihi ? null : (
          <label className="flex items-start gap-2 text-sm text-pretty">
            <input
              type="checkbox"
              checked={kvkkOnay}
              onChange={(olay) => setKvkkOnay(olay.target.checked)}
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
        )}

        {hata ? <HataKutusu hata={hata} /> : null}
        {kaydedildi ? (
          <p className="text-sm text-muted-foreground" role="status">
            Firma profiliniz kaydedildi.
          </p>
        ) : null}

        <div className="flex flex-wrap items-center gap-3">
          <Button type="submit" size="lg" disabled={bekleniyor}>
            {bekleniyor ? "Kaydediliyor…" : "Kaydet"}
          </Button>
          <Link href="/kurum" className="text-sm text-baglanti underline">
            Panele dön
          </Link>
        </div>
      </form>
    </main>
  );
}
