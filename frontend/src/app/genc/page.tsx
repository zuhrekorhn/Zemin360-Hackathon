"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { EpostaDogrulamaBandi } from "@/components/eposta-dogrulama-bandi";
import { FirsatKarti } from "@/components/firsatlar";
import {
  BolumBasligi,
  EksikAdimlar,
  GelenIlgiKarti,
  IsbirligiBekleyeni,
  KabulEdilenIlgi,
  KimlikOzeti,
  SurecListesi,
} from "@/components/genc-paneli";
import { GirisKapisi, useGirisliHesap } from "@/components/giris-kapisi";
import {
  KartDurumuKutusu,
  SiradakiAdimBandi,
} from "@/components/kart-yan-sutunu";
import { Sayfa } from "@/components/sayfa";
import { HataKutusu } from "@/components/sohbet";
import { Button } from "@/components/ui/button";
import { KUTU } from "@/components/ui/yuzey";
import {
  type BanaGelenIlgi,
  type GencEslesmesi,
  type IsbirligiOzeti,
  banaGelenler,
  eslesmeyiKabulEt,
  eslesmeyiReddet,
  firsatlarim,
  gencIlgi,
  ilgilerim,
  ilgiyiGeriCek,
  isbirliklerim,
  kalemDurumu,
  yetenekKartiGetir,
} from "@/lib/api";
import { type Eksik, eksikler, kartinSiradakiAdimi } from "@/lib/calisma";
import {
  bekleyenSayisi,
  bekleyenler,
  eksikAdimlar,
  ozetCumlesi,
  surecler,
} from "@/lib/genc-paneli";
import { type Hata, hatayaCevir } from "@/lib/hata";
import { useOturum } from "@/lib/oturum";
import { cn } from "@/lib/utils";

/**
 * Gencin ana sayfası, "Fırsatlar" (docs/kimlik-ve-dongu.md § 7, docs/kararlar.md G18).
 *
 * Kart sayfasıyla aynı iskelet: solda kim olduğun (kimlik, kartın durumu,
 * süreçlerin), sağda ne yapacağın. Sağ sütun "şimdi ne yapmalıyım" sırasıyla:
 * önce yanıt bekleyen işler (firmanın ilgisi, plan onayı, geciken adım); yoksa
 * kartın tek "Sıradaki adım"ı; sonra fırsatlar. Boş bölüm çizilmez.
 *
 * Kabulden önce firma gencin e-postasını görmez; kabul edince iki tarafın
 * e-postası açılır ve iş birliği başlar (§ 5). Gencin ilgisi açık onayla gider.
 */

export default function GencPaneli() {
  return (
    <GirisKapisi roller={["genc"]} genislik="genis">
      <GencPaneliIcerigi />
    </GirisKapisi>
  );
}

type CalismaEksikleri = { id: string; baslik: string; eksikler: Eksik[] };

function GencPaneliIcerigi() {
  const hesap = useGirisliHesap();
  const { tazele } = useOturum();
  const router = useRouter();

  const [gelenler, setGelenler] = useState<BanaGelenIlgi[] | null>(null);
  const [isbirlikleri, setIsbirlikleri] = useState<IsbirligiOzeti[]>([]);
  const [firsatlar, setFirsatlar] = useState<GencEslesmesi[] | null>(null);
  const [benimIlgilerim, setBenimIlgilerim] = useState<GencEslesmesi[]>([]);
  const [calismalar, setCalismalar] = useState<CalismaEksikleri[]>([]);
  // Bu oturumda kabul edilen ilgiler: iletişim ve iş birliği bağlantısı
  // bir sonraki yenilemeye kadar aynı yerde görünsün.
  const [yeniKabuller, setYeniKabuller] = useState<BanaGelenIlgi[]>([]);
  const [hata, setHata] = useState<Hata | null>(null);
  const okundu = useRef(false);
  // Gencin tek kartı (G17); Keşif'i tamamlamadıysa null.
  const kart = hesap.yetenek_karti;
  const kartId = kart?.id ?? null;

  const firsatlariOku = useCallback(async () => {
    const [yeni, benim] = await Promise.all([firsatlarim(), ilgilerim()]);
    setFirsatlar(yeni);
    setBenimIlgilerim(benim);
  }, []);

  /** Kartın çalışmaları ve eksikleri: "Kartının durumu" ve "Sıradaki adım". */
  const kartiOku = useCallback(async (kimlik: string) => {
    const tam = await yetenekKartiGetir(kimlik);
    const durumlar = await Promise.all(
      tam.somut_ciktilar.map((cikti) => kalemDurumu(cikti.id)),
    );
    setCalismalar(
      tam.somut_ciktilar.map((cikti, i) => ({
        id: cikti.id,
        baslik: cikti.baslik,
        eksikler: eksikler({
          kanitSayisi: durumlar[i].kanitlar.length,
          referansSayisi: durumlar[i].referanslar.length,
          skor: durumlar[i].guven_skoru,
        }),
      })),
    );
  }, []);

  const oku = useCallback(async () => {
    setHata(null);
    try {
      const [gelen, acik] = await Promise.all([
        banaGelenler(),
        isbirliklerim(),
        firsatlariOku(),
        kartId ? kartiOku(kartId) : Promise.resolve(),
      ]);
      setGelenler(gelen);
      setIsbirlikleri(acik);
    } catch (sebep) {
      setHata(hatayaCevir(sebep));
    }
  }, [kartId, firsatlariOku, kartiOku]);

  useEffect(() => {
    if (okundu.current) return;
    okundu.current = true;
    void oku();
  }, [oku]);

  async function calistir(is: () => Promise<void>) {
    setHata(null);
    try {
      await is();
    } catch (sebep) {
      setHata(hatayaCevir(sebep));
    }
  }

  const ilgiGoster = (firsat: GencEslesmesi) =>
    calistir(async () => {
      await gencIlgi(firsat.eslesme_id);
      await firsatlariOku();
    });

  const ilgiyiCek = (eslesmeId: string) =>
    calistir(async () => {
      await ilgiyiGeriCek(eslesmeId);
      await firsatlariOku();
    });

  const yanitla = (ilgi: BanaGelenIlgi, kabul: boolean) =>
    calistir(async () => {
      const yanit = kabul
        ? await eslesmeyiKabulEt(ilgi.eslesme_id)
        : await eslesmeyiReddet(ilgi.eslesme_id);
      const guncel = {
        ...ilgi,
        durum: yanit.durum,
        isbirligi_id: yanit.isbirligi_id,
        iletisim: yanit.iletisim,
      };
      setGelenler((onceki) =>
        (onceki ?? []).map((k) =>
          k.eslesme_id === ilgi.eslesme_id ? guncel : k,
        ),
      );
      if (kabul) {
        setYeniKabuller((onceki) => [...onceki, guncel]);
        setIsbirlikleri(await isbirliklerim());
      }
      // Rozet ve kart /me'den okunuyor.
      void tazele();
    });

  const bekleyen = bekleyenler(gelenler ?? [], isbirlikleri);
  const bekleyenAdet = bekleyenSayisi(bekleyen);
  const kartAdimi = kartinSiradakiAdimi(calismalar);
  const guclendirmeyeGit = (ciktiId: string) => {
    if (kartId) router.push(`/kart/${kartId}#guclendir-${ciktiId}`);
  };
  const ad = hesap.ad ?? hesap.email;

  return (
    <Sayfa genislik="genis">
      {hata ? <HataKutusu hata={hata} tekrarDene={() => void oku()} /> : null}

      <div className="grid items-start gap-8 lg:grid-cols-[19rem_minmax(0,1fr)]">
        <aside
          aria-label="Özet"
          className="order-2 flex flex-col gap-4 lg:sticky lg:top-24 lg:order-1"
        >
          <KimlikOzeti ad={ad} kart={kart} />
          <EksikAdimlar adimlar={eksikAdimlar(hesap)} />
          {kart ? (
            <KartDurumuKutusu
              calismalar={calismalar}
              onSec={guclendirmeyeGit}
            />
          ) : null}
          <div id="surecler" className="scroll-mt-24">
            <SurecListesi
              satirlar={surecler(benimIlgilerim, gelenler ?? [], isbirlikleri)}
              onGeriCek={ilgiyiCek}
            />
          </div>
        </aside>

        <div className="order-1 flex min-w-0 flex-col gap-8 lg:order-2">
          <header className="flex flex-col gap-1.5">
            <h1 className="font-heading text-3xl font-semibold text-balance text-ana sm:text-4xl">
              Merhaba, {ad.split(" ")[0]}
            </h1>
            <p className="text-[15px] text-pretty text-muted-foreground">
              {ozetCumlesi(
                bekleyenAdet,
                firsatlar?.length ?? null,
                Boolean(kart),
              )}
            </p>
          </header>

          <EpostaDogrulamaBandi hesap={hesap} />

          {!kart ? (
            <section className="flex flex-col items-start gap-4 rounded-xl bg-ana px-7 py-8 text-zemin">
              <p className="text-xs font-medium text-zemin/70">İlk adım</p>
              <h2 className="font-heading text-2xl font-semibold text-balance">
                Önce kartını oluşturalım
              </h2>
              <p className="max-w-prose text-[15px] leading-relaxed text-pretty text-zemin/85">
                Birkaç soruyla neler yaptığını anlat, kartını birlikte
                oluşturalım. Kartın hazır olunca firmaların ihtiyaçlarıyla
                eşleşir ve sana uygun fırsatlar burada görünür.
              </p>
              <Link
                href="/kesif"
                className="inline-flex h-10 items-center rounded-lg bg-vurgu px-4 text-sm font-semibold text-metin hover:bg-vurgu/90"
              >
                Kartını oluştur
              </Link>
            </section>
          ) : null}

          {bekleyenAdet + yeniKabuller.length > 0 ? (
            <section
              aria-labelledby="bekleyenler"
              className="flex flex-col gap-4"
            >
              <BolumBasligi
                id="bekleyenler"
                baslik="Seni bekleyenler"
                sayi={bekleyenAdet}
              />
              <ul className="flex flex-col gap-3">
                {yeniKabuller.map((ilgi) => (
                  <KabulEdilenIlgi
                    key={ilgi.eslesme_id}
                    ilgi={ilgi}
                    gencAdi={hesap.ad ?? ""}
                  />
                ))}
                {bekleyen.ilgiler.map((ilgi) => (
                  <GelenIlgiKarti
                    key={ilgi.eslesme_id}
                    ilgi={ilgi}
                    onYanit={(kabul) => yanitla(ilgi, kabul)}
                  />
                ))}
                {bekleyen.planlar.map((isbirligi) => (
                  <IsbirligiBekleyeni
                    key={isbirligi.isbirligi_id}
                    isbirligi={isbirligi}
                    tur="plan"
                  />
                ))}
                {bekleyen.gecikenler.map((isbirligi) => (
                  <IsbirligiBekleyeni
                    key={isbirligi.isbirligi_id}
                    isbirligi={isbirligi}
                    tur="gecikme"
                  />
                ))}
              </ul>
            </section>
          ) : kartAdimi ? (
            // Yanıt bekleyen iş yoksa en değerli adım kartı güçlendirmek.
            <SiradakiAdimBandi
              adim={kartAdimi}
              onAc={() => guclendirmeyeGit(kartAdimi.ciktiId)}
            />
          ) : null}

          {kart ? (
            <section
              id="firsatlar"
              aria-labelledby="firsatlar-baslik"
              className="flex scroll-mt-24 flex-col gap-4"
            >
              <BolumBasligi
                id="firsatlar-baslik"
                baslik="Sana uygun fırsatlar"
                sayi={firsatlar?.length}
                aciklama="Kartına ve çalışma tercihlerine uyan firma ihtiyaçları."
              />
              {firsatlar === null ? (
                <p className="text-sm text-muted-foreground" role="status">
                  Yükleniyor…
                </p>
              ) : firsatlar.length === 0 ? (
                <div
                  className={cn(
                    KUTU,
                    "flex flex-col items-start gap-3 border-dashed px-6 py-7 shadow-none",
                  )}
                >
                  <p className="font-heading text-lg font-semibold text-ana">
                    Şu an kartına uyan açık bir fırsat yok
                  </p>
                  <p className="max-w-prose text-sm text-pretty text-muted-foreground">
                    Firmalar yeni ihtiyaç açtıkça kartın kendiliğinden eşleşir
                    ve sana bildirim gelir. Çalışmalarını güçlendirmek
                    fırsatlarda öne çıkmanı sağlar.
                  </p>
                  <Button asChild variant="outline">
                    <Link href={`/kart/${kart.id}`}>Kartını güçlendir</Link>
                  </Button>
                </div>
              ) : (
                <ul className="flex flex-col gap-4">
                  {firsatlar.map((firsat) => (
                    <FirsatKarti
                      key={firsat.eslesme_id}
                      firsat={firsat}
                      onIlgi={() => ilgiGoster(firsat)}
                    />
                  ))}
                </ul>
              )}
            </section>
          ) : null}
        </div>
      </div>
    </Sayfa>
  );
}
