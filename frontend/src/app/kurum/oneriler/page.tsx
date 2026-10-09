"use client";

import { ChevronDown } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useRef, useState } from "react";

import { Sayfa, SayfaBasligi, SayfaDurumu } from "@/components/sayfa";
import { DogrulanmisFirma } from "@/components/dogrulanmis-firma";
import { OnayAlani } from "@/components/onay-alani";
import { GirisKapisi, useGirisliHesap } from "@/components/giris-kapisi";
import { BolumBasligi, YanKutu } from "@/components/genc-paneli";
import {
  BelgeKarti,
  CiktiOzeti,
  EtiketSatiri,
  KismenUygunRozeti,
  PilotRozeti,
  UyumRozeti,
} from "@/components/kart";
import { DurumEtiketi, IletisimSatiri } from "@/components/panel";
import { HataKutusu } from "@/components/sohbet";
import { Button } from "@/components/ui/button";
import { KUTU } from "@/components/ui/yuzey";
import {
  type IhtiyacKartiOzeti,
  type Oneri,
  type SomutCiktiYaniti,
  type Oneriler,
  eslestirmeCalistir,
  eslestirmeOnerileri,
  ilgileniyorum,
  simdilikDegil,
} from "@/lib/api";
import { type Hata, hatayaCevir } from "@/lib/hata";
import { isbirligiTuruEtiketi } from "@/lib/firma-karti";
import { FIRMA_TURLERI } from "@/lib/firma-profil";
import {
  NEDEN_UYGUN,
  firmaDurumEtiketi,
  firmaEylemleri,
  gerekceBekleniyor,
  ilgiGosterenleriAyir,
  onerininAdayAdi,
} from "@/lib/ilgi";
import { arananEtiketi, ilanKapali } from "@/lib/ilan";
import {
  DENEYIM_ETIKETLERI,
  IS_TURU_ETIKETLERI,
  etiketle,
} from "@/lib/sabitler";
import { cn } from "@/lib/utils";
import { YENILEME_ARALIGI_MS, YENILEME_EN_FAZLA } from "@/lib/yenileme";

/**
 * Eşleştirme önerileri — kurum tarafı (docs/agent-specs.md § 3).
 *
 * Kurum "ilgileniyorum" der, genç kabul ya da red eder; iş birliği ve
 * e-postalar yalnızca kabulle açılır (docs/kimlik-ve-dongu.md § 5).
 *
 * Uyum ve gerekçe birlikte gösteriliyor — matching-algorithm.md § 6'nın
 * kararı: kuruma "şu yüzden" denmeden bir isim listesi sunulmuyor. Uyum
 * kelimeyle (UyumRozeti); skor yalnızca sıralar.
 *
 * Genç akışı (docs/api-contracts.md): ilgi gösteren adaylar ayrı
 * bölümde, uyum sırası değişmeden; firma onlara "İlgileniyorum" (karşılıklı
 * ilgi, iş birliği açılır) ya da "Şimdilik değil" der. Durum etiketleri
 * docs/icerik-rehberi.md § 5.9 (lib/ilgi.ts).
 */

export default function OnerilerSayfasi() {
  return (
    <GirisKapisi roller={["kurum"]} genislik="genis">
      <Suspense fallback={<SayfaDurumu genislik="genis" />}>
        <OnerilerIcerigi />
      </Suspense>
    </GirisKapisi>
  );
}

function OnerilerIcerigi() {
  const hesap = useGirisliHesap();
  const kurumId = hesap.kurum_id;
  const kartVar = hesap.ihtiyac_kartlari.length > 0;
  // Kurum panelinden `?ihtiyac=<id>` ile gelinir; yoksa en son ihtiyaç kartı.
  // Yan sütundaki "diğer ihtiyaçlar" aynı sayfada adresi değiştirir; liste yeniden okunur.
  const ihtiyacKartiId = useSearchParams().get("ihtiyac");
  const sonOkunan = useRef<string | null | undefined>(undefined);
  const [veri, setVeri] = useState<Oneriler | null>(null);
  const [yukleniyor, setYukleniyor] = useState(kartVar);
  const [hata, setHata] = useState<Hata | null>(null);

  /**
   * `tazele` false: hesaplanmış listeyi okur (sayfa açılışı).
   * `tazele` true: pipeline'ı yeniden çalıştırır — skorlar güncellenir,
   * eksik gerekçeler üretilir, eskiyen öneriler düşer. Dil modeli çağrısı
   * burada olabilir, o yüzden açılışta değil yalnızca istenince.
   */
  const onerileriGetir = useCallback(
    async (kart: string | null, tazele = false, sessiz = false) => {
      if (!kurumId) return;
      // `sessiz`: arka plan yenilemesi; yükleniyor ya da hata göstermez.
      if (!sessiz) {
        setHata(null);
        setYukleniyor(true);
      }
      try {
        setVeri(
          await (tazele
            ? eslestirmeCalistir(kart)
            : eslestirmeOnerileri(kurumId, kart)),
        );
      } catch (sebep) {
        if (!sessiz) setHata(hatayaCevir(sebep));
      } finally {
        if (!sessiz) setYukleniyor(false);
      }
    },
    [kurumId],
  );

  useEffect(() => {
    // Aynı adres için bir kez oku (StrictMode efekti iki kez çalıştırır).
    if (!kartVar || sonOkunan.current === ihtiyacKartiId) return;
    sonOkunan.current = ihtiyacKartiId;
    void onerileriGetir(ihtiyacKartiId);
  }, [kartVar, ihtiyacKartiId, onerileriGetir]);

  // İlan düzenlenince gerekçeler arka planda yeniden yazılır; bu sürede liste
  // "açıklama henüz hazır değil" kalmasın: hazır olana dek sessizce yenilenir.
  const gerekceSuruyor = veri !== null && gerekceBekleniyor(veri.oneriler);
  useEffect(() => {
    if (!gerekceSuruyor) return;
    let deneme = 0;
    const zamanlayici = setInterval(() => {
      if (document.hidden) return;
      deneme += 1;
      if (deneme > YENILEME_EN_FAZLA) {
        clearInterval(zamanlayici);
        return;
      }
      void onerileriGetir(ihtiyacKartiId, false, true);
    }, YENILEME_ARALIGI_MS);
    return () => clearInterval(zamanlayici);
  }, [gerekceSuruyor, ihtiyacKartiId, onerileriGetir]);

  async function durumuYaz(
    oneri: Oneri,
    istek: (eslesmeId: string) => ReturnType<typeof ilgileniyorum>,
  ) {
    setHata(null);
    try {
      const yanit = await istek(oneri.eslesme_id);
      setVeri((onceki) =>
        onceki
          ? {
              ...onceki,
              oneriler: onceki.oneriler.map((kayit) =>
                kayit.eslesme_id === oneri.eslesme_id
                  ? {
                      ...kayit,
                      durum: yanit.durum,
                      iletisim: yanit.iletisim,
                      isbirligi_id: yanit.isbirligi_id,
                      genc_ilgi_gosterdi: yanit.durum === "genc_ilgilendi",
                    }
                  : kayit,
              ),
            }
          : onceki,
      );
    } catch (sebep) {
      setHata(hatayaCevir(sebep));
    }
  }

  const ilgilendigimiSoyle = (oneri: Oneri) => durumuYaz(oneri, ilgileniyorum);

  // Onay kartın içinde sorulur (SimdilikDegilDugmesi, rehber § 5.6).
  function simdilikDegilDe(oneri: Oneri) {
    void durumuYaz(oneri, simdilikDegil);
  }

  const gosterilenKart = hesap.ihtiyac_kartlari.find(
    (kart) => kart.id === (veri?.ihtiyac_karti_id ?? ihtiyacKartiId),
  );
  // Ortak ilanının adayları firmalar (docs/kararlar.md F5).
  const ortak = gosterilenKart?.aranan === "firma";
  const digerIhtiyaclar = hesap.ihtiyac_kartlari.filter(
    (kart) => !ilanKapali(kart) && kart.id !== gosterilenKart?.id,
  );

  return (
    <Sayfa genislik="genis">
      <div className="grid items-start gap-8 lg:grid-cols-[19rem_minmax(0,1fr)]">
        <aside
          aria-label="İhtiyacınız"
          className="order-2 flex flex-col gap-4 lg:sticky lg:top-24 lg:order-1"
        >
          {gosterilenKart ? (
            <IhtiyacOzeti
              kart={gosterilenKart}
              yukleniyor={yukleniyor}
              onYenidenHesapla={() =>
                void onerileriGetir(
                  veri?.ihtiyac_karti_id ?? ihtiyacKartiId,
                  true,
                )
              }
            />
          ) : null}
          {digerIhtiyaclar.length > 0 ? (
            <DigerIhtiyaclar kartlar={digerIhtiyaclar} />
          ) : null}
        </aside>

        <div className="order-1 flex min-w-0 flex-col gap-6 lg:order-2">
          <SayfaBasligi
            baslik="Uygun adaylar"
            aciklama={
              ortak
                ? "İhtiyacınıza uyan firmalar, uyumuyla ve neden uygun olduklarıyla birlikte. Karar sizin."
                : "İhtiyacınıza uyan gençler, uyumuyla ve neden uygun olduklarıyla birlikte. Karar sizin."
            }
          >
            {gosterilenKart ? (
              // Geniş ekranda yan sütunda; dar ekranda yan sütun altta kalır, bağlam burada.
              <p className="line-clamp-2 border-l-[3px] border-vurgu pl-3 text-sm leading-relaxed text-pretty lg:hidden">
                {gosterilenKart.problem_tanimi}
              </p>
            ) : null}
          </SayfaBasligi>

          {hata ? (
            <HataKutusu
              hata={hata}
              tekrarDene={() => void onerileriGetir(ihtiyacKartiId)}
            />
          ) : null}

          {yukleniyor ? (
            <p
              role="status"
              className="flex items-center gap-2 text-sm text-muted-foreground"
            >
              <span
                aria-hidden="true"
                className="size-2 rounded-full bg-baglanti motion-safe:animate-pulse"
              />
              Adaylar hazırlanıyor…
            </p>
          ) : null}

          {!kartVar ? <KurumYok /> : null}

          {!yukleniyor && veri ? (
            <OneriListesi
              veri={veri}
              ilan={
                gosterilenKart
                  ? {
                      firmaAdi: hesap.ad ?? "",
                      problem: gosterilenKart.problem_tanimi,
                      basariKriteri: gosterilenKart.basari_kriteri ?? null,
                    }
                  : null
              }
              ortak={ortak}
              onIlgileniyorum={ilgilendigimiSoyle}
              onSimdilikDegil={simdilikDegilDe}
            />
          ) : null}
        </div>
      </div>
    </Sayfa>
  );
}

/** Yan sütun: hangi ihtiyacın adaylarına baktığınız, yeniden hesaplama ve düzenleme. */
function IhtiyacOzeti({
  kart,
  yukleniyor,
  onYenidenHesapla,
}: {
  kart: IhtiyacKartiOzeti;
  yukleniyor: boolean;
  onYenidenHesapla: () => void;
}) {
  const aranan = arananEtiketi(kart.aranan);
  return (
    <section className={cn(KUTU, "flex flex-col gap-4 px-5 py-5")}>
      <div className="flex items-center justify-between gap-2">
        <h2 className="font-heading text-base font-semibold text-ana">
          İhtiyacınız
        </h2>
        {aranan ? <DurumEtiketi metin={aranan} /> : null}
      </div>
      <p className="border-l-[3px] border-vurgu pl-3 text-[15px] leading-relaxed text-pretty">
        {kart.problem_tanimi}
      </p>
      {kart.basari_kriteri ? (
        <p className="text-sm leading-relaxed text-pretty text-muted-foreground">
          <span className="font-medium text-metin">Başarı ölçütü: </span>
          {kart.basari_kriteri}
        </p>
      ) : null}
      <div className="flex flex-col gap-3 border-t border-kenar pt-4">
        <Button
          type="button"
          variant="outline"
          size="lg"
          disabled={yukleniyor}
          onClick={onYenidenHesapla}
          className="w-full"
        >
          Yeniden hesapla
        </Button>
        <Link
          href={`/kurum?duzenle=${kart.id}`}
          className="w-fit text-sm text-baglanti underline underline-offset-4"
        >
          İhtiyacı düzenle
        </Link>
      </div>
    </section>
  );
}

/** Başka bir ihtiyacın adaylarına geçiş (panele dönmeden). */
function DigerIhtiyaclar({ kartlar }: { kartlar: IhtiyacKartiOzeti[] }) {
  return (
    <YanKutu baslik="Diğer ihtiyaçlarınız">
      <ul className="-mx-2 flex flex-col">
        {kartlar.map((kart) => (
          <li key={kart.id}>
            <Link
              href={`/kurum/oneriler?ihtiyac=${kart.id}`}
              className="flex flex-col gap-1 rounded-md px-2 py-2 hover:bg-muted"
            >
              <span className="line-clamp-2 text-sm text-pretty">
                {kart.problem_tanimi}
              </span>
              {arananEtiketi(kart.aranan) ? (
                <span className="text-[13px] text-muted-foreground">
                  {arananEtiketi(kart.aranan)}
                </span>
              ) : null}
            </Link>
          </li>
        ))}
      </ul>
    </YanKutu>
  );
}

/**
 * Adayın çalışmaları: varsayılan kapalı, yalnızca başlık ve tür. Ayrıntılar
 * (sonuç, pay, kanıt, güven göstergesi) istenince açılır; böylece karar düğmesi
 * iki iç içe kutunun altında kalmaz.
 */
function CalismaBolumu({
  ciktilar,
  kartId,
}: {
  ciktilar: SomutCiktiYaniti[];
  kartId: string;
}) {
  const [acik, setAcik] = useState(false);
  if (ciktilar.length === 0) {
    return (
      <section className="flex flex-col gap-2">
        <AltBaslik>Çalışmaları</AltBaslik>
        <p className="text-sm text-muted-foreground">
          Bu karta henüz çalışma eklenmemiş.
        </p>
      </section>
    );
  }
  return (
    <section className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-3">
        <AltBaslik>Çalışmaları ({ciktilar.length})</AltBaslik>
        <button
          type="button"
          aria-expanded={acik}
          onClick={() => setAcik((onceki) => !onceki)}
          className="inline-flex items-center gap-1 rounded-md text-sm text-baglanti outline-none hover:underline focus-visible:ring-3 focus-visible:ring-ring/50"
        >
          {acik ? "Ayrıntıları gizle" : "Ayrıntıları göster"}
          <ChevronDown
            aria-hidden="true"
            className={cn("size-4 transition-transform", acik && "rotate-180")}
          />
        </button>
      </div>
      {acik ? (
        ciktilar.map((cikti) => (
          <CiktiOzeti key={cikti.id} cikti={cikti} kartId={kartId} />
        ))
      ) : (
        <ul className="flex flex-col gap-1.5">
          {ciktilar.map((cikti) => (
            <li
              key={cikti.id}
              className="flex items-baseline justify-between gap-3 rounded-lg bg-muted/60 px-3.5 py-2.5 text-sm"
            >
              <span className="font-medium text-pretty">{cikti.baslik}</span>
              {cikti.is_turu ? (
                <span className="shrink-0 text-xs text-muted-foreground">
                  {etiketle(IS_TURU_ETIKETLERI, cikti.is_turu)}
                </span>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

/** Boş durum: bir sonraki adımı söyleyen kesikli kutu (genç "Fırsatlar"ıyla aynı). */
function BosKutu({
  baslik,
  children,
  eylem,
}: {
  baslik: string;
  children?: React.ReactNode;
  eylem?: React.ReactNode;
}) {
  return (
    <div
      className={cn(
        KUTU,
        "flex flex-col items-start gap-3 border-dashed px-6 py-7 shadow-none",
      )}
    >
      <p className="font-heading text-lg font-semibold text-ana">{baslik}</p>
      {children ? (
        <div className="flex max-w-prose flex-col gap-2 text-sm text-pretty text-muted-foreground">
          {children}
        </div>
      ) : null}
      {eylem}
    </div>
  );
}

function KurumYok() {
  return (
    <BosKutu
      baslik="Henüz bir ihtiyaç tanımlamadınız"
      eylem={
        <Button asChild size="lg">
          <Link href="/tanimlama">İhtiyacınızı tanımlayın</Link>
        </Button>
      }
    >
      <p>
        Kısa bir sohbetle ihtiyacınızı netleştirin, size uygun adayları
        gösterelim.
      </p>
    </BosKutu>
  );
}

/** E-posta taslağı için ilanın bağlamı (e-posta adresi içermez). */
type IlanBaglami = {
  firmaAdi: string;
  problem: string;
  basariKriteri: string | null;
};

function OneriListesi({
  veri,
  ilan,
  ortak,
  onIlgileniyorum,
  onSimdilikDegil,
}: {
  veri: Oneriler;
  ilan: IlanBaglami | null;
  ortak: boolean;
  onIlgileniyorum: (oneri: Oneri) => void;
  onSimdilikDegil: (oneri: Oneri) => void;
}) {
  const { ilgiGosterenler, digerleri } = ilgiGosterenleriAyir(veri.oneriler);
  if (veri.oneriler.length === 0 && ortak) {
    return (
      <BosKutu baslik="Şu an ihtiyacınıza yeterince uyan bir firma yok">
        <p>
          Firmalar kartlarını oluşturdukça yeni adaylar çıkabilir.
          İhtiyacınızdaki problemi ve başarı kriterini netleştirmek de yardımcı
          olur.
        </p>
      </BosKutu>
    );
  }
  if (veri.oneriler.length === 0) {
    return (
      <BosKutu baslik="Şu an ihtiyacınıza yeterince uyan bir aday yok">
        <p>
          Yalnızca yeterince uyan adayları gösteriyoruz; zayıf bir öneri iki
          tarafın da vaktini alır.
        </p>
        <p>
          Yeni gençler katıldıkça ya da ihtiyacınızı netleştirdikçe yeniden
          hesaplayın.
        </p>
      </BosKutu>
    );
  }

  const kartlar = (liste: Oneri[]) =>
    liste.map((oneri) => (
      <li key={oneri.eslesme_id}>
        <OneriKarti
          oneri={oneri}
          ilan={ilan}
          onIlgileniyorum={() => onIlgileniyorum(oneri)}
          onSimdilikDegil={() => onSimdilikDegil(oneri)}
        />
      </li>
    ));

  return (
    <div className="flex flex-col gap-8">
      {veri.az_sonuc_uyarisi ? (
        <p className="rounded-xl bg-muted px-5 py-3 text-sm text-pretty">
          Havuz henüz küçük: {veri.oneriler.length} aday çıktı. Az sayıda aday,
          kötü aday demek değil.
        </p>
      ) : null}

      {ilgiGosterenler.length > 0 ? (
        <section
          aria-labelledby="ilgi-gosterenler"
          className="flex flex-col gap-4"
        >
          <BolumBasligi
            id="ilgi-gosterenler"
            baslik="İlgi gösterenler"
            sayi={ilgiGosterenler.length}
            aciklama="Bu adaylar ihtiyacınızla ilgilendiklerini bildirdi. Siz de ilgilenirseniz iletişim bilgileriniz karşılıklı paylaşılır ve iş birliği başlar."
          />
          <ul className="flex flex-col gap-4">{kartlar(ilgiGosterenler)}</ul>
        </section>
      ) : null}

      {digerleri.length > 0 ? (
        <section aria-labelledby="adaylar" className="flex flex-col gap-4">
          {ilgiGosterenler.length > 0 ? (
            <BolumBasligi
              id="adaylar"
              baslik="Adaylar"
              sayi={digerleri.length}
            />
          ) : null}
          <ul className="flex flex-col gap-4">{kartlar(digerleri)}</ul>
        </section>
      ) : null}
    </div>
  );
}

/** "Neden uygun?": gencin Fırsatlar ekranındaki gerekçe kutusuyla aynı. */
function NedenUygunKutusu({ metin }: { metin: string | null }) {
  return (
    <section className="flex flex-col gap-1 rounded-lg border-l-[3px] border-baglanti bg-baglanti/[0.06] px-4 py-3">
      <h4 className="font-heading text-sm font-semibold text-ana">
        {NEDEN_UYGUN}
      </h4>
      {metin ? (
        <p className="text-sm leading-relaxed text-pretty">{metin}</p>
      ) : (
        <p className="text-sm text-pretty text-muted-foreground">
          Bu aday için açıklama henüz hazır değil. Uyum ve sıralama bundan
          etkilenmiyor; “Yeniden hesapla” ile tekrar denenir.
        </p>
      )}
    </section>
  );
}

function AltBaslik({ children }: { children: React.ReactNode }) {
  return (
    <h4 className="font-heading text-sm font-semibold text-ana">{children}</h4>
  );
}

function OneriKarti({
  oneri,
  ilan,
  onIlgileniyorum,
  onSimdilikDegil,
}: {
  oneri: Oneri;
  ilan: IlanBaglami | null;
  onIlgileniyorum: () => void;
  onSimdilikDegil: () => void;
}) {
  if (oneri.firma_karti)
    return (
      <FirmaAdayiKarti
        oneri={oneri}
        ilan={ilan}
        onIlgileniyorum={onIlgileniyorum}
        onSimdilikDegil={onSimdilikDegil}
      />
    );
  const kart = oneri.yetenek_karti;
  if (!kart) return null;
  const ilgiGosterdi = oneri.durum === "genc_ilgilendi";

  return (
    <BelgeKarti
      vurgulu={ilgiGosterdi}
      baslik={kart.rol_alani}
      altbaslik={`${kart.genc_adi} · Deneyim: ${etiketle(DENEYIM_ETIKETLERI, kart.deneyim_seviyesi)}`}
      rozet={
        <span className="flex flex-wrap items-center justify-end gap-2">
          {ilgiGosterdi ? (
            <DurumEtiketi metin={firmaDurumEtiketi(oneri.durum)} baglanti />
          ) : null}
          <PilotRozeti sayi={kart.tamamlanan_pilot} />
          <UyumRozeti skor={oneri.skor} />
        </span>
      }
      etek={
        <OneriEtegi
          oneri={oneri}
          karsi="genc"
          onIlgileniyorum={onIlgileniyorum}
          onSimdilikDegil={onSimdilikDegil}
        >
          {oneri.iletisim ? (
            <IletisimSatiri
              iletisim={oneri.iletisim}
              karsiTaraf="genc"
              taslak={
                ilan
                  ? {
                      adayTuru: "genc",
                      gonderenAdi: ilan.firmaAdi,
                      aliciAdi: kart.genc_adi,
                      problem: ilan.problem,
                      basariKriteri: ilan.basariKriteri,
                      calisma: kart.somut_ciktilar[0]?.baslik,
                    }
                  : undefined
              }
            />
          ) : null}
        </OneriEtegi>
      }
    >
      <NedenUygunKutusu metin={oneri.gerekce_metni} />

      <EtiketSatiri etiket="Araçlar" degerler={kart.araclar_teknolojiler} />
      <EtiketSatiri etiket="Sektör ilgisi" degerler={kart.sektor_ilgi_alani} />

      <CalismaBolumu ciktilar={kart.somut_ciktilar} kartId={kart.id} />
    </BelgeKarti>
  );
}

/**
 * Ortak ilanında önerilen firma (docs/kararlar.md F8, F16-17).
 * Eylemler genç adayındakiyle aynı kurala bağlı (`firmaEylemleri`); metinler
 * karşı tarafı "firma" diye anar.
 */
function FirmaAdayiKarti({
  oneri,
  ilan,
  onIlgileniyorum,
  onSimdilikDegil,
}: {
  oneri: Oneri;
  ilan: IlanBaglami | null;
  onIlgileniyorum: () => void;
  onSimdilikDegil: () => void;
}) {
  const ilgiGosterdi = oneri.durum === "genc_ilgilendi";
  const firma = oneri.firma_karti;
  if (!firma) return null;
  const tur = FIRMA_TURLERI.find((t) => t.deger === firma.tur)?.etiket;
  return (
    <BelgeKarti
      vurgulu={ilgiGosterdi}
      baslik={firma.firma_adi}
      altbaslik={[tur, firma.sektor, firma.sehir].filter(Boolean).join(" · ")}
      rozet={
        <span className="flex flex-wrap items-center justify-end gap-2">
          <DogrulanmisFirma dogrulandi={firma.dogrulandi} />
          {ilgiGosterdi ? (
            <DurumEtiketi metin={firmaDurumEtiketi(oneri.durum)} baglanti />
          ) : null}
          {firma.tamamlanan_isbirligi > 0 ? (
            <DurumEtiketi
              metin={`${firma.tamamlanan_isbirligi} tamamlanan iş birliği`}
              baglanti
            />
          ) : null}
          <KismenUygunRozeti uygunluk={oneri.uygunluk} />
          <UyumRozeti skor={oneri.skor} />
        </span>
      }
      etek={
        <OneriEtegi
          oneri={oneri}
          karsi="firma"
          onIlgileniyorum={onIlgileniyorum}
          onSimdilikDegil={onSimdilikDegil}
        >
          {oneri.iletisim ? (
            <IletisimSatiri
              iletisim={oneri.iletisim}
              karsiTaraf="genc"
              taslak={
                ilan
                  ? {
                      adayTuru: "firma",
                      gonderenAdi: ilan.firmaAdi,
                      aliciAdi: firma.firma_adi,
                      problem: ilan.problem,
                      basariKriteri: ilan.basariKriteri,
                    }
                  : undefined
              }
            />
          ) : null}
        </OneriEtegi>
      }
    >
      <NedenUygunKutusu metin={oneri.gerekce_metni} />

      <section className="flex flex-col gap-1.5">
        <AltBaslik>Ne yapıyor?</AltBaslik>
        <p className="text-sm text-pretty">{firma.ne_yapiyoruz}</p>
      </section>
      <EtiketSatiri etiket="Yetkinlikler" degerler={firma.yetkinlikler} />
      {firma.onceki_isler ? (
        <section className="flex flex-col gap-1.5">
          <AltBaslik>Önceki işler</AltBaslik>
          <p className="text-sm text-pretty">{firma.onceki_isler}</p>
        </section>
      ) : null}
      {firma.isbirligi_turleri.length > 0 ? (
        <EtiketSatiri
          etiket="İş birliği türleri"
          degerler={firma.isbirligi_turleri.map(isbirligiTuruEtiketi)}
        />
      ) : null}
    </BelgeKarti>
  );
}

/** Kartın etek şeridi: tek birincil eylem ya da durum cümlesi, kabulden sonra iletişim. */
function OneriEtegi({
  oneri,
  karsi,
  onIlgileniyorum,
  onSimdilikDegil,
  children,
}: {
  oneri: Oneri;
  /** Karşı tarafın türü: metinler gence ya da firmaya göre yazılır. */
  karsi: "genc" | "firma";
  onIlgileniyorum: () => void;
  onSimdilikDegil: () => void;
  children?: React.ReactNode;
}) {
  const eylemler = firmaEylemleri(oneri.durum);
  const ilgiGosterdi = oneri.durum === "genc_ilgilendi";
  const karsiAd = karsi === "genc" ? "Gence" : "Firmaya";
  const durumCumlesi: Record<string, string> = {
    ilgileniliyor:
      karsi === "genc"
        ? "Gencin yanıtı bekleniyor; kabul ederse iletişim bilgileri açılır."
        : "Firmanın yanıtı bekleniyor; kabul ederse iletişim bilgileri açılır.",
    kabul_edildi: "İletişim bilgileri aşağıda.",
    reddedildi: "Bu eşleşme kapandı.",
    kapandi: "Bu aday için süreç kapandı.",
  };

  return (
    <div className="flex flex-col gap-3 border-t border-kenar px-6 py-4">
      {ilgiGosterdi ? (
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          <Button type="button" size="lg" onClick={onIlgileniyorum}>
            İlgileniyorum
          </Button>
          <SimdilikDegilDugmesi
            adayAdi={onerininAdayAdi(oneri)}
            onOnayla={onSimdilikDegil}
          />
          <span className="text-xs text-pretty text-muted-foreground">
            İlgilenirseniz iletişim bilgileriniz paylaşılır ve iş birliği
            başlar.
          </span>
        </div>
      ) : eylemler.ilgileniyorum ? (
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          <Button type="button" size="lg" onClick={onIlgileniyorum}>
            İlgileniyorum
          </Button>
          <span className="text-xs text-pretty text-muted-foreground">
            {karsiAd} bildirilir; kabul ederse iş birliği açılır ve e-postalar
            paylaşılır.
          </span>
        </div>
      ) : (
        <p className="text-sm text-pretty">
          <span className="font-medium">{firmaDurumEtiketi(oneri.durum)}.</span>{" "}
          {durumCumlesi[oneri.durum] ?? ""}
          {oneri.isbirligi_id ? (
            <>
              {" "}
              <Link
                href={`/isbirligi/${oneri.isbirligi_id}`}
                className="text-baglanti underline underline-offset-4"
              >
                İş birliğine gidin
              </Link>
            </>
          ) : null}
        </p>
      )}
      {children}
    </div>
  );
}

/**
 * "Şimdilik değil": onay kartın içinde (rehber § 5.6); adaya nedeni yazılmaz.
 */
function SimdilikDegilDugmesi({
  adayAdi,
  onOnayla,
}: {
  adayAdi: string;
  onOnayla: () => void;
}) {
  const [acik, setAcik] = useState(false);
  if (acik) {
    return (
      <OnayAlani
        soru={`${adayAdi} için “Şimdilik değil” denilsin mi? Adaya bu fırsatın kapandığı bildirilir; neden yazılmaz.`}
        onayEtiketi="Şimdilik değil"
        onOnayla={() => {
          setAcik(false);
          onOnayla();
        }}
        onVazgec={() => setAcik(false)}
      />
    );
  }
  return (
    <Button
      type="button"
      size="lg"
      variant="outline"
      onClick={() => setAcik(true)}
    >
      Şimdilik değil
    </Button>
  );
}
