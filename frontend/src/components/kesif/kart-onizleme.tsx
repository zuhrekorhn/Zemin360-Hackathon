"use client";

import { IsKalemiFormu } from "@/components/is-kalemi-formu";
import { Button } from "@/components/ui/button";
import type { KartTaslagi, SomutCiktiTaslagi } from "@/lib/api";
import {
  DENEYIM_ETIKETLERI,
  IS_TURU_ETIKETLERI,
  etiketle,
} from "@/lib/sabitler";

/**
 * Keşif'teki kart önizlemesi: onay öncesi taslak (düzenlenebilir) ve kayıttan
 * hemen sonraki kart (salt okunur) aynı görünümü paylaşır.
 *
 * Görsel dil (docs/design-language.md): hairline çizgili, az yuvarlak —
 * "resmi belge".
 */
export function KartOnizleme({
  taslak,
  ustAlanlar,
  duzenlenebilir = false,
  onCiktiDegis,
  onCiktiSil,
}: {
  taslak: KartTaslagi;
  /** Verilirse salt okunur özet satırlarının yerine geçer (taslak düzenleme). */
  ustAlanlar?: React.ReactNode;
  /** Onaydan önce kullanıcı çıktıları düzeltebilsin diye. */
  duzenlenebilir?: boolean;
  onCiktiDegis?: (
    sira: number,
    alan: keyof SomutCiktiTaslagi,
    deger: string,
  ) => void;
  onCiktiSil?: (sira: number) => void;
}) {
  return (
    <article className="rounded-sm border border-kenar bg-card">
      {ustAlanlar ?? <KartOzeti taslak={taslak} />}

      <div className="border-t border-kenar px-4 py-3">
        <h3 className="text-xs text-muted-foreground">Çalışmaların</h3>
        {taslak.somut_ciktilar.length === 0 ? (
          <p className="mt-1 text-sm text-pretty">
            Henüz yok. Kartın yine kaydedilir; çalışmalarını sonradan
            ekleyebilirsin.
          </p>
        ) : (
          <ul className="mt-2 flex flex-col gap-3">
            {taslak.somut_ciktilar.map((cikti, sira) =>
              duzenlenebilir && onCiktiDegis && onCiktiSil ? (
                <li
                  key={sira}
                  className="flex flex-col gap-2 rounded-sm border border-kenar px-3 py-3"
                >
                  <div className="flex justify-end">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => onCiktiSil(sira)}
                    >
                      Çıkar
                    </Button>
                  </div>
                  <IsKalemiFormu
                    kimlik={`cikti-${sira}`}
                    cikti={cikti}
                    onDegis={(alan, deger) => onCiktiDegis(sira, alan, deger)}
                  />
                </li>
              ) : (
                <li key={sira}>
                  <CalismaOzeti cikti={cikti} />
                </li>
              ),
            )}
          </ul>
        )}
      </div>
    </article>
  );
}

function CalismaOzeti({ cikti }: { cikti: SomutCiktiTaslagi }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-sm font-medium break-words">
        {cikti.baslik}
        {cikti.is_turu ? (
          <span className="ml-2 text-xs font-normal text-muted-foreground">
            {etiketle(IS_TURU_ETIKETLERI, cikti.is_turu)}
          </span>
        ) : null}
      </span>
      {cikti.aciklama ? (
        <span className="text-sm text-pretty text-muted-foreground">
          {cikti.aciklama}
        </span>
      ) : null}
      {cikti.olculebilir_sonuc ? (
        <span className="text-sm text-pretty">
          Sonuç: {cikti.olculebilir_sonuc}
        </span>
      ) : null}
      {cikti.kendi_rolu ? (
        <span className="text-sm text-pretty">Payın: {cikti.kendi_rolu}</span>
      ) : null}
      {cikti.kanit_linki ? (
        <span className="font-mono text-xs break-all text-baglanti">
          {cikti.kanit_linki}
        </span>
      ) : null}
    </div>
  );
}

function KartOzeti({ taslak }: { taslak: KartTaslagi }) {
  return (
    <dl className="grid gap-px bg-kenar sm:grid-cols-2">
      <KartSatiri etiket="Rol / alan" deger={taslak.rol_alani} />
      <KartSatiri
        etiket="Deneyim"
        deger={etiketle(DENEYIM_ETIKETLERI, taslak.deneyim_seviyesi)}
      />
      <KartSatiri
        etiket="Sektör ilgisi"
        deger={taslak.sektor_ilgi_alani.join(", ")}
      />
      <KartSatiri
        etiket="Araçlar"
        deger={taslak.araclar_teknolojiler.join(", ")}
      />
      {taslak.sertifikalar?.length ? (
        <KartSatiri
          etiket="Sertifikalar"
          deger={taslak.sertifikalar.join(", ")}
        />
      ) : null}
      {taslak.diller?.length ? (
        <KartSatiri etiket="Diller" deger={taslak.diller.join(", ")} />
      ) : null}
    </dl>
  );
}

function KartSatiri({
  etiket,
  deger,
}: {
  etiket: string;
  deger: string | null;
}) {
  return (
    <div className="bg-card px-4 py-3">
      <dt className="text-xs text-muted-foreground">{etiket}</dt>
      <dd className="text-sm break-words">{deger || "—"}</dd>
    </div>
  );
}
