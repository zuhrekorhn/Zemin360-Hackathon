/**
 * Genç, kurum ve GİRVAK panellerinin ortak parçaları
 * (docs/kimlik-ve-dongu.md § 7).
 *
 * Görsel dil (docs/design-language.md): panel bir "belge"; bölümler hairline
 * çizgiyle ayrılır, aynı yuvarlak kart kalıbı her yere basılmaz. Boş bölüm
 * bir eyleme davet olarak yazılır — çıkmaz sokak yok.
 */

import Link from "next/link";

import { Button } from "@/components/ui/button";
import type { Iletisim } from "@/lib/api";
import {
  epostaTaslagi,
  taslakYonu,
  type EpostaBaglami,
} from "@/lib/eposta-taslagi";

export function PanelBolumu({
  id,
  baslik,
  aciklama,
  children,
}: {
  id?: string;
  baslik: string;
  aciklama?: string;
  children: React.ReactNode;
}) {
  return (
    <section
      id={id}
      aria-labelledby={id ? `${id}-baslik` : undefined}
      className="flex scroll-mt-20 flex-col gap-4 border-t border-kenar pt-8"
    >
      <div className="flex flex-col gap-1">
        <h2
          id={id ? `${id}-baslik` : undefined}
          className="font-heading text-xl font-semibold text-ana"
        >
          {baslik}
        </h2>
        {aciklama ? (
          <p className="text-sm text-pretty text-muted-foreground">
            {aciklama}
          </p>
        ) : null}
      </div>
      {children}
    </section>
  );
}

export function BosDurum({
  metin,
  eylem,
}: {
  metin: string;
  eylem?: { href: string; etiket: string };
}) {
  return (
    <div className="flex flex-col items-start gap-3 rounded-sm border border-dashed border-kenar px-5 py-4">
      <p className="text-sm text-pretty text-muted-foreground">{metin}</p>
      {eylem ? (
        <Button asChild size="lg">
          <Link href={eylem.href}>{eylem.etiket}</Link>
        </Button>
      ) : null}
    </div>
  );
}

/** Kabulle açılan e-postalar. `karsiTaraf`: gösterenin karşısındaki taraf önce. */
export function IletisimSatiri({
  iletisim,
  karsiTaraf,
  taslak,
}: {
  iletisim: Iletisim;
  karsiTaraf: "genc" | "kurum";
  /** Verilirse e-posta adresinin yanında hazır taslaklı "E-posta yaz" çıkar. */
  taslak?: EpostaBaglami;
}) {
  const satirlar =
    karsiTaraf === "kurum"
      ? [{ etiket: "Firmanın e-postası", eposta: iletisim.kurum_email }]
      : iletisim.aday_firma_email
        ? // Firma–firma: karşı taraf ortak firma (docs/takip.md (Ek)).
          [
            {
              etiket: "Ortak firmanın e-postası",
              eposta: iletisim.aday_firma_email,
            },
          ]
        : [{ etiket: "Gencin e-postası", eposta: iletisim.genc_email }];

  return (
    <dl className="grid gap-1 text-sm sm:grid-cols-[auto_1fr] sm:gap-x-4">
      {satirlar.map((satir) => (
        <div key={satir.etiket} className="contents">
          <dt className="text-muted-foreground">{satir.etiket}</dt>
          <dd className="flex flex-wrap items-center gap-x-3 gap-y-1">
            {satir.eposta ? (
              <>
                <a
                  className="break-all text-baglanti underline"
                  href={`mailto:${satir.eposta}`}
                >
                  {satir.eposta}
                </a>
                {taslak ? (
                  <Button asChild size="sm" variant="outline">
                    <a
                      href={
                        epostaTaslagi(
                          {
                            ...taslak,
                            yon: taslakYonu(karsiTaraf, taslak.adayTuru),
                          },
                          satir.eposta,
                        ).href
                      }
                    >
                      E-posta yaz
                    </a>
                  </Button>
                ) : null}
              </>
            ) : (
              <span className="text-muted-foreground">kayıtlı değil</span>
            )}
          </dd>
        </div>
      ))}
    </dl>
  );
}

/** Durum etiketi; hairline, küçük. Renk yalnızca "bağlantı" anında. */
export function DurumEtiketi({
  metin,
  baglanti = false,
}: {
  metin: string;
  baglanti?: boolean;
}) {
  return (
    <span
      className={
        baglanti
          ? "rounded-sm border border-baglanti px-2 py-0.5 text-xs text-baglanti"
          : "rounded-sm border border-kenar px-2 py-0.5 text-xs text-muted-foreground"
      }
    >
      {metin}
    </span>
  );
}

const TARIH = new Intl.DateTimeFormat("tr-TR", {
  day: "numeric",
  month: "long",
  year: "numeric",
});

const TARIH_SAAT = new Intl.DateTimeFormat("tr-TR", {
  day: "numeric",
  month: "long",
  hour: "2-digit",
  minute: "2-digit",
});

export function tarihYaz(tarih: string | null, saatli = false): string {
  if (!tarih) return "—";
  return (saatli ? TARIH_SAAT : TARIH).format(new Date(tarih));
}
