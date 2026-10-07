"use client";

import Link from "next/link";
import { useState } from "react";

import { FirmaBasligi, KosulEtiketleri } from "@/components/firsatlar";
import { OnayAlani } from "@/components/onay-alani";
import { IletisimSatiri } from "@/components/panel";
import { Button } from "@/components/ui/button";
import type {
  BanaGelenIlgi,
  Guclendirme,
  IsbirligiOzeti,
  YetenekKartiOzeti,
} from "@/lib/api";
import type { EksikAdim, SurecSatiri } from "@/lib/genc-paneli";
import { DENEYIM_ETIKETLERI, etiketle } from "@/lib/sabitler";
import { cn } from "@/lib/utils";
import { kartYolu } from "@/lib/yonlendirme";

/**
 * Gencin ana sayfasının parçaları (app/genc/page.tsx). Kararlar
 * lib/genc-paneli.ts'de; burada yalnızca çizim.
 *
 * Görsel hiyerarşi: yanıt bekleyen iş vurgu renginde sol çizgiyle öne çıkar,
 * fırsat kartları sade, yan sütun küçük ve sakin (docs/design-language.md).
 */

/** Ana sütundaki bölüm başlığı; sayı varsa yanında. */
export function BolumBasligi({
  id,
  baslik,
  sayi,
  aciklama,
}: {
  id: string;
  baslik: string;
  sayi?: number;
  aciklama?: string;
}) {
  return (
    <div className="flex flex-col gap-1">
      <h2
        id={id}
        className="flex items-center gap-2.5 font-heading text-xl font-semibold text-ana"
      >
        {baslik}
        {sayi ? (
          <span className="rounded-full bg-ana px-2 py-0.5 font-sans text-xs font-medium text-zemin">
            {sayi}
          </span>
        ) : null}
      </h2>
      {aciklama ? (
        <p className="text-sm text-pretty text-muted-foreground">{aciklama}</p>
      ) : null}
    </div>
  );
}

/** "Seni bekleyenler"in satır kabı: vurgu renginde sol çizgi. */
function BekleyenKabi({ children }: { children: React.ReactNode }) {
  return (
    <li className="flex flex-col gap-3 rounded-md border border-kenar border-l-[3px] border-l-vurgu bg-card px-5 py-4">
      {children}
    </li>
  );
}

/** Firma kartla ilgileniyor: kabul ya da ret. */
export function GelenIlgiKarti({
  ilgi,
  onYanit,
}: {
  ilgi: BanaGelenIlgi;
  onYanit: (kabul: boolean) => Promise<void>;
}) {
  const [bekleniyor, setBekleniyor] = useState(false);
  const ihtiyac = ilgi.ihtiyac_karti;

  // Çift tıklamayı düğmede de kesiyoruz (backend tekrarı yan etkisiz
  // karşılıyor); hata olursa düğmeler yeniden açılır.
  async function yanitVer(kabul: boolean) {
    setBekleniyor(true);
    try {
      await onYanit(kabul);
    } finally {
      setBekleniyor(false);
    }
  }

  return (
    <BekleyenKabi>
      {/* Küçük metin vurgu renginde yazılmaz (kontrast); renk noktada. */}
      <p className="flex items-center gap-2 text-xs font-medium text-ana">
        <span aria-hidden="true" className="size-1.5 rounded-full bg-vurgu" />
        Firma seninle ilgileniyor
      </p>
      <FirmaBasligi ihtiyac={ihtiyac} />
      <KosulEtiketleri ihtiyac={ihtiyac} />
      <p className="text-sm leading-relaxed text-pretty">
        {ihtiyac.problem_tanimi}
      </p>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2 border-t border-kenar pt-3">
        <Button
          type="button"
          size="lg"
          disabled={bekleniyor}
          onClick={() => void yanitVer(true)}
        >
          Kabul et
        </Button>
        <Button
          type="button"
          size="lg"
          variant="ghost"
          disabled={bekleniyor}
          onClick={() => void yanitVer(false)}
        >
          Reddet
        </Button>
        <span className="text-xs text-pretty text-muted-foreground">
          Kabul edersen e-posta adresleriniz iki tarafa açılır ve iş birliği
          başlar.
        </span>
      </div>
    </BekleyenKabi>
  );
}

/** Kabul sonrası aynı kartta: iletişim ve iş birliğine geçiş. */
export function KabulEdilenIlgi({
  ilgi,
  gencAdi,
}: {
  ilgi: BanaGelenIlgi;
  gencAdi: string;
}) {
  return (
    <li className="flex flex-col gap-3 rounded-md border border-baglanti/40 bg-card px-5 py-4">
      <p className="text-xs font-medium text-baglanti">Karşılıklı ilgi</p>
      <FirmaBasligi ihtiyac={ilgi.ihtiyac_karti} />
      {ilgi.iletisim ? (
        <IletisimSatiri
          iletisim={ilgi.iletisim}
          karsiTaraf="kurum"
          taslak={{
            adayTuru: "genc",
            gonderenAdi: gencAdi,
            aliciAdi: ilgi.ihtiyac_karti.kurum.ad,
            problem: ilgi.ihtiyac_karti.problem_tanimi,
            basariKriteri: ilgi.ihtiyac_karti.basari_kriteri,
          }}
        />
      ) : null}
      {ilgi.isbirligi_id ? (
        <Button asChild size="lg" className="w-fit">
          <Link href={`/isbirligi/${ilgi.isbirligi_id}`}>İş birliğine git</Link>
        </Button>
      ) : null}
    </li>
  );
}

/** İş birliğinde gencin yapacağı bir şey: plan onayı ya da geciken adım. */
export function IsbirligiBekleyeni({
  isbirligi,
  tur,
}: {
  isbirligi: IsbirligiOzeti;
  tur: "plan" | "gecikme";
}) {
  return (
    <BekleyenKabi>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex min-w-0 flex-col gap-0.5">
          <span className="font-heading text-base font-semibold text-ana">
            {isbirligi.kurum_adi}
          </span>
          <span className="text-sm text-muted-foreground">
            {tur === "plan"
              ? "İş birliğinin planı onayını bekliyor."
              : `${isbirligi.ilerleme.geciken} adım gecikti; durumu birlikte güncelleyin.`}
          </span>
        </div>
        <Button asChild size="lg">
          <Link href={`/isbirligi/${isbirligi.isbirligi_id}`}>
            {tur === "plan" ? "Planı gör" : "İş birliğini aç"}
          </Link>
        </Button>
      </div>
    </BekleyenKabi>
  );
}

/** Yan sütunun kutusu: küçük başlık, sakin yüzey. */
export function YanKutu({
  baslik,
  children,
  className,
}: {
  baslik: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section
      className={cn(
        "flex flex-col gap-3 rounded-md border border-kenar bg-card px-5 py-4",
        className,
      )}
    >
      <h2 className="font-heading text-base font-semibold text-ana">
        {baslik}
      </h2>
      {children}
    </section>
  );
}

/** Kartın özeti ve en çok fark yaratacak güçlendirme önerileri. */
export function KartOzeti({
  kart,
  guclendirmeler,
}: {
  kart: YetenekKartiOzeti;
  guclendirmeler: Guclendirme[];
}) {
  const yol = kartYolu(kart);
  return (
    <YanKutu baslik="Kartın">
      <div className="flex flex-col gap-0.5">
        <span className="font-medium text-metin">{kart.rol_alani}</span>
        <span className="text-sm text-muted-foreground">
          Deneyim: {etiketle(DENEYIM_ETIKETLERI, kart.deneyim_seviyesi)}
        </span>
      </div>
      {kart.kanit_bekleyen || !kart.embedding_var ? (
        <ul className="flex flex-col gap-1 text-sm">
          {kart.kanit_bekleyen ? (
            <li className="flex items-center gap-2">
              <span aria-hidden="true" className="size-1.5 rounded-full bg-vurgu" />
              Kanıt bekleyen çalışman var
            </li>
          ) : null}
          {!kart.embedding_var ? (
            <li className="flex items-center gap-2">
              <span aria-hidden="true" className="size-1.5 rounded-full bg-vurgu" />
              Henüz fırsatlarla eşleştirilmedi
            </li>
          ) : null}
        </ul>
      ) : null}

      {guclendirmeler.length > 0 ? (
        <div className="flex flex-col gap-2 border-t border-kenar pt-3">
          <p className="text-sm font-medium text-ana">Kartını güçlendir</p>
          <ul className="flex flex-col gap-2.5">
            {guclendirmeler.slice(0, 2).map((satir) => (
              <li key={satir.somut_cikti_id} className="flex flex-col gap-0.5">
                <span className="text-sm font-medium">{satir.baslik}</span>
                <span className="text-xs text-pretty text-muted-foreground">
                  {satir.metin}
                </span>
                <Link
                  href={`${yol}#calisma-${satir.somut_cikti_id}`}
                  className="w-fit text-sm text-baglanti underline underline-offset-4"
                >
                  Kanıt ekle
                </Link>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <Button asChild variant="outline" className="mt-1 w-full">
        <Link href={yol}>Kartına git</Link>
      </Button>
    </YanKutu>
  );
}

/** Engellemeyen eksikler: her biri tek cümle ve tek bağlantı. */
export function EksikAdimlar({ adimlar }: { adimlar: EksikAdim[] }) {
  if (adimlar.length === 0) return null;
  return (
    <YanKutu baslik="Tamamlanacaklar" className="border-vurgu/50">
      <ul className="flex flex-col gap-3">
        {adimlar.map((adim) => (
          <li key={adim.anahtar} className="flex flex-col gap-1">
            <span className="text-sm text-pretty">{adim.metin}</span>
            <Link
              href={adim.href}
              className="w-fit text-sm font-medium text-baglanti underline underline-offset-4"
            >
              {adim.etiket}
            </Link>
          </li>
        ))}
      </ul>
    </YanKutu>
  );
}

/** Gencin bütün ilişkileri tek listede; her satırda tek durum etiketi. */
export function SurecListesi({
  satirlar,
  onGeriCek,
}: {
  satirlar: SurecSatiri[];
  onGeriCek: (eslesmeId: string) => Promise<void>;
}) {
  return (
    <YanKutu baslik="Süreçlerin">
      {satirlar.length === 0 ? (
        <p className="text-sm text-pretty text-muted-foreground">
          Bir fırsata ilgi gösterdiğinde ya da bir firma seninle ilgilendiğinde
          süreci buradan izlersin.
        </p>
      ) : (
        <ul className="-mx-2 flex flex-col">
          {satirlar.map((satir) => (
            <SurecSatiriGorunumu
              key={satir.anahtar}
              satir={satir}
              onGeriCek={onGeriCek}
            />
          ))}
        </ul>
      )}
      <Link
        href="/isbirliklerim"
        className="w-fit text-sm text-baglanti underline underline-offset-4"
      >
        Bütün iş birliklerin
      </Link>
    </YanKutu>
  );
}

function SurecSatiriGorunumu({
  satir,
  onGeriCek,
}: {
  satir: SurecSatiri;
  onGeriCek: (eslesmeId: string) => Promise<void>;
}) {
  const [onay, setOnay] = useState(false);
  const [bekleniyor, setBekleniyor] = useState(false);
  const etiket = (
    <span
      className={cn(
        "shrink-0 rounded-full px-2 py-0.5 text-xs",
        satir.baglanti
          ? "bg-baglanti/10 text-baglanti"
          : "bg-muted text-muted-foreground",
      )}
    >
      {satir.etiket}
    </span>
  );
  const ust = (
    <span className="flex items-center justify-between gap-3">
      <span className="min-w-0 truncate text-sm font-medium">{satir.firma}</span>
      {etiket}
    </span>
  );

  return (
    <li className="flex flex-col gap-1.5 rounded-md px-2 py-2">
      {satir.hedef ? (
        <Link href={satir.hedef} className="-m-2 rounded-md p-2 hover:bg-muted">
          {ust}
        </Link>
      ) : (
        ust
      )}
      {satir.geriCekilebilir && !onay ? (
        <button
          type="button"
          onClick={() => setOnay(true)}
          className="w-fit text-xs text-muted-foreground underline underline-offset-4 hover:text-metin"
        >
          İlgimi geri çek
        </button>
      ) : null}
      {satir.geriCekilebilir && onay ? (
        <OnayAlani
          soru={`${satir.firma} fırsatına gösterdiğin ilgi geri çekilsin mi? Fırsat yeniden listene döner.`}
          onayEtiketi="İlgimi geri çek"
          bekleniyor={bekleniyor}
          bekleniyorEtiketi="Geri çekiliyor…"
          onOnayla={() => {
            const ilgi = satir.geriCekilebilir;
            if (!ilgi) return;
            setBekleniyor(true);
            void onGeriCek(ilgi.eslesme_id).finally(() => {
              setBekleniyor(false);
              setOnay(false);
            });
          }}
          onVazgec={() => setOnay(false)}
        />
      ) : null}
    </li>
  );
}
