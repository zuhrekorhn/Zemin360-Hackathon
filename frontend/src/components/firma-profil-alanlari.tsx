"use client";

import { FormAlani } from "@/components/sohbet";
import { Input } from "@/components/ui/input";
import { SECIM_SINIFI } from "@/components/ui/secim";
import {
  CALISAN_ARALIKLARI,
  FIRMA_TURLERI,
  type FirmaProfilFormu,
  TANITIM_EN_UZUN,
} from "@/lib/firma-profil";
import { SEHIR_SECENEKLERI } from "@/lib/sabitler";
import { cn } from "@/lib/utils";

/**
 * Firmanın profil alanları (docs/kararlar.md F2). Kayıt
 * formu ve /kurum/profil aynı parçayı kullanır; doğrulama `lib/firma-profil.ts`'de.
 *
 * Vergi numarası, adres ve telefon bilinçli olarak yok. Firmaya "siz".
 */
type AlanProps = {
  form: FirmaProfilFormu;
  onDegis: (form: FirmaProfilFormu) => void;
};

/** Kayıt formu: iki parça arka arkaya. Profil sayfası parçaları ayrı bölümlerde çizer. */
export function FirmaProfilAlanlari(props: AlanProps) {
  return (
    <div className="flex flex-col gap-6">
      <FirmaTemelAlanlari {...props} />
      <FirmaTanitimAlanlari {...props} />
    </div>
  );
}

/** Zorunlu parça: firma türü, sektör, şehir. */
export function FirmaTemelAlanlari({ form, onDegis }: AlanProps) {
  function alan<K extends keyof FirmaProfilFormu>(
    ad: K,
    deger: FirmaProfilFormu[K],
  ) {
    onDegis({ ...form, [ad]: deger });
  }

  return (
    <div className="flex flex-col gap-6">
      <fieldset className="flex flex-col gap-2">
        <legend className="mb-1 text-sm font-medium">Firma türü</legend>
        <div className="grid gap-2 sm:grid-cols-3">
          {FIRMA_TURLERI.map((secenek) => (
            <label
              key={secenek.deger}
              className={cn(
                "flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-sm",
                form.tur === secenek.deger
                  ? "border-ana bg-card ring-1 ring-ana"
                  : "border-kenar hover:border-ana/40",
              )}
            >
              <input
                type="radio"
                name="firma-turu"
                value={secenek.deger}
                checked={form.tur === secenek.deger}
                onChange={() => alan("tur", secenek.deger)}
                required
                className="accent-ana"
              />
              {secenek.etiket}
            </label>
          ))}
        </div>
        <p className="text-xs text-pretty text-muted-foreground">
          İş birliği ortağı ararken hangi tür firmalarla eşleşeceğinizi
          belirler.
        </p>
      </fieldset>

      <div className="grid gap-4 sm:grid-cols-2">
        <FormAlani etiket="Sektör" htmlFor="firma-sektor">
          <Input
            id="firma-sektor"
            value={form.sektor}
            onChange={(olay) => alan("sektor", olay.target.value)}
            required
          />
        </FormAlani>

        <FormAlani etiket="Şehir" htmlFor="firma-sehir">
          <select
            id="firma-sehir"
            value={form.sehir}
            required
            onChange={(olay) => alan("sehir", olay.target.value)}
            className={SECIM_SINIFI}
          >
            {SEHIR_SECENEKLERI.map((secenek) => (
              <option key={secenek.deger} value={secenek.deger}>
                {secenek.etiket}
              </option>
            ))}
          </select>
        </FormAlani>
      </div>
    </div>
  );
}

/** İsteğe bağlı parça: web sitesi, çalışan sayısı, tanıtım, formu dolduran. */
export function FirmaTanitimAlanlari({ form, onDegis }: AlanProps) {
  function alan<K extends keyof FirmaProfilFormu>(
    ad: K,
    deger: FirmaProfilFormu[K],
  ) {
    onDegis({ ...form, [ad]: deger });
  }

  return (
    <div className="flex flex-col gap-6">
      <fieldset className="flex flex-col gap-4">
        <legend className="mb-1 font-heading text-lg font-semibold text-ana">
          Firmanızı tanıtın{" "}
          <span className="text-sm font-normal text-muted-foreground">
            (isteğe bağlı)
          </span>
        </legend>

        <FormAlani etiket="Web sitesi" htmlFor="firma-site" istegeBagli>
          <Input
            id="firma-site"
            value={form.web_sitesi}
            onChange={(olay) => alan("web_sitesi", olay.target.value)}
            placeholder="ör. ornekfirma.com"
            autoComplete="url"
          />
        </FormAlani>

        <div className="grid gap-4 sm:grid-cols-2">
          <FormAlani
            etiket="Çalışan sayısı"
            htmlFor="firma-calisan"
            istegeBagli
          >
            <select
              id="firma-calisan"
              value={form.calisan_araligi}
              onChange={(olay) =>
                alan(
                  "calisan_araligi",
                  olay.target.value as FirmaProfilFormu["calisan_araligi"],
                )
              }
              className={SECIM_SINIFI}
            >
              <option value="">Seçiniz</option>
              {CALISAN_ARALIKLARI.map((aralik) => (
                <option key={aralik} value={aralik}>
                  {aralik}
                </option>
              ))}
            </select>
          </FormAlani>

          <FormAlani etiket="Kuruluş yılı" htmlFor="firma-yil" istegeBagli>
            <Input
              id="firma-yil"
              inputMode="numeric"
              value={form.kurulus_yili}
              onChange={(olay) => alan("kurulus_yili", olay.target.value)}
            />
          </FormAlani>
        </div>

        <FormAlani etiket="Kısa tanıtım" htmlFor="firma-tanitim" istegeBagli>
          <textarea
            id="firma-tanitim"
            value={form.tanitim}
            maxLength={TANITIM_EN_UZUN}
            rows={3}
            onChange={(olay) => alan("tanitim", olay.target.value)}
            className="w-full rounded-lg border border-input bg-transparent px-2.5 py-2 text-sm outline-none focus-visible:border-baglanti focus-visible:ring-3 focus-visible:ring-baglanti/30"
          />
        </FormAlani>
        <p className="-mt-3 text-xs text-muted-foreground">
          Bir-iki cümle; en çok {TANITIM_EN_UZUN} karakter.
        </p>

        <div className="grid gap-4 sm:grid-cols-2">
          <FormAlani etiket="Adınız" htmlFor="firma-yetkili" istegeBagli>
            <Input
              id="firma-yetkili"
              value={form.yetkili_ad}
              onChange={(olay) => alan("yetkili_ad", olay.target.value)}
              autoComplete="name"
            />
          </FormAlani>
          <FormAlani etiket="Göreviniz" htmlFor="firma-gorev" istegeBagli>
            <Input
              id="firma-gorev"
              value={form.yetkili_gorev}
              onChange={(olay) => alan("yetkili_gorev", olay.target.value)}
              autoComplete="organization-title"
            />
          </FormAlani>
        </div>
      </fieldset>
    </div>
  );
}
