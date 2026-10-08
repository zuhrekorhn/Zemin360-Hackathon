"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { Sayfa, SayfaBasligi, SayfaDurumu } from "@/components/sayfa";
import { DogrulanmisFirma } from "@/components/dogrulanmis-firma";
import {
  FirmaTanitimAlanlari,
  FirmaTemelAlanlari,
} from "@/components/firma-profil-alanlari";
import { GirisKapisi } from "@/components/giris-kapisi";
import { FormAlani, HataKutusu } from "@/components/sohbet";
import { Button } from "@/components/ui/button";
import { FormBolumu } from "@/components/ui/form-bolumu";
import { Input } from "@/components/ui/input";
import { KUTU } from "@/components/ui/yuzey";
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
import { cn } from "@/lib/utils";

/**
 * Firmanın profil düzenleme sayfası (docs/kararlar.md F2, F9).
 *
 * Kayıt formundaki alanlar; yalnızca kendi profili (token'ın firması). Bu
 * alanlardan önce açılmış firma hesapları paneldeki banttan buraya gelir ve
 * eksikleri ile KVKK onayını burada tamamlar. Firmaya "siz".
 */
const BOLUMLER = [
  { id: "kimlik", etiket: "Ad ve e-posta" },
  { id: "temel", etiket: "Tür, sektör ve şehir" },
  { id: "tanitim", etiket: "Firmanızı tanıtın" },
  { id: "dogrulama", etiket: "Firma doğrulaması" },
];

export default function FirmaProfilSayfasi() {
  return (
    <GirisKapisi roller={["kurum"]} genislik="genis">
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
    return <SayfaDurumu genislik="genis" hata={hata} />;
  }

  return (
    <Sayfa genislik="genis">
      <div className="grid items-start gap-8 lg:grid-cols-[15rem_minmax(0,1fr)]">
        <nav
          aria-label="Firma profili bölümleri"
          className="hidden flex-col gap-1 lg:sticky lg:top-24 lg:flex"
        >
          {BOLUMLER.map((bolum) => (
            <a
              key={bolum.id}
              href={`#${bolum.id}`}
              className="rounded-lg px-3 py-2 text-sm text-muted-foreground hover:bg-muted hover:text-metin"
            >
              {bolum.etiket}
            </a>
          ))}
          <div className="mt-3 border-t border-kenar pt-3">
            <Link
              href="/kurum/kart"
              className="block rounded-lg px-3 py-2 text-sm text-baglanti hover:bg-muted"
            >
              Firma kartınız
            </Link>
          </div>
        </nav>

        <div className="flex min-w-0 max-w-3xl flex-col gap-6">
          <SayfaBasligi
            baslik="Firma profili"
            aciklama="Firmanızın kayıt bilgileri. İş birliği ortağı ararken sizi bulacak kişilere ne yaptığınızı ise firma kartınız anlatır."
            etiket={
              profil.dogrulandi ? <DogrulanmisFirma dogrulandi /> : undefined
            }
          />

          <form className={cn(KUTU, "flex flex-col")} onSubmit={kaydet}>
            <FormBolumu id="kimlik">
              <div className="flex flex-col gap-4">
                <FormAlani etiket="Firma adı" htmlFor="ad">
                  <Input
                    id="ad"
                    value={ad}
                    onChange={(olay) => setAd(olay.target.value)}
                    required
                    autoComplete="organization"
                  />
                </FormAlani>
                <div className="flex flex-col gap-1">
                  <span className="text-sm font-medium">
                    İletişim e-postası
                  </span>
                  <span className="text-sm text-muted-foreground">
                    {profil.email ? `${profil.email} · ` : ""}
                    yalnızca karşılıklı ilgi oluşunca paylaşılır.
                  </span>
                </div>
              </div>
            </FormBolumu>

            <FormBolumu id="temel">
              <FirmaTemelAlanlari form={form} onDegis={setForm} />
            </FormBolumu>

            <FormBolumu id="tanitim">
              <FirmaTanitimAlanlari form={form} onDegis={setForm} />
            </FormBolumu>

            {profil.kvkk_onay_tarihi ? null : (
              <FormBolumu>
                <label className="flex items-start gap-2 text-sm text-pretty">
                  <input
                    type="checkbox"
                    checked={kvkkOnay}
                    onChange={(olay) => setKvkkOnay(olay.target.checked)}
                    className="mt-0.5 size-4 accent-ana"
                  />
                  <span>
                    <Link
                      href="/kvkk"
                      target="_blank"
                      className="text-baglanti underline"
                    >
                      KVKK aydınlatma metnini
                    </Link>{" "}
                    okudum; verilerimin bu metinde anlatılan amaçlarla
                    işlenmesini onaylıyorum.
                  </span>
                </label>
              </FormBolumu>
            )}

            <div className="flex flex-col gap-3 rounded-b-xl border-t border-kenar bg-zemin/60 px-6 py-4">
              {hata ? <HataKutusu hata={hata} /> : null}
              <div className="flex flex-wrap items-center gap-3">
                <Button type="submit" size="lg" disabled={bekleniyor}>
                  {bekleniyor ? "Kaydediliyor…" : "Kaydet"}
                </Button>
                {kaydedildi ? (
                  <span className="text-sm text-muted-foreground" role="status">
                    Kaydedildi.
                  </span>
                ) : null}
              </div>
            </div>
          </form>

          <section
            id="dogrulama"
            className={cn(KUTU, "scroll-mt-24 px-6 py-6")}
          >
            <h2 className="font-heading text-lg font-semibold text-ana">
              Firma doğrulaması
            </h2>
            {profil.dogrulandi ? (
              <p className="mt-2 flex flex-wrap items-center gap-2 text-sm text-pretty text-muted-foreground">
                <DogrulanmisFirma dogrulandi />
                Adınızın yanında “Doğrulanmış firma” işareti görünüyor. Web
                sitenizi değiştirirseniz doğrulama yeniden yapılır.
              </p>
            ) : (
              <p className="mt-2 text-sm text-pretty text-muted-foreground">
                Doğrulama bekleniyor. Program ekibi firmanızı doğrulayınca
                adınızın yanında “Doğrulanmış firma” işareti görünür. Web
                sitenizi değiştirirseniz doğrulama yeniden yapılır.
              </p>
            )}
          </section>
        </div>
      </div>
    </Sayfa>
  );
}
