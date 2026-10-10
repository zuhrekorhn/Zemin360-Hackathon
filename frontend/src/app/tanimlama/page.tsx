"use client";

import { CalendarClock, Search, UserRoundPlus } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useRef, useState } from "react";

import { Sayfa, SayfaBasligi } from "@/components/sayfa";
import { IhtiyacOnizleme } from "@/components/sohbet-onizlemeleri";
import {
  IhtiyacFormu,
  OlcumBelirlenecekRozeti,
} from "@/components/ihtiyac-formu";

import { GirisKapisi, useGirisliHesap } from "@/components/giris-kapisi";
import { EslestirmeyeHazirla } from "@/components/eslestirmeye-hazirla";
import {
  CevapAlani,
  HataKutusu,
  type Mesaj,
  Sohbet,
  type SohbetHatasi,
} from "@/components/sohbet";
import { KUTU } from "@/components/ui/yuzey";
import {
  type IhtiyacKartiYaniti,
  type IhtiyacTaslagi,
  ApiHatasi,
  ihtiyacKartiHazirla,
  ihtiyacKartiOnayla,
  tanimlamaBaslat,
  tanimlamaCevap,
  tanimlamaSohbetDurumu,
} from "@/lib/api";
import {
  sohbetOturumuOku,
  sohbetOturumuSil,
  sohbetOturumuYaz,
} from "@/lib/sohbet-oturumu";
import { isbirligiTuruEtiketi } from "@/lib/firma-karti";
import { FIRMA_TURLERI } from "@/lib/firma-profil";
import { hatayaCevir } from "@/lib/hata";
import { cn } from "@/lib/utils";
import { type Aranan, KAPILAR, arananParametresi } from "@/lib/ilan";
import {
  CALISMA_MODELI_ETIKETLERI,
  MUSAITLIK_ETIKETLERI,
  etiketle,
  sehirEtiketi,
} from "@/lib/sabitler";

/**
 * Tanımlama Ajanı sohbeti (docs/agent-specs.md § 2).
 *
 * Keşif ile aynı akış: sohbet → taslak gözden geçirme → onay → kaydedilen kart.
 * Fark soru setinde: ajan sokratik sorularla belirsiz ifadeyi ölçülebilir hale
 * getirir. Kart kurum onaylamadan veritabanına yazılmaz.
 */

type Asama = "sohbet" | "taslak" | "kaydedildi";

export default function TanimlamaSayfasi() {
  return (
    <GirisKapisi roller={["kurum"]}>
      <Suspense fallback={null}>
        <TanimlamaGirisi />
      </Suspense>
    </GirisKapisi>
  );
}

/**
 * Kapı adreste açıkça seçilmişse sohbet başlar; seçilmemişse (üst menüdeki
 * "Yeni ihtiyaç") önce kimi aradığı sorulur. Eskiden `/tanimlama` sessizce
 * genç kapısını açıyordu ve firma, iş birliği ortağı kapısını bulamıyordu.
 */
function TanimlamaGirisi() {
  const parametre = useSearchParams().get("aranan");
  if (parametre === "genc" || parametre === "firma")
    return <TanimlamaSohbeti />;
  return <KapiSecimi />;
}

function KapiSecimi() {
  return (
    <Sayfa genislik="form">
      <SayfaBasligi
        baslik="Ne arıyorsunuz?"
        aciklama="Önce kimi aradığınızı seçin; ardından kısa bir sohbetle ihtiyacınızı netleştireceğiz."
      />
      <ul className="grid gap-4 sm:grid-cols-2">
        {KAPILAR.map((kapi) => (
          <li key={kapi.aranan}>
            <Link
              href={kapi.yol}
              className={cn(
                KUTU,
                "flex h-full flex-col gap-2 px-5 py-5 outline-none hover:border-ana/40 focus-visible:ring-3 focus-visible:ring-baglanti/40",
              )}
            >
              <span className="font-heading text-lg font-semibold text-ana">
                {kapi.baslik}
              </span>
              <span className="text-sm text-pretty text-muted-foreground">
                {kapi.aciklama}
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </Sayfa>
  );
}

function TanimlamaSohbeti() {
  // İki kapı (docs/kararlar.md F4): ortak ilanı `?aranan=firma`.
  const aranan: Aranan = arananParametresi(useSearchParams().get("aranan"));
  const ortak = aranan === "firma";
  const hesap = useGirisliHesap();
  const [asama, setAsama] = useState<Asama>("sohbet");
  const [oturumId, setOturumId] = useState<string | null>(null);
  const [mesajlar, setMesajlar] = useState<Mesaj[]>([]);
  const [taslak, setTaslak] = useState<IhtiyacTaslagi | null>(null);
  const [kart, setKart] = useState<IhtiyacKartiYaniti | null>(null);

  const [girdi, setGirdi] = useState("");
  const [bekleniyor, setBekleniyor] = useState(false);
  const [hata, setHata] = useState<SohbetHatasi | null>(null);

  const bekleyenCevap = useRef<string | null>(null);
  const baslatildi = useRef(false);
  const sonMesaj = useRef<HTMLDivElement | null>(null);

  // Hata cümlesi tek yerden: lib/hata.ts (429 hız sınırı, 503 arıza ayrımı orada).
  const hatayiYaz = useCallback(
    (sebep: unknown) => setHata(hatayaCevir(sebep)),
    [],
  );

  // Kapı başına bir açık sohbet: yenilenen sayfa onu sürdürür.
  const oturumAnahtari = `tanimlama-oturumu:${aranan}`;

  const sohbetiBaslat = useCallback(async () => {
    setHata(null);
    setBekleniyor(true);
    try {
      const kayitli = sohbetOturumuOku(oturumAnahtari);
      if (kayitli) {
        try {
          const durum = await tanimlamaSohbetDurumu(kayitli);
          setOturumId(durum.oturum_id);
          setMesajlar(durum.mesajlar);
          setTaslak(durum.taslak);
          if (durum.taslak_hazir) setAsama("taslak");
          return;
        } catch (sebep) {
          // Sohbet yok (silinmiş, başka hesap): yenisi açılır. Diğer hatalar
          // gösterilir; "Tekrar dene" aynı sohbeti yeniden ister.
          if (!(sebep instanceof ApiHatasi && sebep.durumKodu === 404)) {
            throw sebep;
          }
          sohbetOturumuSil(oturumAnahtari);
        }
      }
      const yanit = await tanimlamaBaslat(aranan);
      sohbetOturumuYaz(oturumAnahtari, yanit.oturum_id);
      setOturumId(yanit.oturum_id);
      setMesajlar(yanit.soru ? [{ kim: "ajan", metin: yanit.soru }] : []);
      setTaslak(yanit.taslak);
    } catch (sebep) {
      hatayiYaz(sebep);
    } finally {
      setBekleniyor(false);
    }
  }, [hatayiYaz, aranan, oturumAnahtari]);

  useEffect(() => {
    // StrictMode efekti iki kez çalıştırıyor; ikinci oturum açılmasın.
    if (baslatildi.current) return;
    baslatildi.current = true;
    void sohbetiBaslat();
  }, [sohbetiBaslat]);

  useEffect(() => {
    sonMesaj.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [mesajlar, bekleniyor]);

  async function cevapGonder(cevap: string) {
    if (!oturumId || !cevap.trim()) return;

    setHata(null);
    setBekleniyor(true);
    bekleyenCevap.current = cevap;

    try {
      const yanit = await tanimlamaCevap(oturumId, cevap);
      bekleyenCevap.current = null;
      setTaslak(yanit.taslak);

      if (yanit.taslak_hazir) {
        setAsama("taslak");
      } else if (yanit.soru) {
        setMesajlar((oncekiler) => [
          ...oncekiler,
          { kim: "ajan", metin: yanit.soru as string },
        ]);
      }
    } catch (sebep) {
      hatayiYaz(sebep);
    } finally {
      setBekleniyor(false);
    }
  }

  function gonder() {
    const cevap = girdi.trim();
    if (!cevap || bekleniyor) return;
    setMesajlar((oncekiler) => [
      ...oncekiler,
      { kim: "kullanici", metin: cevap },
    ]);
    setGirdi("");
    void cevapGonder(cevap);
  }

  function tekrarDene() {
    if (bekleyenCevap.current) {
      void cevapGonder(bekleyenCevap.current);
    } else if (!oturumId) {
      void sohbetiBaslat();
    }
  }

  const baslik = (
    <SayfaBasligi
      baslik="İhtiyacınızı tanımlayın"
      aciklama={
        ortak
          ? "Kısa bir sohbetle bir iş birliği ortağıyla çözmek istediğiniz ihtiyacı netleştireceğiz; ihtiyacınıza uyan firmaları göstereceğiz. Bu sohbet yapay zekâ desteğiyle ilerler. İhtiyacınız siz onaylamadan kaydedilmez."
          : "Kısa bir sohbetle ihtiyacınızı ölçülebilir bir ihtiyaç kartına çevireceğiz. Bu sohbet yapay zekâ desteğiyle ilerler. İhtiyacınız siz onaylamadan kaydedilmez."
      }
    />
  );

  // Sohbet sürerken: solda sohbet, sağda ihtiyacın canlı hali (Keşif'le aynı iskelet).
  if (asama === "sohbet") {
    return (
      <Sayfa genislik="genis">
        <div className="grid items-start gap-8 lg:grid-cols-[minmax(0,1fr)_20rem]">
          <div className="flex min-w-0 flex-col gap-6">
            {baslik}
            {hata ? <HataKutusu hata={hata} tekrarDene={tekrarDene} /> : null}
            <Sohbet
              ajanAdi="Zemin360"
              mesajlar={mesajlar}
              bekleniyor={bekleniyor}
              sonMesajRef={sonMesaj}
              altKisim={
                <CevapAlani
                  girdi={girdi}
                  setGirdi={setGirdi}
                  bekleniyor={bekleniyor}
                  gonder={gonder}
                />
              }
            />
          </div>
          <aside aria-label="İhtiyacınız" className="lg:sticky lg:top-24">
            <IhtiyacOnizleme
              taslak={taslak}
              ortak={ortak}
              firmaAdi={hesap.ad ?? ""}
            />
          </aside>
        </div>
      </Sayfa>
    );
  }

  if (asama === "kaydedildi" && kart) {
    return (
      <Sayfa genislik="genis">
        <div className="mx-auto flex w-full max-w-4xl flex-col gap-6">
          <h1 className="sr-only">İhtiyacınız kaydedildi</h1>
          <KayitliKart kart={kart} onGuncelle={setKart} />
        </div>
      </Sayfa>
    );
  }

  // Taslak: sohbetten çıkan ihtiyacı gözden geçirip onaylama.
  return (
    <Sayfa genislik="form">
      <SayfaBasligi
        baslik="İhtiyacınızı gözden geçirin"
        aciklama="Sohbetten çıkan ihtiyaç bu. Yanlış anlaşılan bir şey varsa düzeltin; doğruysa onaylayın. İhtiyacınız siz onaylamadan kaydedilmez."
      />
      {hata ? <HataKutusu hata={hata} tekrarDene={tekrarDene} /> : null}
      {taslak ? (
        <IhtiyacFormu
          taslak={taslak}
          ortak={ortak}
          bekleniyor={bekleniyor}
          baslikGizle
          onGonder={async (kurumProfili, duzeltilmisTaslak) => {
            if (!oturumId) return;
            setHata(null);
            setBekleniyor(true);
            try {
              const kayitli = await ihtiyacKartiOnayla(
                oturumId,
                kurumProfili,
                duzeltilmisTaslak,
              );
              setKart(kayitli);
              setAsama("kaydedildi");
              // Kaydedilen ihtiyacın sohbeti kapandı; yenileme yeni sohbet açar.
              sohbetOturumuSil(oturumAnahtari);
            } catch (sebep) {
              hatayiYaz(sebep);
            } finally {
              setBekleniyor(false);
            }
          }}
        />
      ) : null}
    </Sayfa>
  );
}

/* --- Kart gösterimleri ---------------------------------------------------- */

function TaslakKarti({
  taslak,
  ortak = false,
  kurumAdi,
  olcumBelirlenecek = false,
}: {
  taslak: IhtiyacTaslagi;
  ortak?: boolean;
  kurumAdi?: string;
  olcumBelirlenecek?: boolean;
}) {
  const olcut = taslak.basari_olcutu;
  const olcutParcalari = [
    olcut?.mevcut_deger ? `Bugün: ${olcut.mevcut_deger}` : null,
    olcut?.hedef_deger ? `Hedef: ${olcut.hedef_deger}` : null,
    olcut?.sure ? `Süre: ${olcut.sure}` : null,
  ].filter(Boolean);
  return (
    <article className={cn(KUTU, "overflow-hidden")}>
      {kurumAdi ? (
        <div className="border-b border-kenar px-4 py-3">
          <p className="text-xs text-muted-foreground">Firma</p>
          <p className="text-sm break-words">{kurumAdi}</p>
        </div>
      ) : null}

      <div className="border-b border-kenar px-4 py-3">
        <p className="text-xs text-muted-foreground">Problem</p>
        <p className="text-sm text-pretty break-words">
          {taslak.problem_tanimi || "—"}
        </p>
      </div>

      <div className="border-b border-kenar px-4 py-3">
        <p className="text-xs text-muted-foreground">Başarı kriteri</p>
        <p className="text-sm text-pretty break-words">
          {taslak.basari_kriteri || "—"}
        </p>
        {olcumBelirlenecek ? (
          <div className="mt-2">
            <OlcumBelirlenecekRozeti />
          </div>
        ) : olcutParcalari.length ? (
          <p className="mt-1 text-xs text-muted-foreground">
            {olcutParcalari.join(" · ")}
          </p>
        ) : null}
      </div>

      {taslak.kisitlar ? (
        <div className="border-b border-kenar px-4 py-3">
          <p className="text-xs text-muted-foreground">Kısıtlar</p>
          <p className="text-sm text-pretty break-words">{taslak.kisitlar}</p>
        </div>
      ) : null}

      <dl className="grid gap-px bg-kenar sm:grid-cols-2">
        <div className="bg-card px-4 py-3">
          <dt className="text-xs text-muted-foreground">Aranan şehir</dt>
          <dd className="text-sm break-words">
            {ortak && !taslak.sehir_tercihi
              ? "Fark etmez"
              : sehirEtiketi(taslak.sehir_tercihi)}
          </dd>
        </div>
        {ortak ? (
          <>
            <div className="bg-card px-4 py-3">
              <dt className="text-xs text-muted-foreground">
                Aranan firma türleri
              </dt>
              <dd className="text-sm break-words">
                {taslak.aranan_firma_turleri?.length
                  ? taslak.aranan_firma_turleri
                      .map(
                        (tur) =>
                          FIRMA_TURLERI.find((t) => t.deger === tur)?.etiket ??
                          tur,
                      )
                      .join(", ")
                  : "Hepsi"}
              </dd>
            </div>
            <div className="bg-card px-4 py-3">
              <dt className="text-xs text-muted-foreground">İş birliği türü</dt>
              <dd className="text-sm break-words">
                {taslak.isbirligi_turu
                  ? isbirligiTuruEtiketi(taslak.isbirligi_turu)
                  : "—"}
              </dd>
            </div>
          </>
        ) : (
          <>
            <div className="bg-card px-4 py-3">
              <dt className="text-xs text-muted-foreground">Çalışma modeli</dt>
              <dd className="text-sm break-words">
                {etiketle(CALISMA_MODELI_ETIKETLERI, taslak.calisma_modeli)}
              </dd>
            </div>
            <div className="bg-card px-4 py-3">
              <dt className="text-xs text-muted-foreground">
                Müsaitlik tercihi
              </dt>
              <dd className="text-sm break-words">
                {etiketle(MUSAITLIK_ETIKETLERI, taslak.musaitlik_tercihi)}
              </dd>
            </div>
          </>
        )}
      </dl>
    </article>
  );
}

/**
 * Kaydedildikten hemen sonra: ihtiyacın hazır olduğunu söyleyen bant, kaydedilen
 * kart ve sonraki adımlar (Keşif'teki `KayitliKart`ın eşi).
 */
function KayitliKart({
  kart,
  onGuncelle,
}: {
  kart: IhtiyacKartiYaniti;
  onGuncelle: (kart: IhtiyacKartiYaniti) => void;
}) {
  const ortak = kart.aranan === "firma";
  const adaylarYolu = `/kurum/oneriler?ihtiyac=${kart.id}`;
  const adimlar = [
    {
      ikon: Search,
      baslik: "Adayları gör",
      metin: ortak
        ? "Firma kartlarıyla eşleşen uygun firmalar ve neden uygun oldukları."
        : "Yetenek kartlarıyla eşleşen uygun adaylar ve neden uygun oldukları.",
      href: adaylarYolu,
    },
    {
      ikon: CalendarClock,
      baslik: "İhtiyacı düzenle",
      metin:
        "Bir şeyi eksik ya da yanlış yazdıysanız düzeltin; adaylar yeniden belirlenir.",
      href: `/kurum?duzenle=${kart.id}`,
    },
    {
      ikon: UserRoundPlus,
      baslik: "Başka bir ihtiyaç",
      metin: "Farklı bir konuda ayrı bir ihtiyaç tanımlayın.",
      href: ortak ? "/tanimlama?aranan=firma" : "/tanimlama?aranan=genc",
    },
  ];

  return (
    <section className="flex flex-col gap-6">
      <div className="flex flex-col gap-4 rounded-xl bg-ana px-7 py-7 text-zemin sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-col gap-1.5">
          <p className="text-xs font-medium text-zemin/70">
            İhtiyacınız kaydedildi
          </p>
          <h2 className="font-heading text-2xl font-semibold text-balance">
            İhtiyacınız hazır
          </h2>
          <p className="max-w-prose text-[15px] text-pretty text-zemin/85">
            {kart.embedding_var
              ? ortak
                ? "Artık firma kartlarıyla eşleştirilebilir."
                : "Artık gençlerin yetenek kartlarıyla eşleştirilebilir."
              : "Uygun adayları bulmak için eşleştirmeye hazırlanması gerekiyor."}
          </p>
        </div>
        <Link
          href={adaylarYolu}
          className="inline-flex h-10 shrink-0 items-center justify-center self-start rounded-lg bg-vurgu px-5 text-sm font-semibold text-metin hover:bg-vurgu/90 sm:self-center"
        >
          Uygun adayları gör
        </Link>
      </div>

      {kart.embedding_var ? null : (
        <EslestirmeyeHazirla
          hazirla={async () => onGuncelle(await ihtiyacKartiHazirla(kart.id))}
        />
      )}

      <TaslakKarti
        taslak={kart}
        ortak={ortak}
        kurumAdi={kart.kurum.ad}
        olcumBelirlenecek={kart.olcum_belirlenecek}
      />

      <div className="flex flex-col gap-3">
        <h3 className="font-heading text-lg font-semibold text-ana">
          Sırada ne var
        </h3>
        <ul className="grid gap-3 sm:grid-cols-3">
          {adimlar.map(({ ikon: Ikon, baslik, metin, href }) => (
            <li key={baslik}>
              <Link
                href={href}
                className={cn(
                  KUTU,
                  "flex h-full flex-col gap-2 px-5 py-5 transition-colors hover:border-ana",
                )}
              >
                <Ikon aria-hidden="true" className="size-5 text-baglanti" />
                <span className="font-medium text-ana">{baslik}</span>
                <span className="text-sm text-pretty text-muted-foreground">
                  {metin}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
