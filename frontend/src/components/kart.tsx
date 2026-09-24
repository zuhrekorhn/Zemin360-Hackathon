import type { GuvenSkoru, SomutCiktiYaniti } from "@/lib/api";

/**
 * Kart ve gerekçe görünümünün paylaşılan parçaları.
 *
 * Ana sayfadaki örnek blok da bunları kullanıyor (statik veriyle, backend
 * kapalıyken de çizilsin diye) — böylece vitrindeki görünümle gerçek
 * ekranlardaki görünüm ayrışmıyor.
 *
 * Görsel dil (docs/design-language.md): hairline çizgi, az yuvarlak köşe,
 * resmi belge hissi.
 */

/** Rubriğin dört bileşeni (docs/agent-specs.md § 4). */
const BILESENLER = [
  { ad: "Kanıt orijinalliği", alan: "kanit_orijinalligi" },
  { ad: "Ölçülebilir sonuç", alan: "sonuc_olculebilirligi" },
  { ad: "Rol netliği", alan: "rol_netligi" },
  { ad: "Üçüncü taraf onayı", alan: "ucuncu_taraf_onayi" },
] as const;

/**
 * Dört bileşen ayrı ayrı gösterilir, tek bir "güven puanı"na indirgenmez —
 * agent-specs.md § 4'ün açık kararı.
 */
export function GuvenGostergesi({ skor }: { skor: GuvenSkoru }) {
  return (
    <dl className="grid grid-cols-2 gap-px border-t border-kenar bg-kenar sm:grid-cols-4">
      {BILESENLER.map((bilesen) => (
        <div key={bilesen.ad} className="bg-card px-5 py-3 sm:px-4">
          <dt className="text-xs text-muted-foreground">{bilesen.ad}</dt>
          <dd className="font-mono text-sm text-ana">{skor[bilesen.alan]}/3</dd>
        </div>
      ))}
    </dl>
  );
}

/** Hairline çerçeveli belge kartı: başlık şeridi + gövde + isteğe bağlı etek. */
export function BelgeKarti({
  baslik,
  altbaslik,
  rozet,
  children,
  etek,
}: {
  baslik: string;
  altbaslik?: string | null;
  rozet?: React.ReactNode;
  children?: React.ReactNode;
  etek?: React.ReactNode;
}) {
  return (
    <article className="rounded-sm border border-kenar bg-card">
      <div className="flex items-start justify-between gap-4 border-b border-kenar px-5 py-4">
        <div className="min-w-0">
          <h3 className="font-heading text-base font-semibold text-ana">
            {baslik}
          </h3>
          {altbaslik ? (
            <p className="mt-1 text-sm text-pretty text-muted-foreground">
              {altbaslik}
            </p>
          ) : null}
        </div>
        {rozet ? <div className="shrink-0">{rozet}</div> : null}
      </div>

      {children ? (
        <div className="flex flex-col gap-3 px-5 py-4 text-sm">{children}</div>
      ) : null}

      {etek}
    </article>
  );
}

/**
 * Eşleşme skoru. Yüzdeye çevriliyor çünkü 0.6839 kimseye bir şey anlatmıyor;
 * ondalık gösterilmiyor ki olduğundan hassas görünmesin.
 */
export function SkorRozeti({ skor }: { skor: number }) {
  return (
    <span className="rounded-sm border border-kenar px-2.5 py-1 font-mono text-sm text-ana">
      %{Math.round(skor * 100)}
      <span className="sr-only"> eşleşme skoru</span>
    </span>
  );
}

/** Kartın etiket dizileri (araçlar, sektörler). Boşsa hiç çizilmez. */
export function EtiketSatiri({
  etiket,
  degerler,
}: {
  etiket: string;
  degerler: string[];
}) {
  if (degerler.length === 0) return null;
  return (
    <p className="text-sm">
      <span className="text-muted-foreground">{etiket}: </span>
      {degerler.join(", ")}
    </p>
  );
}

/** Somut çıktı + (varsa) rubriği. Rubrik yoksa "doğrulanmamış" denir. */
export function CiktiOzeti({
  cikti,
  eylem,
}: {
  cikti: SomutCiktiYaniti;
  eylem?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-2 rounded-sm border border-kenar">
      <div className="flex flex-col gap-1 px-4 py-3">
        <div className="flex items-start justify-between gap-3">
          <p className="font-medium">{cikti.baslik}</p>
          {eylem ? <div className="shrink-0">{eylem}</div> : null}
        </div>
        {cikti.aciklama ? (
          <p className="text-sm text-pretty text-muted-foreground">
            {cikti.aciklama}
          </p>
        ) : null}
        {cikti.kanit_linki ? (
          <a
            href={
              /^https?:\/\//i.test(cikti.kanit_linki)
                ? cikti.kanit_linki
                : `https://${cikti.kanit_linki}`
            }
            target="_blank"
            rel="noreferrer noopener"
            className="w-fit text-sm break-all text-baglanti underline underline-offset-4"
          >
            {cikti.kanit_linki}
          </a>
        ) : (
          <p className="text-sm text-muted-foreground">Kanıt eklenmemiş.</p>
        )}
      </div>

      {cikti.guven_skoru ? (
        <GuvenGostergesi skor={cikti.guven_skoru} />
      ) : (
        <p className="border-t border-kenar px-4 py-3 text-sm text-muted-foreground">
          Bu çıktı henüz doğrulanmadı. Doğrulanmamış olmak kartı eler değil,
          sadece güven göstergesi boş kalır.
        </p>
      )}
    </div>
  );
}
