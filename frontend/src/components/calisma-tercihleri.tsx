"use client";

import { ListeIskeleti } from "@/components/ui/iskelet";
import { useEffect, useRef, useState } from "react";

import { CalismaTercihleriAlanlari } from "@/components/genc-profil-alanlari";
import { tarihYaz } from "@/components/panel";
import { HataKutusu } from "@/components/sohbet";
import { Button } from "@/components/ui/button";
import { KUTU } from "@/components/ui/yuzey";
import { type GencProfil, profilGetir, profilGuncelle } from "@/lib/api";
import { type Hata, hatayaCevir } from "@/lib/hata";
import { useOturum } from "@/lib/oturum";
import {
  BOS_PROFIL_FORMU,
  profildenForma,
  tercihGovdesi,
  tercihHatalari,
} from "@/lib/profil";
import { CALISMA_MODELLERI, MUSAITLIKLER, sehirEtiketi } from "@/lib/sabitler";
import { cn } from "@/lib/utils";

/**
 * Kart sayfasındaki "Çalışma tercihlerin" (docs/kararlar.md G18): şehir, çalışma
 * modeli, müsaitlik ve başlama tarihi. Eşleştirme bunlarla yapıldığı için
 * kartın yanında; kayıt bilgileri (eğitim, bağlantılar) Hesabım'da.
 * Okuma görünümü ve yerinde düzenleme; kayıt yalnızca bu alanları gönderir.
 */

function secimEtiketleri(
  secenekler: readonly { deger: string; etiket: string }[],
  secili: string[],
): string {
  return (
    secenekler
      .filter((s) => secili.includes(s.deger))
      .map((s) => s.etiket)
      .join(", ") || "—"
  );
}

export function CalismaTercihleri() {
  const { tazele } = useOturum();
  const [profil, setProfil] = useState<GencProfil | null>(null);
  const [form, setForm] = useState(BOS_PROFIL_FORMU);
  const [duzenleniyor, setDuzenleniyor] = useState(false);
  const [bekleniyor, setBekleniyor] = useState(false);
  const [hata, setHata] = useState<Hata | null>(null);
  const okundu = useRef(false);

  useEffect(() => {
    if (okundu.current) return;
    okundu.current = true;
    profilGetir()
      .then((gelen) => {
        setProfil(gelen);
        setForm(profildenForma(gelen));
      })
      .catch((sebep) => setHata(hatayaCevir(sebep)));
  }, []);

  async function kaydet(olay: React.FormEvent) {
    olay.preventDefault();
    if (bekleniyor) return;
    const hatalar = tercihHatalari(form);
    if (hatalar.length > 0) {
      setHata({ metin: hatalar.join(" "), kota: false });
      return;
    }
    setHata(null);
    setBekleniyor(true);
    try {
      const yeni = await profilGuncelle(tercihGovdesi(form));
      setProfil(yeni);
      setForm(profildenForma(yeni));
      setDuzenleniyor(false);
      // Ana sayfadaki "Tamamlanacaklar" /me'den okunuyor.
      void tazele();
    } catch (sebep) {
      setHata(hatayaCevir(sebep));
    } finally {
      setBekleniyor(false);
    }
  }

  const satirlar = profil
    ? [
        ["Şehir", profil.sehir ? sehirEtiketi(profil.sehir) : "—"],
        [
          "Çalışma modeli",
          secimEtiketleri(CALISMA_MODELLERI, profil.calisma_modelleri),
        ],
        ["Müsaitlik", secimEtiketleri(MUSAITLIKLER, profil.musaitlikler)],
        [
          "Başlangıç",
          profil.musaitlik_baslangici
            ? tarihYaz(profil.musaitlik_baslangici)
            : "Hemen",
        ],
      ]
    : [];

  return (
    <section
      id="tercihler"
      aria-labelledby="tercihler-baslik"
      className={cn(KUTU, "flex scroll-mt-24 flex-col gap-4 px-5 py-5")}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex flex-col gap-0.5">
          <h2
            id="tercihler-baslik"
            className="font-heading text-base font-semibold text-ana"
          >
            Çalışma tercihlerin
          </h2>
          <p className="text-xs text-pretty text-muted-foreground">
            Sana gelen fırsatlar bu tercihlere göre seçilir.
          </p>
        </div>
        {profil && !duzenleniyor ? (
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => setDuzenleniyor(true)}
          >
            Düzenle
          </Button>
        ) : null}
      </div>

      {hata ? <HataKutusu hata={hata} /> : null}

      {!profil ? (
        hata ? null : (
          <ListeIskeleti satir={1} />
        )
      ) : duzenleniyor ? (
        <form className="flex flex-col gap-4" onSubmit={kaydet}>
          <CalismaTercihleriAlanlari form={form} onDegis={setForm} />
          <div className="flex flex-wrap gap-2">
            <Button type="submit" size="sm" disabled={bekleniyor}>
              {bekleniyor ? "Kaydediliyor…" : "Kaydet"}
            </Button>
            <Button
              type="button"
              size="sm"
              variant="ghost"
              onClick={() => {
                setForm(profildenForma(profil));
                setHata(null);
                setDuzenleniyor(false);
              }}
            >
              Vazgeç
            </Button>
          </div>
        </form>
      ) : (
        <dl className="grid gap-x-6 gap-y-3 text-sm">
          {satirlar.map(([etiket, deger]) => (
            <div key={etiket} className="flex flex-col gap-0.5">
              <dt className="text-xs text-muted-foreground">{etiket}</dt>
              <dd className="text-metin">{deger}</dd>
            </div>
          ))}
        </dl>
      )}
    </section>
  );
}
