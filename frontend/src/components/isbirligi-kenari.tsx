import Link from "next/link";

import { YanKutu } from "@/components/genc-paneli";
import { IletisimSatiri } from "@/components/panel";
import { KUTU } from "@/components/ui/yuzey";
import type { IsbirligiDetayi } from "@/lib/api";
import { type Taraf, ilerlemeMetni } from "@/lib/takip";
import { cn } from "@/lib/utils";

/**
 * İş birliği sayfasının yan sütunu (docs/kararlar.md F21): kimin kiminle çalıştığı,
 * ilerleme, ihtiyacın özü ve kabulle açılan iletişim. Plan ve adımlar sağda, işin
 * kendisi; bağlam solda ve hep görünür. İki tarafa aynı sayfa olduğu için hitapsız.
 */
export function IsbirligiKenari({
  detay,
  taraf,
  karsiTaraf,
  listeYolu,
  listeEtiketi,
}: {
  detay: IsbirligiDetayi;
  taraf: Taraf | null;
  karsiTaraf: Taraf | null;
  /** Sayfanın altındaki sakin dönüş: kullanıcının iş birlikleri listesi (GİRVAK'ta panel). */
  listeYolu: string;
  listeEtiketi: string;
}) {
  const { tamamlanan, toplam } = detay.ilerleme;
  const cizgi = detay.durum === "aktif" || detay.durum === "tamamlandi";

  return (
    <aside
      aria-label="İş birliği özeti"
      className="order-2 flex flex-col gap-4 lg:sticky lg:top-24 lg:order-1"
    >
      <section className={cn(KUTU, "flex flex-col gap-4 px-5 py-5")}>
        <dl className="flex flex-col gap-3">
          <div className="flex flex-col gap-0.5">
            <dt className="text-xs text-muted-foreground">İhtiyacı açan</dt>
            <dd className="font-heading text-base font-semibold text-ana">
              {detay.kurum_adi}
            </dd>
          </div>
          <div className="flex flex-col gap-0.5">
            <dt className="text-xs text-muted-foreground">Aday</dt>
            <dd className="font-heading text-base font-semibold text-ana">
              {detay.aday_adi}
              {detay.rol_alani ? (
                <span className="block font-sans text-sm font-normal text-muted-foreground">
                  {detay.rol_alani}
                </span>
              ) : null}
            </dd>
          </div>
        </dl>

        <div className="flex flex-col gap-2 border-t border-kenar pt-4">
          <span className="text-sm text-muted-foreground">
            {ilerlemeMetni(detay.durum, detay.ilerleme)}
          </span>
          {cizgi && toplam > 0 ? (
            <div
              role="progressbar"
              aria-valuemin={0}
              aria-valuemax={toplam}
              aria-valuenow={tamamlanan}
              aria-label="Tamamlanan adımlar"
              className="h-1.5 overflow-hidden rounded-full bg-kenar"
            >
              <div
                className="h-full rounded-full bg-baglanti"
                style={{ width: `${(tamamlanan / toplam) * 100}%` }}
              />
            </div>
          ) : null}
        </div>

        <p className="border-l-[3px] border-vurgu pl-3 text-sm leading-relaxed text-pretty">
          {detay.problem_tanimi}
          {detay.basari_kriteri ? (
            <span className="mt-1.5 block text-muted-foreground">
              Başarı ölçütü: {detay.basari_kriteri}
            </span>
          ) : null}
        </p>
      </section>

      {detay.iletisim && karsiTaraf ? (
        <YanKutu baslik="İletişim">
          <IletisimSatiri
            iletisim={detay.iletisim}
            karsiTaraf={karsiTaraf}
            taslak={{
              adayTuru: detay.aday_turu,
              // Aday tarafı yazıyorsa gönderen aday, alıcı ilanı açan firma.
              gonderenAdi: taraf === "genc" ? detay.aday_adi : detay.kurum_adi,
              aliciAdi: taraf === "genc" ? detay.kurum_adi : detay.aday_adi,
              problem: detay.problem_tanimi,
              basariKriteri: detay.basari_kriteri,
              calisma: detay.calisma_basligi,
            }}
          />
        </YanKutu>
      ) : null}

      <Link
        href={listeYolu}
        className="w-fit px-1 text-sm text-baglanti underline underline-offset-4"
      >
        {listeEtiketi}
      </Link>
    </aside>
  );
}
