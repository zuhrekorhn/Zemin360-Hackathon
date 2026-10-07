"use client";

import { useState } from "react";

import { CokluSecim } from "@/components/coklu-secim";
import { useGirisliHesap } from "@/components/giris-kapisi";
import { KartAlanlari } from "@/components/kart-alanlari";
import { KartOnizleme } from "@/components/kesif/kart-onizleme";
import { FormAlani } from "@/components/sohbet";
import { Button } from "@/components/ui/button";
import type { GencProfili, KartTaslagi } from "@/lib/api";
import {
  eksikKartAlanlari,
  kartAlanDegerleri,
  kartAlanlariniCevir,
} from "@/lib/kart-duzenleme";
import { onaydaProfilSorulmali } from "@/lib/profil";
import {
  CALISMA_MODELLERI,
  MUSAITLIKLER,
  SEHIR_SECENEKLERI,
} from "@/lib/sabitler";

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
      <section className="flex flex-col gap-3">
        <h2 className="font-heading text-xl font-semibold text-ana">
          Kart taslağın
        </h2>
        <p className="text-sm text-pretty text-muted-foreground">
          Sohbetten çıkan kart bu. Gözden geçir, gerekirse düzelt, doğruysa
          aşağıdan onayla.
        </p>
        {ilkEksikler.length > 0 ? (
          <p className="text-sm text-pretty">
            Sohbette netleşmeyen alanlar boş kaldı; onaylamadan önce doldur.
          </p>
        ) : null}
        <KartOnizleme
          taslak={{ ...taslak, somut_ciktilar: ciktilar }}
          ustAlanlar={
            <div className="flex flex-col gap-3 px-4 py-4">
              <KartAlanlari
                kimlik="taslak"
                degerler={alanlar}
                onDegis={(alan, deger) =>
                  setAlanlar((onceki) => ({ ...onceki, [alan]: deger }))
                }
              />
            </div>
          }
          duzenlenebilir
          onCiktiDegis={(sira, alan, deger) =>
            setCiktilar((oncekiler) =>
              oncekiler.map((cikti, i) =>
                i === sira ? { ...cikti, [alan]: deger || null } : cikti,
              ),
            )
          }
          onCiktiSil={(sira) =>
            setCiktilar((oncekiler) => oncekiler.filter((_, i) => i !== sira))
          }
        />
      </section>

      <section className="flex flex-col gap-4">
        <div className="flex flex-col gap-1">
          <h2 className="font-heading text-xl font-semibold text-ana">
            {profilSor ? "Nerede ve nasıl çalışabilirsin" : "Onay"}
          </h2>
          <p className="text-sm text-pretty text-muted-foreground">
            {profilSor
              ? "Eşleştirme bu bilgilerle yapılır. "
              : "Çalışma tercihlerini kartın onaylandıktan sonra kart sayfasından değiştirebilirsin. "}
            E-postan kartta görünmez; iletişim ancak karşılıklı ilgiyle açılır.
          </p>
        </div>

        <div className="flex flex-col gap-4">
          {profilSor ? (
            <ProfilSorulari profil={profil} onDegis={setProfil} />
          ) : null}

          <Button
            type="submit"
            size="lg"
            disabled={bekleniyor}
            className="w-fit"
          >
            {bekleniyor ? "Kaydediliyor…" : "Kartı onayla"}
          </Button>
        </div>
      </section>
    </form>
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
    <div className="grid gap-4 sm:grid-cols-2">
      <FormAlani etiket="Şehir" htmlFor="sehir">
        {/* Serbest metin değil: yazım farkı eşleştirmeyi sessizce
          bozuyordu (bkz. backend/app/core/sehir.py). */}
        <select
          id="sehir"
          value={profil.sehir}
          required
          onChange={(olay) => onDegis({ ...profil, sehir: olay.target.value })}
          className="h-8 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-baglanti focus-visible:ring-3 focus-visible:ring-baglanti/30"
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
