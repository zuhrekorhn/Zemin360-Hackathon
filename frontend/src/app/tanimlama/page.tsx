"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useRef, useState } from "react";

import { Sayfa, SayfaBasligi } from "@/components/sayfa";
import {
  IhtiyacFormu,
  OlcumBelirlenecekRozeti,
} from "@/components/ihtiyac-formu";

import { GirisKapisi } from "@/components/giris-kapisi";
import { EslestirmeyeHazirla } from "@/components/eslestirmeye-hazirla";
import {
  CevapAlani,
  HataKutusu,
  type Mesaj,
  Sohbet,
  type SohbetHatasi,
} from "@/components/sohbet";
import { Button } from "@/components/ui/button";
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
import { type Aranan, arananParametresi } from "@/lib/ilan";
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
        <TanimlamaSohbeti />
      </Suspense>
    </GirisKapisi>
  );
}

function TanimlamaSohbeti() {
  // İki kapı (docs/plans/firma-akisi.md § 0 karar 4): ortak ilanı `?aranan=firma`.
  const aranan: Aranan = arananParametresi(useSearchParams().get("aranan"));
  const ortak = aranan === "firma";
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

  return (
    <Sayfa>
      <SayfaBasligi
        baslik="İhtiyacınızı tanımlayın"
        aciklama={
          ortak
            ? "Kısa bir sohbetle bir iş birliği ortağıyla çözmek istediğiniz ihtiyacı netleştireceğiz; ihtiyacınıza uyan firmaları göstereceğiz. Bu sohbet yapay zekâ desteğiyle ilerler. İhtiyacınız siz onaylamadan kaydedilmez."
            : "Kısa bir sohbetle ihtiyacınızı ölçülebilir bir ihtiyaç kartına çevireceğiz. Bu sohbet yapay zekâ desteğiyle ilerler. İhtiyacınız siz onaylamadan kaydedilmez."
        }
      />

      {asama === "sohbet" ? (
        <Sohbet
          ajanAdi="Zemin360"
          mesajlar={mesajlar}
          bekleniyor={bekleniyor}
          sonMesajRef={sonMesaj}
        />
      ) : null}

      {hata ? <HataKutusu hata={hata} tekrarDene={tekrarDene} /> : null}

      {asama === "sohbet" ? (
        <CevapAlani
          girdi={girdi}
          setGirdi={setGirdi}
          bekleniyor={bekleniyor}
          gonder={gonder}
        />
      ) : null}

      {asama === "taslak" && taslak ? (
        <IhtiyacFormu
          taslak={taslak}
          ortak={ortak}
          bekleniyor={bekleniyor}
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

      {asama === "kaydedildi" && kart ? (
        <KayitliKart kart={kart} onGuncelle={setKart} />
      ) : null}

      <footer className="mt-auto border-t border-kenar pt-6">
        <Button asChild variant="outline" size="lg">
          <Link href="/kurum">Panele dön</Link>
        </Button>
      </footer>
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
    <article className="rounded-sm border border-kenar bg-card">
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

function KayitliKart({
  kart,
  onGuncelle,
}: {
  kart: IhtiyacKartiYaniti;
  onGuncelle: (kart: IhtiyacKartiYaniti) => void;
}) {
  return (
    <section className="flex flex-col gap-3">
      <h2 className="font-heading text-xl font-semibold text-ana">
        İhtiyaç kartınız kaydedildi
      </h2>
      {kart.embedding_var ? (
        <p className="text-sm text-pretty text-muted-foreground">
          {kart.aranan === "firma"
            ? "Artık firma kartlarıyla eşleştirilebilir."
            : "Artık gençlerin yetenek kartlarıyla eşleştirilebilir."}
        </p>
      ) : (
        <EslestirmeyeHazirla
          hazirla={async () => onGuncelle(await ihtiyacKartiHazirla(kart.id))}
        />
      )}

      <TaslakKarti
        taslak={kart}
        ortak={kart.aranan === "firma"}
        kurumAdi={kart.kurum.ad}
        olcumBelirlenecek={kart.olcum_belirlenecek}
      />

      <p className="font-mono text-xs text-muted-foreground">
        kart no: <span className="break-all">{kart.id}</span>
      </p>

      <Button asChild size="lg" className="mt-1 w-fit">
        <Link href={`/kurum/oneriler?ihtiyac=${kart.id}`}>
          Uygun adayları gör
        </Link>
      </Button>
    </section>
  );
}
