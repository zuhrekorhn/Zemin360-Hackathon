"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useRef, useState } from "react";

import { Sayfa, SayfaBasligi } from "@/components/sayfa";
import { CokluSecim } from "@/components/coklu-secim";

import { GirisKapisi, useGirisliHesap } from "@/components/giris-kapisi";
import { EslestirmeyeHazirla } from "@/components/eslestirmeye-hazirla";
import {
  CevapAlani,
  FormAlani,
  HataKutusu,
  type Mesaj,
  Sohbet,
  type SohbetHatasi,
} from "@/components/sohbet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  type IhtiyacKartiYaniti,
  type IhtiyacTaslagi,
  type KurumProfili,
  ihtiyacKartiHazirla,
  ihtiyacKartiOnayla,
  tanimlamaBaslat,
  tanimlamaCevap,
} from "@/lib/api";
import { ISBIRLIGI_TURLERI, isbirligiTuruEtiketi } from "@/lib/firma-karti";
import { FIRMA_TURLERI, onaydaFirmaBilgisiSorulmali } from "@/lib/firma-profil";
import { hatayaCevir } from "@/lib/hata";
import { type Aranan, arananParametresi } from "@/lib/ilan";
import {
  CALISMA_MODELI_ETIKETLERI,
  CALISMA_MODELLERI,
  MUSAITLIK_ETIKETLERI,
  MUSAITLIK_SECENEKLERI,
  SEHIR_SECENEKLERI,
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

  const sohbetiBaslat = useCallback(async () => {
    setHata(null);
    setBekleniyor(true);
    try {
      const yanit = await tanimlamaBaslat(aranan);
      setOturumId(yanit.oturum_id);
      setMesajlar(yanit.soru ? [{ kim: "ajan", metin: yanit.soru }] : []);
      setTaslak(yanit.taslak);
    } catch (sebep) {
      hatayiYaz(sebep);
    } finally {
      setBekleniyor(false);
    }
  }, [hatayiYaz, aranan]);

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
        <TaslakBolumu
          taslak={taslak}
          ortak={ortak}
          bekleniyor={bekleniyor}
          onOnayla={async (kurumProfili, duzeltilmisTaslak) => {
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

/* --- Taslak ve onay ------------------------------------------------------- */

function TaslakBolumu({
  taslak,
  ortak,
  bekleniyor,
  onOnayla,
}: {
  taslak: IhtiyacTaslagi;
  ortak: boolean;
  bekleniyor: boolean;
  onOnayla: (
    kurumProfili: KurumProfili,
    duzeltilmisTaslak: IhtiyacTaslagi,
  ) => void;
}) {
  // Firmanın sektörü ve şehri kayıtta alınıyor (docs/plans/firma-akisi.md
  // § 0 karar 2); burada yalnızca bu alanlardan önce açılmış hesaplarda sorulur.
  const firmaBilgisiSor = onaydaFirmaBilgisiSorulmali(
    useGirisliHesap().eksik_profil_alanlari,
  );
  const [sektor, setSektor] = useState("");
  const [sehir, setSehir] = useState("");
  // İki ayrı şehir var ve karıştırılıyordu: kurumun bulunduğu yer ile
  // gencin bulunmasını istediğiniz yer. İkincisi eşleştirmenin sert
  // filtresi, o yüzden burada görünür ve düzeltilebilir.
  const [aranilanSehir, setAranilanSehir] = useState(
    taslak.sehir_tercihi ?? "",
  );
  // Tek seçim: iş nerede yapılacak. "Uzaktan" ise şehir filtresi uygulanmaz.
  const [calismaModeli, setCalismaModeli] = useState(
    taslak.calisma_modeli ?? "",
  );
  // Eşleştirmenin sert filtresi; ajan yanlış anlamış olabilir, kurum düzeltsin.
  const [musaitlik, setMusaitlik] = useState(taslak.musaitlik_tercihi ?? "");
  // Sohbetten çıkan metinler düzenlenebilir (sohbet tavana gelip boş kapatmış olabilir).
  const [problem, setProblem] = useState(taslak.problem_tanimi ?? "");
  const [kriter, setKriter] = useState(taslak.basari_kriteri ?? "");
  const [kisitlar, setKisitlar] = useState(taslak.kisitlar ?? "");
  // Ortak ilanı (docs/plans/firma-akisi.md § 5): aranan firma türleri ve iş
  // birliği türü; çalışma modeli ve müsaitlik sorulmaz.
  const [firmaTurleri, setFirmaTurleri] = useState<string[]>(
    taslak.aranan_firma_turleri ?? [],
  );
  const [isbirligiTuru, setIsbirligiTuru] = useState(
    taslak.isbirligi_turu ?? "",
  );

  return (
    <form
      className="flex flex-col gap-8"
      onSubmit={(olay) => {
        olay.preventDefault();
        if (bekleniyor) return;
        onOnayla(
          {
            sektor: sektor.trim() || null,
            sehir: sehir || null,
          },
          {
            ...taslak,
            problem_tanimi: problem.trim() || null,
            basari_kriteri: kriter.trim() || null,
            kisitlar: kisitlar.trim() || null,
            sehir_tercihi: aranilanSehir || null,
            calisma_modeli: ortak ? null : secimDegeri(calismaModeli),
            musaitlik_tercihi: ortak ? null : secimDegeri(musaitlik),
            aranan_firma_turleri: ortak ? firmaTurleri : [],
            isbirligi_turu: ortak ? isbirligiTuru || null : null,
          },
        );
      }}
    >
      <section className="flex flex-col gap-4">
        <div className="flex flex-col gap-1">
          <h2 className="font-heading text-xl font-semibold text-ana">
            İhtiyaç kartı taslağınız
          </h2>
          <p className="text-sm text-pretty text-muted-foreground">
            Sohbetten çıkan kart bu. Gözden geçirin, gerekirse düzeltin, sonra
            aşağıdan onaylayın.
          </p>
        </div>

        <MetinAlani
          id="problem"
          etiket="Problem"
          deger={problem}
          setDeger={setProblem}
          enUzun={PROBLEM_EN_UZUN}
          sohbetteBos={!taslak.problem_tanimi}
        />
        <MetinAlani
          id="basari-kriteri"
          etiket="Başarı kriteri"
          deger={kriter}
          setDeger={setKriter}
          enUzun={KRITER_EN_UZUN}
          sohbetteBos={!taslak.basari_kriteri}
        />
        <MetinAlani
          id="kisitlar"
          etiket="Kısıtlar"
          deger={kisitlar}
          setDeger={setKisitlar}
          enUzun={KRITER_EN_UZUN}
          istegeBagli
        />
      </section>

      <section className="flex flex-col gap-4">
        <div className="flex flex-col gap-1">
          <h2 className="font-heading text-xl font-semibold text-ana">
            Firma bilgileri
          </h2>
          <p className="text-sm text-pretty text-muted-foreground">
            Firma adınız ve iletişim e-postanız kayıtta alındı. E-posta kartta
            görünmez; iletişim iki taraf da onaylayınca açılır.
          </p>
        </div>

        <div className="flex flex-col gap-4">
          <div className="grid gap-4 sm:grid-cols-2">
            {firmaBilgisiSor ? (
              <>
                <FormAlani etiket="Sektör" htmlFor="sektor" istegeBagli>
                  <Input
                    id="sektor"
                    value={sektor}
                    onChange={(olay) => setSektor(olay.target.value)}
                  />
                </FormAlani>

                <FormAlani etiket="Firmanın şehri" htmlFor="sehir" istegeBagli>
                  {/* Serbest metin değil: yazım farkı eşleştirmeyi sessizce
                      bozuyordu (bkz. backend/app/core/sehir.py). */}
                  <select
                    id="sehir"
                    value={sehir}
                    onChange={(olay) => {
                      setSehir(olay.target.value);
                      // Aranan şehir boşsa kurumun şehri makul bir varsayılan;
                      // kullanıcı yine de değiştirebiliyor.
                      if (!aranilanSehir) setAranilanSehir(olay.target.value);
                    }}
                    className="h-8 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-baglanti focus-visible:ring-3 focus-visible:ring-baglanti/30"
                  >
                    {SEHIR_SECENEKLERI.map((secenek) => (
                      <option key={secenek.deger} value={secenek.deger}>
                        {secenek.etiket}
                      </option>
                    ))}
                  </select>
                </FormAlani>
              </>
            ) : null}

            <FormAlani
              etiket="Aranan şehir"
              htmlFor="aranilan-sehir"
              istegeBagli
            >
              <select
                id="aranilan-sehir"
                value={aranilanSehir}
                onChange={(olay) => setAranilanSehir(olay.target.value)}
                className="h-8 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-baglanti focus-visible:ring-3 focus-visible:ring-baglanti/30"
              >
                {SEHIR_SECENEKLERI.map((secenek) => (
                  <option key={secenek.deger} value={secenek.deger}>
                    {/* Ortak ilanında şehir varsayılan olarak fark etmez (karar 5). */}
                    {ortak && secenek.deger === ""
                      ? "Fark etmez"
                      : secenek.etiket}
                  </option>
                ))}
              </select>
            </FormAlani>
          </div>

          {ortak ? (
            <>
              <CokluSecim
                baslik="Aradığınız firma türleri"
                ipucu="(hiçbiri seçilmezse hepsi)"
                secenekler={FIRMA_TURLERI}
                secili={firmaTurleri}
                onDegis={setFirmaTurleri}
              />
              <FormAlani
                etiket="İş birliği türü"
                htmlFor="isbirligi-turu"
                istegeBagli
              >
                <select
                  id="isbirligi-turu"
                  value={isbirligiTuru}
                  onChange={(olay) => setIsbirligiTuru(olay.target.value)}
                  className="h-8 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-baglanti focus-visible:ring-3 focus-visible:ring-baglanti/30"
                >
                  <option value="">Belirtmek istemiyorum</option>
                  {ISBIRLIGI_TURLERI.map((tur) => (
                    <option key={tur.deger} value={tur.deger}>
                      {tur.etiket}
                    </option>
                  ))}
                </select>
              </FormAlani>
            </>
          ) : (
            <>
              {/* Eşleştirmenin sert filtreleri: zorunlu seçim. "Fark etmez"
                  boş değer olarak gider ve filtre uygulanmaz; firma bunu
                  unutarak değil, bilerek seçmiş olur. */}
              <FormAlani etiket="Çalışma modeli" htmlFor="calisma-modeli">
                <select
                  id="calisma-modeli"
                  required
                  value={calismaModeli}
                  onChange={(olay) => setCalismaModeli(olay.target.value)}
                  className="h-8 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-baglanti focus-visible:ring-3 focus-visible:ring-baglanti/30"
                >
                  <option value="" disabled>
                    Seçin
                  </option>
                  <option value={FARK_ETMEZ}>Fark etmez</option>
                  {CALISMA_MODELLERI.map((model) => (
                    <option key={model.deger} value={model.deger}>
                      {model.etiket}
                    </option>
                  ))}
                </select>
              </FormAlani>

              <FormAlani etiket="Müsaitlik" htmlFor="musaitlik">
                <select
                  id="musaitlik"
                  required
                  value={musaitlik}
                  onChange={(olay) => setMusaitlik(olay.target.value)}
                  className="h-8 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-baglanti focus-visible:ring-3 focus-visible:ring-baglanti/30"
                >
                  <option value="" disabled>
                    Seçin
                  </option>
                  <option value={FARK_ETMEZ}>Fark etmez</option>
                  {MUSAITLIK_SECENEKLERI.filter((s) => s.deger).map(
                    (secenek) => (
                      <option key={secenek.deger} value={secenek.deger}>
                        {secenek.etiket}
                      </option>
                    ),
                  )}
                </select>
              </FormAlani>
            </>
          )}

          {ortak ? (
            <p className="text-xs text-pretty text-muted-foreground">
              <span className="font-medium">Aranan şehir</span> yalnızca ortağın
              belirli bir şehirde olması şartsa seçilir; seçilmezse şehir fark
              etmez.
            </p>
          ) : firmaBilgisiSor ? (
            <p className="text-xs text-pretty text-muted-foreground">
              <span className="font-medium">Firmanın şehri</span> sizin
              bulunduğunuz yer;{" "}
              <span className="font-medium">aranan şehir</span> gencin nerede
              olmasını istediğiniz. Çalışma modeli “Uzaktan” ise aranan şehir
              dikkate alınmaz.
            </p>
          ) : (
            <p className="text-xs text-pretty text-muted-foreground">
              <span className="font-medium">Aranan şehir</span>, adayın nerede
              olmasını istediğiniz yer. Çalışma modeli “Uzaktan” ise aranan
              şehir dikkate alınmaz.
            </p>
          )}

          {/* Genç akışı (docs/plans/genc-akisi.md § 0 karar 1): eşik üstü
              adaylar ihtiyacı fırsat olarak görür. */}
          <p className="text-sm text-pretty text-muted-foreground">
            Onaylanan ihtiyaç, eşleşen adaylara gösterilir.
          </p>

          <Button
            type="submit"
            size="lg"
            disabled={bekleniyor}
            className="w-fit"
          >
            {bekleniyor ? "Kaydediliyor…" : "Kartı onayla"}
          </Button>
        </div>
      </section>
    </form>
  );
}

// Zorunlu seçimlerde "Fark etmez": backend'e boş gider (filtre yok).
const FARK_ETMEZ = "fark_etmez";

function secimDegeri(deger: string): string | null {
  return deger && deger !== FARK_ETMEZ ? deger : null;
}

// Backend'deki sınırlarla aynı (app/schemas/tanimlama.py).
const PROBLEM_EN_UZUN = 1000;
const KRITER_EN_UZUN = 500;

/** Taslağın düzenlenebilir metin alanı; sohbette çıkmadıysa bunu söyler. */
function MetinAlani({
  id,
  etiket,
  deger,
  setDeger,
  enUzun,
  sohbetteBos = false,
  istegeBagli = false,
}: {
  id: string;
  etiket: string;
  deger: string;
  setDeger: (deger: string) => void;
  enUzun: number;
  sohbetteBos?: boolean;
  istegeBagli?: boolean;
}) {
  const eksik = !istegeBagli && sohbetteBos && !deger.trim();
  return (
    <FormAlani etiket={etiket} htmlFor={id} istegeBagli={istegeBagli}>
      <Textarea
        id={id}
        rows={3}
        required={!istegeBagli}
        maxLength={enUzun}
        value={deger}
        aria-invalid={eksik || undefined}
        onChange={(olay) => setDeger(olay.target.value)}
        className={eksik ? "border-destructive" : undefined}
      />
      {eksik ? (
        <p className="text-xs text-pretty text-destructive">
          Sohbette netleşmedi. Onaylamadan önce buraya yazın.
        </p>
      ) : null}
    </FormAlani>
  );
}

/* --- Kart gösterimleri ---------------------------------------------------- */

function TaslakKarti({
  taslak,
  ortak = false,
  kurumAdi,
}: {
  taslak: IhtiyacTaslagi;
  ortak?: boolean;
  kurumAdi?: string;
}) {
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
