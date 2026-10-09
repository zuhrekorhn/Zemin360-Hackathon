"use client";

import { Check, ChevronDown, Minus } from "lucide-react";
import { useState } from "react";

import { CokluSecim } from "@/components/coklu-secim";
import { useGirisliHesap } from "@/components/giris-kapisi";
import { IsKalemiFormu } from "@/components/is-kalemi-formu";
import { KartAlanlari } from "@/components/kart-alanlari";
import { FormAlani } from "@/components/sohbet";
import { Button } from "@/components/ui/button";
import { SECIM_SINIFI } from "@/components/ui/secim";
import { OnayCubugu } from "@/components/onay-cubugu";
import { KUTU } from "@/components/ui/yuzey";
import type { GencProfili, KartTaslagi, SomutCiktiTaslagi } from "@/lib/api";
import {
  eksikKartAlanlari,
  kartAlanDegerleri,
  kartAlanlariniCevir,
} from "@/lib/kart-duzenleme";
import { onaydaProfilSorulmali } from "@/lib/profil";
import {
  CALISMA_MODELLERI,
  IS_TURU_ETIKETLERI,
  MUSAITLIKLER,
  SEHIR_SECENEKLERI,
  etiketle,
} from "@/lib/sabitler";
import { cn } from "@/lib/utils";

type ProfilSecimi = {
  sehir: string;
  calismaModelleri: string[];
  musaitlikler: string[];
};

const BOS_PROFIL: ProfilSecimi = {
  sehir: "",
  calismaModelleri: [],
  musaitlikler: [],
};

/**
 * Sohbetten çıkan taslak ve onay (docs/agent-specs.md § 1.3). Kullanıcı son
 * sözü söyler: ajan aynı işi iki kez yazmış, bir şeyi yanlış anlamış ya da bir
 * alanı netleştirememiş olabilir (boş alan onayda doldurulur, yer tutucu
 * yazılmaz). Tek form: zorunlu alan uyarısı sayfanın tamamında çalışsın.
 *
 * Düzen (docs/kararlar.md G18): solda kartın alanları, sağda çalışmalar kapalı
 * kartlar halinde (neyin toplandığı işaretli, düzenleme istenince açılır),
 * altta yapışık onay çubuğu. Altı açık form alt alta dizilmez.
 */
export function TaslakBolumu({
  taslak,
  bekleniyor,
  onOnayla,
}: {
  taslak: KartTaslagi;
  bekleniyor: boolean;
  onOnayla: (profil: GencProfili, duzeltilmisTaslak: KartTaslagi) => void;
}) {
  const [alanlar, setAlanlar] = useState(() => kartAlanDegerleri(taslak));
  const [ciktilar, setCiktilar] = useState(taslak.somut_ciktilar);
  // Açılışta boş gelen alanlar: uyarı yazılırken kaybolmasın diye sabit.
  const [ilkEksikler] = useState(() =>
    eksikKartAlanlari(kartAlanDegerleri(taslak)),
  );
  const [profil, setProfil] = useState<ProfilSecimi>(BOS_PROFIL);
  // Kayıtta alındıysa sorulmaz; bu alanlardan önce açılmış hesapta eksikse sorulur.
  const profilSor = onaydaProfilSorulmali(
    useGirisliHesap().eksik_profil_alanlari,
  );

  function onayla(olay: React.FormEvent) {
    olay.preventDefault();
    if (bekleniyor || eksikKartAlanlari(alanlar).length > 0) return;
    onOnayla(
      // Boş profil kayıtlı değerleri silmez (backend kuralı).
      profilSor
        ? {
            sehir: profil.sehir,
            calisma_modelleri: profil.calismaModelleri,
            musaitlikler: profil.musaitlikler,
          }
        : {},
      { ...taslak, ...kartAlanlariniCevir(alanlar), somut_ciktilar: ciktilar },
    );
  }

  return (
    <form className="flex flex-col gap-8" onSubmit={onayla}>
      {ilkEksikler.length > 0 ? (
        <p className="rounded-lg border border-dashed border-vurgu/60 bg-vurgu/[0.08] px-4 py-3 text-sm text-pretty">
          Sohbette netleşmeyen alanlar boş kaldı; onaylamadan önce doldur.
        </p>
      ) : null}

      <div className="grid items-start gap-8 lg:grid-cols-[22rem_minmax(0,1fr)]">
        <aside className="flex flex-col gap-4 lg:sticky lg:top-24">
          <section className={cn(KUTU, "flex flex-col gap-4 px-5 py-5")}>
            <h2 className="font-heading text-lg font-semibold text-ana">
              Kartın
            </h2>
            <KartAlanlari
              kimlik="taslak"
              degerler={alanlar}
              onDegis={(alan, deger) =>
                setAlanlar((onceki) => ({ ...onceki, [alan]: deger }))
              }
            />
          </section>
          {profilSor ? (
            <section className={cn(KUTU, "flex flex-col gap-4 px-5 py-5")}>
              <div className="flex flex-col gap-1">
                <h2 className="font-heading text-lg font-semibold text-ana">
                  Nerede ve nasıl çalışabilirsin
                </h2>
                <p className="text-xs text-pretty text-muted-foreground">
                  Eşleştirme bu bilgilerle yapılır.
                </p>
              </div>
              <ProfilSorulari profil={profil} onDegis={setProfil} />
            </section>
          ) : null}
        </aside>

        <section className="flex min-w-0 flex-col gap-4">
          <div className="flex flex-col gap-1">
            <h2 className="flex items-center gap-2.5 font-heading text-2xl font-semibold text-ana">
              Çalışmaların
              <span className="rounded-full bg-ana px-2 py-0.5 font-sans text-xs font-medium text-zemin">
                {ciktilar.length}
              </span>
            </h2>
            <p className="text-sm text-pretty text-muted-foreground">
              Sohbetten çıkanlar. Yanlış anlaşılan bir şey varsa düzelt,
              kartında olmasını istemediğini çıkar. Kanıt ve referansı onaydan
              sonra da ekleyebilirsin.
            </p>
          </div>
          {ciktilar.length === 0 ? (
            <p
              className={cn(KUTU, "px-5 py-5 text-sm text-pretty shadow-none")}
            >
              Henüz çalışma yok. Kartın yine kaydedilir; çalışmalarını sonradan
              ekleyebilirsin.
            </p>
          ) : (
            <ul className="flex flex-col gap-3">
              {ciktilar.map((cikti, sira) => (
                <TaslakCalismasi
                  key={sira}
                  sira={sira}
                  cikti={cikti}
                  onDegis={(alan, deger) =>
                    setCiktilar((oncekiler) =>
                      oncekiler.map((c, i) =>
                        i === sira ? { ...c, [alan]: deger || null } : c,
                      ),
                    )
                  }
                  onCikar={() =>
                    setCiktilar((oncekiler) =>
                      oncekiler.filter((_, i) => i !== sira),
                    )
                  }
                />
              ))}
            </ul>
          )}
        </section>
      </div>

      {/* Onay her zaman görünür: uzun taslakta sayfanın sonuna inmek gerekmesin. */}
      <OnayCubugu
        metin="Doğruysa onayla; kartın kaydedilir ve fırsatlarla eşleşir. Sonra istediğin zaman düzenleyebilirsin. E-postan kartta görünmez."
        etiket="Kartı onayla"
        bekleniyor={bekleniyor}
      />
    </form>
  );
}

/** Çalışmada neyin toplandığı: kart sayfasındaki başlıklarla aynı dil. */
function Isaret({ var: varMi, etiket }: { var: boolean; etiket: string }) {
  return (
    <li
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs",
        varMi
          ? "bg-baglanti/10 text-baglanti"
          : "bg-muted text-muted-foreground",
      )}
    >
      {varMi ? (
        <Check aria-hidden="true" className="size-3" />
      ) : (
        <Minus aria-hidden="true" className="size-3" />
      )}
      {etiket}
      <span className="sr-only">{varMi ? " var" : " yok"}</span>
    </li>
  );
}

function TaslakCalismasi({
  sira,
  cikti,
  onDegis,
  onCikar,
}: {
  sira: number;
  cikti: SomutCiktiTaslagi;
  onDegis: (alan: keyof SomutCiktiTaslagi, deger: string) => void;
  onCikar: () => void;
}) {
  const [acik, setAcik] = useState(!cikti.baslik);
  return (
    <li className={cn(KUTU, "flex flex-col gap-3 px-5 py-4")}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 flex-col gap-1">
          <h3 className="flex flex-wrap items-center gap-2 text-base leading-snug font-semibold">
            {cikti.baslik || "Başlıksız çalışma"}
            {cikti.is_turu ? (
              <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-normal text-muted-foreground">
                {etiketle(IS_TURU_ETIKETLERI, cikti.is_turu)}
              </span>
            ) : null}
          </h3>
          {cikti.aciklama && !acik ? (
            <p className="line-clamp-2 text-sm text-pretty text-muted-foreground">
              {cikti.aciklama}
            </p>
          ) : null}
        </div>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="text-muted-foreground hover:text-destructive"
          onClick={onCikar}
        >
          Çıkar
        </Button>
      </div>

      {!acik ? (
        <ul className="flex flex-wrap gap-1.5" aria-label="Toplananlar">
          <Isaret var={Boolean(cikti.olculebilir_sonuc)} etiket="Sonuç" />
          <Isaret var={Boolean(cikti.kendi_rolu)} etiket="Payın" />
          <Isaret var={Boolean(cikti.kanit_linki)} etiket="Kanıt linki" />
          <Isaret var={Boolean(cikti.referans_email)} etiket="Referans" />
        </ul>
      ) : (
        <div className="border-t border-kenar pt-4">
          <IsKalemiFormu
            kimlik={`cikti-${sira}`}
            cikti={cikti}
            onDegis={onDegis}
          />
        </div>
      )}

      <button
        type="button"
        aria-expanded={acik}
        onClick={() => setAcik((onceki) => !onceki)}
        className="inline-flex w-fit items-center gap-1 text-sm font-medium text-baglanti outline-none hover:underline focus-visible:ring-3 focus-visible:ring-ring/50"
      >
        {acik ? "Kapat" : "Düzenle"}
        <ChevronDown
          aria-hidden="true"
          className={cn("size-4 transition-transform", acik && "rotate-180")}
        />
      </button>
    </li>
  );
}

/** Kayıt formu bu alanlardan önce açılmış hesaplarda onayda sorulanlar. */
function ProfilSorulari({
  profil,
  onDegis,
}: {
  profil: ProfilSecimi;
  onDegis: (profil: ProfilSecimi) => void;
}) {
  return (
    <div className="flex flex-col gap-4">
      <FormAlani etiket="Şehir" htmlFor="sehir">
        {/* Serbest metin değil: yazım farkı eşleştirmeyi sessizce
          bozuyordu (bkz. backend/app/core/sehir.py). */}
        <select
          id="sehir"
          value={profil.sehir}
          required
          onChange={(olay) => onDegis({ ...profil, sehir: olay.target.value })}
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
        secili={profil.calismaModelleri}
        onDegis={(calismaModelleri) => onDegis({ ...profil, calismaModelleri })}
      />

      <CokluSecim
        baslik="Müsaitlik"
        ipucu="(uygun olanların hepsini işaretle; boş bırakabilirsin)"
        secenekler={MUSAITLIKLER}
        secili={profil.musaitlikler}
        onDegis={(musaitlikler) => onDegis({ ...profil, musaitlikler })}
      />
    </div>
  );
}
