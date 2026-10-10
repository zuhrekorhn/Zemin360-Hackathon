import Link from "next/link";

import { DurumEtiketi, tarihYaz } from "@/components/panel";
import { Button } from "@/components/ui/button";
import { KUTU } from "@/components/ui/yuzey";
import type { GirvakIsbirligi } from "@/lib/api";
import { ISBIRLIGI_DURUM_ETIKETLERI, ilerlemeMetni } from "@/lib/takip";
import { cn } from "@/lib/utils";

/**
 * GİRVAK'ın iş birliği satırı: iki taraf, ilerleme, ayrıntıya geçiş. Firma ve
 * genç panelindeki satırla aynı yüzey ve ilerleme çizgisi; farkı iletişim
 * bilgisinin hiç olmaması (GİRVAK e-posta görmez).
 */
export function GirvakIsbirligiSatiri({
  isbirligi,
}: {
  isbirligi: GirvakIsbirligi;
}) {
  const { tamamlanan, toplam, geciken } = isbirligi.ilerleme;
  const cizgi = isbirligi.durum === "aktif" || isbirligi.durum === "tamamlandi";
  const adayAdi =
    isbirligi.aday_turu === "genc" && isbirligi.rol_alani
      ? `${isbirligi.aday_adi} (${isbirligi.rol_alani})`
      : isbirligi.aday_adi;

  return (
    <li className={cn(KUTU, "flex flex-col gap-3 px-6 py-5")}>
      <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-1">
        <div className="flex min-w-0 flex-col gap-0.5">
          <span className="font-heading text-lg font-semibold text-ana">
            {isbirligi.kurum_adi} · {isbirligi.aday_adi}
          </span>
          <span className="text-xs text-muted-foreground">
            {[
              isbirligi.aday_turu === "firma"
                ? "Firma–firma"
                : `Genç–firma · ${adayAdi}`,
              isbirligi.baslangic_tarihi
                ? `${tarihYaz(isbirligi.baslangic_tarihi)} tarihinde başladı`
                : null,
            ]
              .filter(Boolean)
              .join(" · ")}
          </span>
        </div>
        <span className="flex flex-wrap items-center gap-2">
          {geciken > 0 && isbirligi.durum === "aktif" ? (
            <DurumEtiketi metin={`${geciken} gecikmiş adım`} />
          ) : null}
          <DurumEtiketi
            metin={
              ISBIRLIGI_DURUM_ETIKETLERI[isbirligi.durum] ?? isbirligi.durum
            }
            baglanti={isbirligi.durum === "tamamlandi"}
          />
        </span>
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

      <div className="flex justify-end border-t border-kenar pt-3">
        <Button asChild size="sm">
          <Link href={`/isbirligi/${isbirligi.isbirligi_id}`}>
            İş birliğini aç
          </Link>
        </Button>
      </div>
    </li>
  );
}
