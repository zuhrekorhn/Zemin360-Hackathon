"use client";

import { ListeIskeleti } from "@/components/ui/iskelet";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { EpostaDogrulamaBandi } from "@/components/eposta-dogrulama-bandi";
import { FirmaFirsatlari } from "@/components/firma-firsatlari";
import {
  BolumBasligi,
  EksikAdimlar,
  IsbirligiBekleyeni,
} from "@/components/genc-paneli";
import { GirisKapisi, useGirisliHesap } from "@/components/giris-kapisi";
import { IlanDuzenlemePaneli } from "@/components/ilan-duzenleme-paneli";
import { IsbirligiSatiri } from "@/components/isbirligi-satiri";
import {
  AdayListesi,
  FirmaOzeti,
  IhtiyacKarti,
  KapaliBolum,
  IlgiGosterenKarti,
  YeniIhtiyacMenusu,
} from "@/components/kurum-paneli";
import { BosDurum } from "@/components/panel";
import { Sayfa } from "@/components/sayfa";
import { HataKutusu } from "@/components/sohbet";
import {
  type IsbirligiOzeti,
  type KurumOnerisi,
  isbirliklerim,
  onerilerim,
} from "@/lib/api";
import { type Hata, hatayaCevir } from "@/lib/hata";
import { KAPILAR, ilanKapali, ilanlariSirala } from "@/lib/ilan";
import {
  adaySatirlari,
  firmaEksikAdimlari,
  ihtiyacSayilari,
  kurumBekleyenSayisi,
  kurumBekleyenleri,
  kurumOzetCumlesi,
  tamamlananIsbirligiSayilari,
} from "@/lib/kurum-paneli";
import { useOturum } from "@/lib/oturum";
import { useSekmeBasligi } from "@/lib/sekme-basligi";
import { isbirligiSirasi } from "@/lib/takip";

/**
 * Firma paneli (docs/kimlik-ve-dongu.md § 7, docs/kararlar.md G18): gencin ana
 * sayfasıyla aynı iskelet. Solda kim olduğunuz (firma, tamamlanacaklar,
 * adaylarınız), sağda ne yapacağınız, "şimdi ne yapmalıyım" sırasıyla: önce
 * yanıtınızı bekleyen işler, sonra ihtiyaçlar, firma olarak gelen fırsatlar,
 * iş birlikleri. Boş bölüm çizilmez.
 *
 * Panel yalnızca okur; eşleştirmeyi çalıştırmak (dil modeli çağrısı olabilir)
 * öneriler sayfasının işi.
 */

export default function KurumPaneli() {
  return (
    <GirisKapisi roller={["kurum"]} genislik="genis">
      <KurumPaneliIcerigi />
    </GirisKapisi>
  );
}

function KurumPaneliIcerigi() {
  const hesap = useGirisliHesap();
  useSekmeBasligi("Panelim");
  const { tazele } = useOturum();
  const [oneriler, setOneriler] = useState<KurumOnerisi[] | null>(null);
  const [isbirlikleri, setIsbirlikleri] = useState<IsbirligiOzeti[] | null>(
    null,
  );
  // Kapatma onayı açık olan ihtiyaç; aynı anda biri.
  const [kapatilan, setKapatilan] = useState<string | null>(null);
  // Düzenleme paneli açık olan ihtiyaç; `?duzenle=<id>` ile de açılır.
  const [duzenlenen, setDuzenlenen] = useState<string | null>(null);
  const [hata, setHata] = useState<Hata | null>(null);
  const okundu = useRef(false);

  const oku = useCallback(async () => {
    setHata(null);
    try {
      const [gelen, acik] = await Promise.all([onerilerim(), isbirliklerim()]);
      setOneriler(gelen);
      setIsbirlikleri(acik);
    } catch (sebep) {
      setHata(hatayaCevir(sebep));
    }
  }, []);

  useEffect(() => {
    if (okundu.current) return;
    okundu.current = true;
    // Adres çubuğu yalnızca tarayıcıda; okuma bağlandıktan sonra.
    setDuzenlenen(new URLSearchParams(window.location.search).get("duzenle"));
    void oku();
  }, [oku]);

  const kartlar = ilanlariSirala(hesap.ihtiyac_kartlari);
  const acikKartlar = kartlar.filter((kart) => !ilanKapali(kart));
  const kapaliKartlar = kartlar.filter(ilanKapali);
  const acikIhtiyac = acikKartlar.length;
  const ilkAcikIhtiyac = acikKartlar[0] ?? null;
  const bekleyen = kurumBekleyenleri(oneriler ?? [], isbirlikleri ?? []);
  const bekleyenAdet = kurumBekleyenSayisi(bekleyen);
  const sayilar = ihtiyacSayilari(oneriler ?? []);
  const tamamlananlar = tamamlananIsbirligiSayilari(
    oneriler ?? [],
    isbirlikleri ?? [],
  );
  const adaySayisi = oneriler
    ? Object.values(sayilar).reduce((toplam, s) => toplam + s.aday, 0)
    : null;
  const ad = hesap.ad ?? "Firma paneli";

  const surenIsbirlikleri = isbirligiSirasi(
    (isbirlikleri ?? []).filter((i) => i.durum !== "tamamlandi"),
  );
  const biten = isbirligiSirasi(
    (isbirlikleri ?? []).filter((i) => i.durum === "tamamlandi"),
  );
  const isbirligiSatiri = (isbirligi: (typeof surenIsbirlikleri)[number]) => (
    <IsbirligiSatiri key={isbirligi.isbirligi_id} isbirligi={isbirligi} />
  );
  const ihtiyacSatiri = (kart: (typeof kartlar)[number]) => (
    <IhtiyacKarti
      key={kart.id}
      kart={kart}
      sayi={sayilar[kart.id]}
      tamamlanan={tamamlananlar[kart.id] ?? 0}
      kapatiliyor={kapatilan === kart.id}
      onDuzenle={() => setDuzenlenen(kart.id)}
      onKapatmaAc={() => setKapatilan(kart.id)}
      onKapatmaBirak={() => setKapatilan(null)}
      // Kapanınca /me tazelenir: liste durumu oradan okuyor;
      // öneriler de "kapandı" olduğu için yeniden okunur.
      onKapandi={() => {
        setKapatilan(null);
        void tazele();
        void oku();
      }}
    />
  );

  return (
    <Sayfa genislik="genis">
      {hata ? <HataKutusu hata={hata} tekrarDene={() => void oku()} /> : null}

      <div className="grid items-start gap-8 lg:grid-cols-[19rem_minmax(0,1fr)]">
        <aside
          aria-label="Özet"
          className="order-2 flex flex-col gap-4 lg:sticky lg:top-24 lg:order-1"
        >
          <FirmaOzeti ad={ad} kartVar={hesap.firma_karti_var} />
          <EksikAdimlar adimlar={firmaEksikAdimlari(hesap)} />
          {kartlar.length > 0 ? (
            <AdayListesi satirlar={adaySatirlari(oneriler ?? [])} />
          ) : null}
        </aside>

        <div className="order-1 flex min-w-0 flex-col gap-8 lg:order-2">
          <header className="flex flex-col gap-1.5">
            <h1 className="font-heading text-3xl font-semibold text-balance text-ana sm:text-4xl">
              {ad}
            </h1>
            <p className="text-[15px] text-pretty text-muted-foreground">
              {kurumOzetCumlesi(bekleyenAdet, acikIhtiyac, adaySayisi)}
            </p>
          </header>

          <EpostaDogrulamaBandi hesap={hesap} />

          {kartlar.length === 0 ? (
            // İki kapı (docs/kararlar.md F9): ilk ihtiyaç tek çağrı.
            <section className="flex flex-col items-start gap-4 rounded-xl bg-ana px-7 py-8 text-zemin">
              <p className="text-xs font-medium text-zemin/70">İlk adım</p>
              <h2 className="font-heading text-2xl font-semibold text-balance">
                Önce ihtiyacınızı tanımlayalım
              </h2>
              <p className="max-w-prose text-[15px] leading-relaxed text-pretty text-zemin/85">
                Kısa bir sohbetle ihtiyacınızı netleştirin; size uygun adayları
                gösterelim. Genç yetenek ya da iş birliği ortağı
                arayabilirsiniz.
              </p>
              <div className="flex flex-wrap gap-3">
                <Link
                  href={KAPILAR[0].yol}
                  className="inline-flex h-10 items-center rounded-lg bg-vurgu px-4 text-sm font-semibold text-metin hover:bg-vurgu/90"
                >
                  {KAPILAR[0].baslik}
                </Link>
                <Link
                  href={KAPILAR[1].yol}
                  className="inline-flex h-10 items-center rounded-lg border border-zemin/40 px-4 text-sm font-semibold text-zemin hover:bg-zemin/10"
                >
                  {KAPILAR[1].baslik}
                </Link>
              </div>
            </section>
          ) : null}

          {bekleyenAdet > 0 ? (
            <section
              aria-labelledby="bekleyenler"
              className="flex flex-col gap-4"
            >
              <BolumBasligi
                id="bekleyenler"
                baslik="Sizi bekleyenler"
                sayi={bekleyenAdet}
              />
              <ul className="flex flex-col gap-3">
                {bekleyen.ilgiler.map((oneri) => (
                  <IlgiGosterenKarti key={oneri.eslesme_id} oneri={oneri} />
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

          {kartlar.length > 0 ? (
            <section
              id="ihtiyaclar"
              aria-labelledby="ihtiyaclar-baslik"
              className="flex scroll-mt-24 flex-col gap-4"
            >
              <div className="flex flex-wrap items-end justify-between gap-x-4 gap-y-3">
                <BolumBasligi
                  id="ihtiyaclar-baslik"
                  baslik="İhtiyaçlarınız"
                  sayi={acikIhtiyac}
                />
                <YeniIhtiyacMenusu />
              </div>
              {acikKartlar.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  Şu an açık bir ihtiyacınız yok.
                </p>
              ) : (
                <ul className="flex flex-col gap-4">
                  {acikKartlar.map(ihtiyacSatiri)}
                </ul>
              )}
              {kapaliKartlar.length > 0 ? (
                <KapaliBolum
                  baslik="Kapanan ihtiyaçlar"
                  sayi={kapaliKartlar.length}
                >
                  {kapaliKartlar.map(ihtiyacSatiri)}
                </KapaliBolum>
              ) : null}
            </section>
          ) : null}

          {hesap.firma_karti_var ? (
            // Aday olarak (firma kartıyla) gördükleri: fırsatlar ve ilgiler.
            <FirmaFirsatlari />
          ) : null}

          <section
            id="isbirlikleri"
            aria-labelledby="isbirlikleri-baslik"
            className="flex scroll-mt-24 flex-col gap-4"
          >
            <BolumBasligi
              id="isbirlikleri-baslik"
              baslik="İş birliklerim"
              sayi={isbirlikleri?.length}
            />
            {isbirlikleri === null ? (
              <ListeIskeleti satir={1} />
            ) : isbirlikleri.length === 0 ? (
              <BosDurum
                metin="Henüz iş birliğiniz yok. Bir aday ilginizi kabul ettiğinde iş birliği burada açılır ve iletişim bilgileri görünür."
                eylem={
                  ilkAcikIhtiyac
                    ? {
                        href: `/kurum/oneriler?ihtiyac=${ilkAcikIhtiyac.id}`,
                        etiket: "Adayları gör",
                      }
                    : undefined
                }
              />
            ) : (
              <>
                {surenIsbirlikleri.length > 0 ? (
                  <ul className="flex flex-col gap-4">
                    {surenIsbirlikleri.map(isbirligiSatiri)}
                  </ul>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    Şu an süren bir iş birliğiniz yok.
                  </p>
                )}
                {biten.length > 0 ? (
                  <KapaliBolum
                    baslik="Tamamlanan iş birlikleri"
                    sayi={biten.length}
                    acik={surenIsbirlikleri.length === 0}
                  >
                    {biten.map(isbirligiSatiri)}
                  </KapaliBolum>
                ) : null}
              </>
            )}
          </section>
        </div>
      </div>

      {duzenlenen && kartlar.some((kart) => kart.id === duzenlenen) ? (
        <IlanDuzenlemePaneli
          key={duzenlenen}
          kartId={duzenlenen}
          onKapat={() => {
            setDuzenlenen(null);
            // Adresteki ?duzenle= yenilemede paneli yeniden açmasın.
            window.history.replaceState(null, "", "/kurum");
          }}
          // /me ihtiyaç metnini, öneriler adayları taşıyor; ikisi de tazelenir.
          onKaydedildi={() => {
            void tazele();
            void oku();
          }}
        />
      ) : null}
    </Sayfa>
  );
}
