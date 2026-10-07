"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { EpostaDogrulamaBandi } from "@/components/eposta-dogrulama-bandi";
import { FirsatKarti } from "@/components/firsatlar";
import {
  BolumBasligi,
  EksikAdimlar,
  GelenIlgiKarti,
  IsbirligiBekleyeni,
  KabulEdilenIlgi,
  KartOzeti,
  SurecListesi,
} from "@/components/genc-paneli";
import { GirisKapisi, useGirisliHesap } from "@/components/giris-kapisi";
import { Sayfa, SayfaBasligi } from "@/components/sayfa";
import { HataKutusu } from "@/components/sohbet";
import { Button } from "@/components/ui/button";
import {
  type BanaGelenIlgi,
  type GencEslesmesi,
  type Guclendirme,
  type IsbirligiOzeti,
  banaGelenler,
  eslesmeyiKabulEt,
  eslesmeyiReddet,
  firsatlarim,
  gencIlgi,
  ilgilerim,
  ilgiyiGeriCek,
  isbirliklerim,
  kartGuclendir,
} from "@/lib/api";
import {
  bekleyenSayisi,
  bekleyenler,
  eksikAdimlar,
  ozetCumlesi,
  surecler,
} from "@/lib/genc-paneli";
import { type Hata, hatayaCevir } from "@/lib/hata";
import { useOturum } from "@/lib/oturum";

/**
 * Gencin ana sayfası (docs/kimlik-ve-dongu.md § 7): "şimdi ne yapmalıyım"
 * sırasıyla. Ana sütunda önce yanıt bekleyen işler (firmanın ilgisi, plan
 * onayı, geciken adım), sonra fırsatlar; yan sütunda kartın özeti,
 * tamamlanacaklar ve bütün süreçler tek listede. Boş bölüm çizilmez.
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

function GencPaneliIcerigi() {
  const hesap = useGirisliHesap();
  const { tazele } = useOturum();

  const [gelenler, setGelenler] = useState<BanaGelenIlgi[] | null>(null);
  const [isbirlikleri, setIsbirlikleri] = useState<IsbirligiOzeti[]>([]);
  const [firsatlar, setFirsatlar] = useState<GencEslesmesi[] | null>(null);
  const [benimIlgilerim, setBenimIlgilerim] = useState<GencEslesmesi[]>([]);
  const [guclendirmeler, setGuclendirmeler] = useState<Guclendirme[]>([]);
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

  const oku = useCallback(async () => {
    setHata(null);
    try {
      const [gelen, acik, guclendir] = await Promise.all([
        banaGelenler(),
        isbirliklerim(),
        kartId ? kartGuclendir(kartId) : Promise.resolve([]),
        firsatlariOku(),
      ]);
      setGelenler(gelen);
      setIsbirlikleri(acik);
      setGuclendirmeler(guclendir);
    } catch (sebep) {
      setHata(hatayaCevir(sebep));
    }
  }, [kartId, firsatlariOku]);

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
  const bekleyenToplam = bekleyenSayisi(bekleyen) + yeniKabuller.length;
  const eksikler = eksikAdimlar(hesap);
  const sureclerListesi = surecler(
    benimIlgilerim,
    gelenler ?? [],
    isbirlikleri,
  );

  return (
    <Sayfa genislik="genis">
      <SayfaBasligi
        baslik={<>Merhaba{hesap.ad ? `, ${hesap.ad.split(" ")[0]}` : ""}</>}
        aciklama={ozetCumlesi(
          bekleyenSayisi(bekleyen),
          firsatlar?.length ?? null,
          Boolean(kart),
        )}
      />

      {hata ? <HataKutusu hata={hata} tekrarDene={() => void oku()} /> : null}

      <div className="grid items-start gap-10 lg:grid-cols-[minmax(0,1fr)_19rem]">
        <div className="flex min-w-0 flex-col gap-10">
          <EpostaDogrulamaBandi hesap={hesap} />

          {!kart ? (
            <section className="flex flex-col items-start gap-4 rounded-md border border-kenar bg-card px-6 py-8">
              <h2 className="font-heading text-2xl font-semibold text-balance text-ana">
                Önce kartını oluşturalım
              </h2>
              <p className="max-w-prose text-[15px] leading-relaxed text-pretty text-muted-foreground">
                Birkaç soruyla neler yaptığını anlat, kartını birlikte
                oluşturalım. Kartın hazır olunca firmaların ihtiyaçlarıyla
                eşleşir ve sana uygun fırsatlar burada görünür.
              </p>
              <Button asChild size="lg">
                <Link href="/kesif">Kartını oluştur</Link>
              </Button>
            </section>
          ) : null}

          {bekleyenToplam > 0 ? (
            <section aria-labelledby="bekleyenler" className="flex flex-col gap-4">
              <BolumBasligi
                id="bekleyenler"
                baslik="Seni bekleyenler"
                sayi={bekleyenSayisi(bekleyen)}
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
              />
              {firsatlar === null ? (
                <p className="text-sm text-muted-foreground" role="status">
                  Yükleniyor…
                </p>
              ) : firsatlar.length === 0 ? (
                <div className="flex flex-col items-start gap-3 rounded-md border border-dashed border-kenar px-6 py-6">
                  <p className="text-[15px] font-medium text-ana">
                    Şu an kartına uyan açık bir fırsat yok.
                  </p>
                  <p className="text-sm text-pretty text-muted-foreground">
                    Firmalar yeni ihtiyaç açtıkça kartın kendiliğinden
                    eşleşir ve sana bildirim gelir. Çalışmalarına kanıt
                    eklemek, öne çıkmanı sağlar.
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

        <aside
          aria-label="Özet"
          className="flex flex-col gap-4 lg:sticky lg:top-24"
        >
          <EksikAdimlar adimlar={eksikler} />
          {kart ? (
            <KartOzeti kart={kart} guclendirmeler={guclendirmeler} />
          ) : null}
          <div id="surecler" className="scroll-mt-24">
            <SurecListesi
              satirlar={sureclerListesi}
              onGeriCek={ilgiyiCek}
            />
          </div>
        </aside>
      </div>
    </Sayfa>
  );
}
