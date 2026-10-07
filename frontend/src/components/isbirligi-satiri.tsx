import Link from "next/link";

import { DurumEtiketi, IletisimSatiri, tarihYaz } from "@/components/panel";
import { Button } from "@/components/ui/button";
import type { IsbirligiOzeti } from "@/lib/api";
import { ISBIRLIGI_DURUM_ETIKETLERI, ilerlemeMetni } from "@/lib/takip";

/**
 * Bir iş birliği satırı: genç ve firma aynı satırı görür, karşı taraf
 * `tarafim`'dan (ilanı açtıysak aday, aday tarafındaysak ilanı açan firma;
 * docs/takip.md, Ek). İş birliklerim sayfası ve firma paneli kullanır.
 */
export function IsbirligiSatiri({ isbirligi }: { isbirligi: IsbirligiOzeti }) {
  const adayTarafi = isbirligi.tarafim === "genc";
  const karsiAd = adayTarafi ? isbirligi.kurum_adi : isbirligi.aday_adi;
  const benimAd = adayTarafi ? isbirligi.aday_adi : isbirligi.kurum_adi;
  const { tamamlanan, toplam } = isbirligi.ilerleme;
  const cizgi =
    isbirligi.durum === "aktif" || isbirligi.durum === "tamamlandi";

  return (
    <li className="flex flex-col gap-3 rounded-md border border-kenar bg-card px-5 py-4">
      <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-1">
        <div className="flex min-w-0 flex-col gap-0.5">
          <span className="font-heading text-lg font-semibold text-ana">
            {karsiAd}
          </span>
          <span className="text-xs text-muted-foreground">
            {[
              adayTarafi ? null : (isbirligi.rol_alani ?? "İş birliği ortağı"),
              `${tarihYaz(isbirligi.baslangic_tarihi)} tarihinde başladı`,
            ]
              .filter(Boolean)
              .join(" · ")}
          </span>
        </div>
        <DurumEtiketi
          metin={
            ISBIRLIGI_DURUM_ETIKETLERI[isbirligi.durum] ?? isbirligi.durum
          }
          baglanti={isbirligi.durum === "tamamlandi"}
        />
      </div>

      <p className="line-clamp-2 text-sm text-pretty">
        {isbirligi.problem_tanimi}
      </p>

      {cizgi && toplam > 0 ? (
        <div className="flex items-center gap-3">
          <div
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={toplam}
            aria-valuenow={tamamlanan}
            aria-label="Tamamlanan adımlar"
            className="h-1.5 flex-1 overflow-hidden rounded-full bg-kenar"
          >
            <div
              className="h-full rounded-full bg-baglanti"
              style={{ width: `${(tamamlanan / toplam) * 100}%` }}
            />
          </div>
          <span className="shrink-0 text-xs text-muted-foreground">
            {ilerlemeMetni(isbirligi.durum, isbirligi.ilerleme)}
          </span>
        </div>
      ) : (
        <span className="text-xs text-muted-foreground">
          {ilerlemeMetni(isbirligi.durum, isbirligi.ilerleme)}
        </span>
      )}

      <div className="flex flex-wrap items-end justify-between gap-3 border-t border-kenar pt-3">
        <IletisimSatiri
          iletisim={isbirligi.iletisim}
          karsiTaraf={adayTarafi ? "kurum" : "genc"}
          taslak={{
            adayTuru: isbirligi.aday_turu,
            gonderenAdi: benimAd,
            aliciAdi: karsiAd,
            problem: isbirligi.problem_tanimi,
            basariKriteri: isbirligi.basari_kriteri,
            calisma: isbirligi.calisma_basligi,
          }}
        />
        <Button asChild size="sm" className="ml-auto">
          <Link href={`/isbirligi/${isbirligi.isbirligi_id}`}>
            {isbirligi.durum === "plan_bekliyor"
              ? "Planı gör"
              : "İş birliğini aç"}
          </Link>
        </Button>
      </div>
    </li>
  );
}
