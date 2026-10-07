import { SeviyeCubugu } from "@/components/seviye-cubugu";
import { DIKKAT } from "@/components/ui/yuzey";
import type { GuvenSkoru, SomutCiktiYaniti } from "@/lib/api";
import {
  GOSTERGE_BASLIKLARI,
  baslikGosterimi,
  gostergeDoluMu,
} from "@/lib/guven-gostergesi";
import { kartDosyasiAdresi } from "@/lib/api";
import { dosyaParcalari, kanitAdresi, kanitLinkleri } from "@/lib/kanit";
import { IS_TURU_ETIKETLERI, etiketle } from "@/lib/sabitler";
import { type Uygunluk, uygunlukRozeti } from "@/lib/uygunluk";
import { cn } from "@/lib/utils";

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

/**
 * Dört başlık ayrı ayrı gösterilir, tek bir "güven puanı"na indirgenmez:
 * agent-specs.md § 4'ün açık kararı. Her başlık bir karo: ad ve kelime üstte,
 * üç parçalı çubuk altta. Zayıf başlık (Eksik, Zayıf) amber zeminle kendini
 * gösterir; değerlendirilmemiş başlık "—" (0 değil).
 */
export function GostergeKarolari({ skor }: { skor: GuvenSkoru }) {
  return (
    <dl className="grid grid-cols-2 gap-2 sm:grid-cols-4">
      {GOSTERGE_BASLIKLARI.map((bilesen) => {
        const { metin, sozlu, seviye } = baslikGosterimi(
          bilesen.ad,
          skor[bilesen.alan],
        );
        const zayif = seviye !== null && seviye <= 1;
        return (
          <div
            key={bilesen.ad}
            className={cn(
              "flex flex-col gap-2 rounded-lg px-3 py-2.5",
              zayif ? DIKKAT : "border border-transparent bg-zemin",
            )}
          >
            <div className="flex items-baseline justify-between gap-2">
              <dt className="text-xs text-muted-foreground">{bilesen.ad}</dt>
              <dd
                aria-hidden="true"
                className={cn(
                  "text-xs font-semibold",
                  seviye === null ? "text-muted-foreground" : "text-metin",
                )}
              >
                {metin}
              </dd>
            </div>
            <SeviyeCubugu
              seviye={seviye}
              etiket={`${bilesen.ad}: ${sozlu}`}
              genis
            />
          </div>
        );
      })}
    </dl>
  );
}

/** Belge kartının eteğinde gösterge (firmanın gördüğü salt okunur çalışma). */
export function GuvenGostergesi({ skor }: { skor: GuvenSkoru }) {
  return (
    <div className="border-t border-kenar px-4 py-3">
      <GostergeKarolari skor={skor} />
    </div>
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
      %{Math.round(skor * 100)} uyum
    </span>
  );
}

/** Yapay zekâ "kısmen uygun" dediyse rozet; diğer kararlarda hiçbir şey çizmez. */
export function KismenUygunRozeti({
  uygunluk,
}: {
  uygunluk: Uygunluk | undefined;
}) {
  const metin = uygunlukRozeti(uygunluk);
  if (!metin) return null;
  return (
    <span className="rounded-sm border border-baglanti px-2.5 py-1 text-xs text-baglanti">
      {metin}
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
    <div className="flex flex-col gap-1.5 sm:flex-row sm:items-baseline sm:gap-3">
      <span className="w-24 shrink-0 text-xs text-muted-foreground">
        {etiket}
      </span>
      <ul className="flex flex-wrap gap-1.5">
        {degerler.map((deger) => (
          <li
            key={deger}
            className="rounded-full border border-kenar px-2.5 py-0.5 text-sm text-metin"
          >
            {deger}
          </li>
        ))}
      </ul>
    </div>
  );
}

/**
 * Somut çıktı + (varsa) rubriği. Rubrik yoksa "doğrulanmamış" denir.
 * Hem gencin kendi kart sayfası hem firmanın öneri ekranı kullanır; sahibe
 * özgü metinler isteğe bağlı özelliklerle açılır, varsayılan firma görünümü.
 */
export function CiktiOzeti({
  cikti,
  eylem,
  sahibiBakiyor = false,
  referansVar = false,
  kartId,
}: {
  cikti: SomutCiktiYaniti;
  /** Dosya indirme adresi kart üzerinden alınır (firma yalnızca açılan dosyayı). */
  kartId?: string;
  eylem?: React.ReactNode;
  /** Genç kendi kartına bakıyor: "Payın" (firma gencin payını okur: "Payı"). */
  sahibiBakiyor?: boolean;
  /**
   * Çalışmanın referans isteği var. Referans da kanıt sayılır
   * (backend: core/is_kalemi.kanit_bekliyor); linki yok diye "Kanıt
   * eklenmemiş" denmez. Referans listesi yalnızca sahibin sayfasında.
   */
  referansVar?: boolean;
}) {
  const linkler = kanitLinkleri(cikti.kanitlar);
  const dosyalar = dosyaParcalari(cikti.kanitlar);
  return (
    <div className="flex flex-col gap-2 rounded-sm border border-kenar">
      <div className="flex flex-col gap-1 px-4 py-3">
        <div className="flex items-start justify-between gap-3">
          <p className="font-medium">
            {cikti.baslik}
            {cikti.is_turu ? (
              <span className="ml-2 text-xs font-normal text-muted-foreground">
                {etiketle(IS_TURU_ETIKETLERI, cikti.is_turu)}
              </span>
            ) : null}
          </p>
          {eylem ? <div className="shrink-0">{eylem}</div> : null}
        </div>
        {cikti.aciklama ? (
          <p className="text-sm text-pretty text-muted-foreground">
            {cikti.aciklama}
          </p>
        ) : null}
        {cikti.olculebilir_sonuc ? (
          <p className="text-sm text-pretty">
            Sonuç: {cikti.olculebilir_sonuc}
          </p>
        ) : null}
        {cikti.kendi_rolu ? (
          <p className="text-sm text-pretty">
            {sahibiBakiyor ? "Payın" : "Payı"}: {cikti.kendi_rolu}
          </p>
        ) : null}
        {dosyalar.length > 0 ? (
          <ul className="flex flex-col gap-1">
            {dosyalar.map((parca) =>
              parca.dosya_adi && kartId ? (
                <li key={parca.id}>
                  <button
                    type="button"
                    onClick={() =>
                      void kartDosyasiAdresi(kartId, parca.id)
                        .then(({ adres }) => window.location.assign(adres))
                        .catch(() => undefined)
                    }
                    className="w-fit text-left text-sm break-all text-baglanti underline underline-offset-4"
                  >
                    {parca.dosya_adi}
                  </button>
                </li>
              ) : (
                <li key={parca.id} className="text-sm text-muted-foreground">
                  {parca.tur === "gorsel"
                    ? "Yüklenmiş bir görsel"
                    : "Yüklenmiş bir belge"}
                  ; içeriği paylaşılmadı, değerlendirme sonucu aşağıda.
                </li>
              ),
            )}
          </ul>
        ) : null}
        {linkler.length > 0 ? (
          <ul className="flex flex-col gap-1">
            {linkler.map((parca) => (
              <li key={parca.id}>
                <a
                  href={kanitAdresi(parca.url)}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="w-fit text-sm break-all text-baglanti underline underline-offset-4"
                >
                  {parca.url}
                </a>
              </li>
            ))}
          </ul>
        ) : dosyalar.length > 0 ? null : (
          <p className="text-sm text-muted-foreground">
            {referansVar
              ? "Kanıt linki yok; referansın aşağıda."
              : "Kanıt eklenmemiş."}
          </p>
        )}
      </div>

      {cikti.guven_skoru && gostergeDoluMu(cikti.guven_skoru) ? (
        <GuvenGostergesi skor={cikti.guven_skoru} />
      ) : (
        <p className="border-t border-kenar px-4 py-3 text-sm text-muted-foreground">
          Bu çalışma henüz değerlendirilmedi. Değerlendirilmemiş olmak kartı
          elemez; yalnızca güven göstergesi boş kalır.
        </p>
      )}
    </div>
  );
}

/**
 * Tamamlanmış pilot rozeti (docs/takip.md § 6): iki tarafın her adımı
 * onayladığı iş birliği. Bağlantı rengi — "bağlantı anı". Sıfırsa çizilmez.
 */
export function PilotRozeti({ sayi }: { sayi: number }) {
  if (sayi < 1) return null;
  return (
    <span className="rounded-sm border border-baglanti px-2.5 py-1 text-xs text-baglanti">
      {sayi} tamamlanan iş birliği
    </span>
  );
}
