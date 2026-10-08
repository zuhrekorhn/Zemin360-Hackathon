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
import { type Aranan, arananParametresi } from "@/lib/ilan";
import {
  CALISMA_MODELI_ETIKETLERI,
  MUSAITLIK_ETIKETLERI,
  etiketle,
  sehirEtiketi,
} from "@/lib/sabitler";

/**
 * TanÄ±mlama AjanÄ± sohbeti (docs/agent-specs.md Â§ 2).
 *
 * KeÅŸif ile aynÄ± akÄ±ÅŸ: sohbet â†’ taslak gÃ¶zden geÃ§irme â†’ onay â†’ kaydedilen kart.
 * Fark soru setinde: ajan sokratik sorularla belirsiz ifadeyi Ã¶lÃ§Ã¼lebilir hale
 * getirir. Kart kurum onaylamadan veritabanÄ±na yazÄ±lmaz.
 */

type Asama = "sohbet" | "taslak" | "kaydedildi";

export default function TanimlamaSayfasi() {
  return (
    <GirisKapisi roller={["kurum"]}>
      <Suspense fallback={null}>
        <TanimlamaSohbeti />
      </Suspense>
    </GirisKapisi>
  );
}

function TanimlamaSohbeti() {
  // Ä°ki kapÄ± (docs/kararlar.md F4): ortak ilanÄ± `?aranan=firma`.
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

  // Hata cÃ¼mlesi tek yerden: lib/hata.ts (429 hÄ±z sÄ±nÄ±rÄ±, 503 arÄ±za ayrÄ±mÄ± orada).
  const hatayiYaz = useCallback(
    (sebep: unknown) => setHata(hatayaCevir(sebep)),
    [],
  );

  // KapÄ± baÅŸÄ±na bir aÃ§Ä±k sohbet: yenilenen sayfa onu sÃ¼rdÃ¼rÃ¼r.
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
          // Sohbet yok (silinmiÅŸ, baÅŸka hesap): yenisi aÃ§Ä±lÄ±r. DiÄŸer hatalar
          // gÃ¶sterilir; "Tekrar dene" aynÄ± sohbeti yeniden ister.
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
    // StrictMode efekti iki kez Ã§alÄ±ÅŸtÄ±rÄ±yor; ikinci oturum aÃ§Ä±lmasÄ±n.
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
      baslik="Ä°htiyacÄ±nÄ±zÄ± tanÄ±mlayÄ±n"
      aciklama={
        ortak
          ? "KÄ±sa bir sohbetle bir iÅŸ birliÄŸi ortaÄŸÄ±yla Ã§Ã¶zmek istediÄŸiniz ihtiyacÄ± netleÅŸtireceÄŸiz; ihtiyacÄ±nÄ±za uyan firmalarÄ± gÃ¶stereceÄŸiz. Bu sohbet yapay zekÃ¢ desteÄŸiyle ilerler. Ä°htiyacÄ±nÄ±z siz onaylamadan kaydedilmez."
          : "KÄ±sa bir sohbetle ihtiyacÄ±nÄ±zÄ± Ã¶lÃ§Ã¼lebilir bir ihtiyaÃ§ kartÄ±na Ã§evireceÄŸiz. Bu sohbet yapay zekÃ¢ desteÄŸiyle ilerler. Ä°htiyacÄ±nÄ±z siz onaylamadan kaydedilmez."
      }
    />
  );

  // Sohbet sÃ¼rerken: solda sohbet, saÄŸda ihtiyacÄ±n canlÄ± hali (KeÅŸif'le aynÄ± iskelet).
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
          <aside aria-label="Ä°htiyacÄ±nÄ±z" className="lg:sticky lg:top-24">
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
          <h1 className="sr-only">Ä°htiyacÄ±nÄ±z kaydedildi</h1>
          <KayitliKart kart={kart} onGuncelle={setKart} />
        </div>
      </Sayfa>
    );
  }

  // Taslak: sohbetten Ã§Ä±kan ihtiyacÄ± gÃ¶zden geÃ§irip onaylama.
  return (
    <Sayfa genislik="form">
      <SayfaBasligi
        baslik="Ä°htiyacÄ±nÄ±zÄ± gÃ¶zden geÃ§irin"
        aciklama="Sohbetten Ã§Ä±kan ihtiyaÃ§ bu. YanlÄ±ÅŸ anlaÅŸÄ±lan bir ÅŸey varsa dÃ¼zeltin; doÄŸruysa onaylayÄ±n. Ä°htiyacÄ±nÄ±z siz onaylamadan kaydedilmez."
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
              // Kaydedilen ihtiyacÄ±n sohbeti kapandÄ±; yenileme yeni sohbet aÃ§ar.
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

/* --- Kart gÃ¶sterimleri ---------------------------------------------------- */

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
    olcut?.mevcut_deger ? `BugÃ¼n: ${olcut.mevcut_deger}` : null,
    olcut?.hedef_deger ? `Hedef: ${olcut.hedef_deger}` : null,
    olcut?.sure ? `SÃ¼re: ${olcut.sure}` : null,
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
          {taslak.problem_tanimi || "â€”"}
        </p>
      </div>

      <div className="border-b border-kenar px-4 py-3">
        <p className="text-xs text-muted-foreground">BaÅŸarÄ± kriteri</p>
        <p className="text-sm text-pretty break-words">
          {taslak.basari_kriteri || "â€”"}
        </p>
        {olcumBelirlenecek ? (
          <div className="mt-2">
            <OlcumBelirlenecekRozeti />
          </div>
        ) : olcutParcalari.length ? (
          <p className="mt-1 text-xs text-muted-foreground">
            {olcutParcalari.join(" Â· ")}
          </p>
        ) : null}
      </div>

      {taslak.kisitlar ? (
        <div className="border-b border-kenar px-4 py-3">
          <p className="text-xs text-muted-foreground">KÄ±sÄ±tlar</p>
          <p className="text-sm text-pretty break-words">{taslak.kisitlar}</p>
        </div>
      ) : null}

      <dl className="grid gap-px bg-kenar sm:grid-cols-2">
        <div className="bg-card px-4 py-3">
          <dt className="text-xs text-muted-foreground">Aranan ÅŸehir</dt>
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
                Aranan firma tÃ¼rleri
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
              <dt className="text-xs text-muted-foreground">Ä°ÅŸ birliÄŸi tÃ¼rÃ¼</dt>
              <dd className="text-sm break-words">
                {taslak.isbirligi_turu
                  ? isbirligiTuruEtiketi(taslak.isbirligi_turu)
                  : "â€”"}
              </dd>
            </div>
          </>
        ) : (
          <>
            <div className="bg-card px-4 py-3">
              <dt className="text-xs text-muted-foreground">Ã‡alÄ±ÅŸma modeli</dt>
              <dd className="text-sm break-words">
                {etiketle(CALISMA_MODELI_ETIKETLERI, taslak.calisma_modeli)}
              </dd>
            </div>
            <div className="bg-card px-4 py-3">
              <dt className="text-xs text-muted-foreground">
                MÃ¼saitlik tercihi
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
 * Kaydedildikten hemen sonra: ihtiyacÄ±n hazÄ±r olduÄŸunu sÃ¶yleyen bant, kaydedilen
 * kart ve sonraki adÄ±mlar (KeÅŸif'teki `KayitliKart`Ä±n eÅŸi).
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
      baslik: "AdaylarÄ± gÃ¶r",
      metin: ortak
        ? "Firma kartlarÄ±yla eÅŸleÅŸen uygun firmalar ve neden uygun olduklarÄ±."
        : "Yetenek kartlarÄ±yla eÅŸleÅŸen uygun adaylar ve neden uygun olduklarÄ±.",
      href: adaylarYolu,
    },
    {
      ikon: CalendarClock,
      baslik: "Ä°htiyacÄ± dÃ¼zenle",
      metin:
        "Bir ÅŸeyi eksik ya da yanlÄ±ÅŸ yazdÄ±ysanÄ±z dÃ¼zeltin; adaylar yeniden belirlenir.",
      href: `/kurum?duzenle=${kart.id}`,
    },
    {
      ikon: UserRoundPlus,
      baslik: "BaÅŸka bir ihtiyaÃ§",
      metin: "FarklÄ± bir konuda ayrÄ± bir ihtiyaÃ§ tanÄ±mlayÄ±n.",
      href: ortak ? "/tanimlama?aranan=firma" : "/tanimlama",
    },
  ];

  return (
    <section className="flex flex-col gap-6">
      <div className="flex flex-col gap-4 rounded-xl bg-ana px-7 py-7 text-zemin sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-col gap-1.5">
          <p className="text-xs font-medium text-zemin/70">
            Ä°htiyacÄ±nÄ±z kaydedildi
          </p>
          <h2 className="font-heading text-2xl font-semibold text-balance">
            Ä°htiyacÄ±nÄ±z hazÄ±r
          </h2>
          <p className="max-w-prose text-[15px] text-pretty text-zemin/85">
            {kart.embedding_var
              ? ortak
                ? "ArtÄ±k firma kartlarÄ±yla eÅŸleÅŸtirilebilir."
                : "ArtÄ±k genÃ§lerin yetenek kartlarÄ±yla eÅŸleÅŸtirilebilir."
              : "Uygun adaylarÄ± bulmak iÃ§in eÅŸleÅŸtirmeye hazÄ±rlanmasÄ± gerekiyor."}
          </p>
        </div>
        <Link
          href={adaylarYolu}
          className="inline-flex h-10 shrink-0 items-center justify-center self-start rounded-lg bg-vurgu px-5 text-sm font-semibold text-metin hover:bg-vurgu/90 sm:self-center"
        >
          Uygun adaylarÄ± gÃ¶r
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
          SÄ±rada ne var
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
