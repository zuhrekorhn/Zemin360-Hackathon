"use client";

import { CokluSecim } from "@/components/coklu-secim";
import { FormAlani } from "@/components/sohbet";
import { Input } from "@/components/ui/input";
import {
  MEZUNIYET_EN_ESKI,
  type ProfilFormu,
  SINIF_EN_AZ,
  SINIF_EN_COK,
} from "@/lib/profil";
import {
  CALISMA_MODELLERI,
  KARIYER_DURUMLARI,
  MUSAITLIKLER,
  SEHIR_SECENEKLERI,
} from "@/lib/sabitler";

const SECIM_SINIFI =
  "h-8 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-baglanti focus-visible:ring-3 focus-visible:ring-baglanti/30";

/**
 * Gencin profil alanları (docs/plans/genc-akisi.md § 5.1). Kayıt formu ve
 * profil sayfası aynı parçayı kullanır; doğrulama `lib/profil.ts`'de.
 *
 * Fotoğraf, yaş, cinsiyet, adres gibi alanlar bilinçli olarak yok: eşleştirme
 * yalnızca yetkinliğe dayanıyor.
 */
export function GencProfilAlanlari({
  form,
  onDegis,
}: {
  form: ProfilFormu;
  onDegis: (form: ProfilFormu) => void;
}) {
  function alan<K extends keyof ProfilFormu>(ad: K, deger: ProfilFormu[K]) {
    onDegis({ ...form, [ad]: deger });
  }

  return (
    <div className="flex flex-col gap-6">
      <fieldset className="flex flex-col gap-4">
        <legend className="mb-2 font-heading text-lg font-semibold text-ana">
          Nerede ve nasıl çalışabilirsin
        </legend>
        <p className="-mt-2 text-xs text-pretty text-muted-foreground">
          Eşleştirme yalnızca bu bilgilerle ve yetkinliklerinle yapılır.
        </p>

        <FormAlani etiket="Şehir" htmlFor="sehir">
          <select
            id="sehir"
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

        <CokluSecim
          baslik="Çalışma modeli"
          ipucu="(kabul ettiklerini işaretle)"
          aciklama="Nerede çalışacağın. Müsaitlik ayrı bir şey: ne kadar süreyle."
          secenekler={CALISMA_MODELLERI}
          secili={form.calisma_modelleri}
          onDegis={(secili) => alan("calisma_modelleri", secili)}
        />

        <CokluSecim
          baslik="Müsaitlik"
          ipucu="(uygun olanların hepsini işaretle)"
          secenekler={MUSAITLIKLER}
          secili={form.musaitlikler}
          onDegis={(secili) => alan("musaitlikler", secili)}
        />

        <FormAlani
          etiket="Ne zaman başlayabilirsin?"
          htmlFor="musaitlik_baslangici"
          istegeBagli
        >
          <Input
            id="musaitlik_baslangici"
            type="date"
            value={form.musaitlik_baslangici}
            onChange={(olay) => alan("musaitlik_baslangici", olay.target.value)}
          />
        </FormAlani>
      </fieldset>

      <fieldset className="flex flex-col gap-4">
        <legend className="mb-2 font-heading text-lg font-semibold text-ana">
          Eğitim ve durum
        </legend>

        <FormAlani etiket="Durumun" htmlFor="kariyer_durumu">
          <select
            id="kariyer_durumu"
            value={form.kariyer_durumu}
            required
            onChange={(olay) =>
              alan(
                "kariyer_durumu",
                olay.target.value as ProfilFormu["kariyer_durumu"],
              )
            }
            className={SECIM_SINIFI}
          >
            <option value="">Seçiniz</option>
            {KARIYER_DURUMLARI.map((secenek) => (
              <option key={secenek.deger} value={secenek.deger}>
                {secenek.etiket}
              </option>
            ))}
          </select>
        </FormAlani>

        <div className="grid gap-4 sm:grid-cols-2">
          <FormAlani etiket="Okul" htmlFor="okul" istegeBagli>
            <Input
              id="okul"
              value={form.okul}
              onChange={(olay) => alan("okul", olay.target.value)}
            />
          </FormAlani>
          <FormAlani etiket="Bölüm" htmlFor="bolum" istegeBagli>
            <Input
              id="bolum"
              value={form.bolum}
              onChange={(olay) => alan("bolum", olay.target.value)}
            />
          </FormAlani>
          {form.kariyer_durumu === "ogrenci" ? (
            <FormAlani etiket="Sınıf" htmlFor="sinif" istegeBagli>
              <Input
                id="sinif"
                type="number"
                inputMode="numeric"
                min={SINIF_EN_AZ}
                max={SINIF_EN_COK}
                value={form.sinif}
                onChange={(olay) => alan("sinif", olay.target.value)}
              />
            </FormAlani>
          ) : null}
          <FormAlani
            etiket={
              form.kariyer_durumu === "ogrenci"
                ? "Beklenen mezuniyet yılı"
                : "Mezuniyet yılı"
            }
            htmlFor="mezuniyet_yili"
            istegeBagli
          >
            <Input
              id="mezuniyet_yili"
              type="number"
              inputMode="numeric"
              min={MEZUNIYET_EN_ESKI}
              value={form.mezuniyet_yili}
              onChange={(olay) => alan("mezuniyet_yili", olay.target.value)}
            />
          </FormAlani>
        </div>
      </fieldset>

      <fieldset className="flex flex-col gap-4">
        <legend className="mb-2 font-heading text-lg font-semibold text-ana">
          Bağlantıların
        </legend>
        {(
          [
            ["github_url", "GitHub", "github.com/kullanici-adin"],
            ["linkedin_url", "LinkedIn", "linkedin.com/in/…"],
            ["portfolyo_url", "Portfolyo", "kisisel-siten.com"],
          ] as const
        ).map(([ad, etiket, ornek]) => (
          <FormAlani key={ad} etiket={etiket} htmlFor={ad} istegeBagli>
            <Input
              id={ad}
              inputMode="url"
              placeholder={ornek}
              value={form[ad]}
              onChange={(olay) => alan(ad, olay.target.value)}
            />
          </FormAlani>
        ))}
      </fieldset>
    </div>
  );
}
