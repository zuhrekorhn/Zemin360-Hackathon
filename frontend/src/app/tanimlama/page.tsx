"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

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
import {
  ApiHatasi,
  type IhtiyacKartiYaniti,
  type IhtiyacTaslagi,
  type KurumGirdisi,
  ihtiyacKartiOnayla,
  tanimlamaBaslat,
  tanimlamaCevap,
} from "@/lib/api";
import {
  MUSAITLIK_ETIKETLERI,
  SEHIR_SECENEKLERI,
  etiketle,
  sehirEtiketi,
} from "@/lib/sabitler";
import { kimlikYaz } from "@/lib/yerel";

/**
 * Tanımlama Ajanı sohbeti (docs/agent-specs.md § 2).
 *
 * Keşif ile aynı akış: sohbet → taslak gözden geçirme → onay → kaydedilen kart.
 * Fark soru setinde: ajan sokratik sorularla belirsiz ifadeyi ölçülebilir hale
 * getirir. Kart kurum onaylamadan veritabanına yazılmaz.
 */

type Asama = "sohbet" | "taslak" | "kaydedildi";

export default function TanimlamaSayfasi() {
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

  const hatayiYaz = useCallback((sebep: unknown) => {
    if (sebep instanceof ApiHatasi && sebep.durumKodu === 429) {
      setHata({
        metin: "Şu an yoğunluk var. Birkaç saniye sonra tekrar deneyin.",
        kota: true,
      });
      return;
    }
    setHata({
      metin:
        sebep instanceof ApiHatasi
          ? sebep.message
          : "Beklenmeyen bir şey oldu, tekrar deneyin.",
      kota: false,
    });
  }, []);

  const sohbetiBaslat = useCallback(async () => {
    setHata(null);
    setBekleniyor(true);
    try {
      const yanit = await tanimlamaBaslat();
      setOturumId(yanit.oturum_id);
      setMesajlar(yanit.soru ? [{ kim: "ajan", metin: yanit.soru }] : []);
      setTaslak(yanit.taslak);
    } catch (sebep) {
      hatayiYaz(sebep);
    } finally {
      setBekleniyor(false);
    }
  }, [hatayiYaz]);

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
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-8 px-4 py-10 sm:px-6 sm:py-16">
      <header className="flex flex-col gap-2">
        <h1 className="font-heading text-2xl font-semibold text-ana sm:text-3xl">
          Tanımlama Ajanı
        </h1>
        <p className="text-sm text-pretty text-muted-foreground">
          Kısa bir sohbet. İhtiyacınızı birlikte ölçülebilir bir ihtiyaç kartına
          çevireceğiz. Kart siz onaylamadan kaydedilmez.
        </p>
      </header>

      {asama === "sohbet" ? (
        <Sohbet
          ajanAdi="Tanımlama Ajanı"
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
          bekleniyor={bekleniyor}
          onOnayla={async (kurum, duzeltilmisTaslak) => {
            if (!oturumId) return;
            setHata(null);
            setBekleniyor(true);
            try {
              const kayitli = await ihtiyacKartiOnayla(
                oturumId,
                kurum,
                duzeltilmisTaslak,
              );
              // Öneri ekranı kurum kimliğiyle çalışıyor; giriş akışı
              // olmadığı için kimlik tarayıcıda hatırlanıyor.
              kimlikYaz("kurum", kayitli.kurum.id);
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

      {asama === "kaydedildi" && kart ? <KayitliKart kart={kart} /> : null}

      <footer className="mt-auto border-t border-kenar pt-6">
        <Button asChild variant="outline" size="lg">
          <Link href="/">Ana sayfaya dön</Link>
        </Button>
      </footer>
    </main>
  );
}

/* --- Taslak ve onay ------------------------------------------------------- */

function TaslakBolumu({
  taslak,
  bekleniyor,
  onOnayla,
}: {
  taslak: IhtiyacTaslagi;
  bekleniyor: boolean;
  onOnayla: (kurum: KurumGirdisi, duzeltilmisTaslak: IhtiyacTaslagi) => void;
}) {
  const [ad, setAd] = useState("");
  const [sektor, setSektor] = useState("");
  const [sehir, setSehir] = useState("");
  const [email, setEmail] = useState("");
  // İki ayrı şehir var ve karıştırılıyordu: kurumun bulunduğu yer ile
  // gencin bulunmasını istediğiniz yer. İkincisi eşleştirmenin sert
  // filtresi, o yüzden burada görünür ve düzeltilebilir.
  const [aranilanSehir, setAranilanSehir] = useState(
    taslak.sehir_tercihi ?? "",
  );

  return (
    <div className="flex flex-col gap-8">
      <section className="flex flex-col gap-3">
        <h2 className="font-heading text-xl font-semibold text-ana">
          İhtiyaç kartı taslağınız
        </h2>
        <p className="text-sm text-pretty text-muted-foreground">
          Sohbetten çıkan kart bu. Gözden geçirin, doğruysa aşağıdan onaylayın.
        </p>
        <TaslakKarti taslak={taslak} />
      </section>

      <section className="flex flex-col gap-4">
        <div className="flex flex-col gap-1">
          <h2 className="font-heading text-xl font-semibold text-ana">
            Kurum bilgileri
          </h2>
          <p className="text-sm text-pretty text-muted-foreground">
            İletişim e-postanız kartta görünmez. Gençlere sadece kart
            gösterilir; iletişim iki taraf da onaylayınca açılır.
          </p>
        </div>

        <form
          className="flex flex-col gap-4"
          onSubmit={(olay) => {
            olay.preventDefault();
            if (bekleniyor) return;
            onOnayla(
              {
                ad: ad.trim(),
                sektor: sektor.trim() || null,
                sehir: sehir || null,
                iletisim_email: email.trim(),
              },
              { ...taslak, sehir_tercihi: aranilanSehir || null },
            );
          }}
        >
          <div className="grid gap-4 sm:grid-cols-2">
            <FormAlani etiket="Kurum adı" htmlFor="ad">
              <Input
                id="ad"
                value={ad}
                onChange={(olay) => setAd(olay.target.value)}
                required
                autoComplete="organization"
              />
            </FormAlani>

            <FormAlani etiket="İletişim e-postası" htmlFor="email">
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(olay) => setEmail(olay.target.value)}
                required
                autoComplete="email"
              />
            </FormAlani>

            <FormAlani etiket="Sektör" htmlFor="sektor" istegeBagli>
              <Input
                id="sektor"
                value={sektor}
                onChange={(olay) => setSektor(olay.target.value)}
              />
            </FormAlani>

            <FormAlani etiket="Kurumun şehri" htmlFor="sehir" istegeBagli>
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
                    {secenek.etiket}
                  </option>
                ))}
              </select>
            </FormAlani>
          </div>

          <p className="text-xs text-pretty text-muted-foreground">
            <span className="font-medium">Kurumun şehri</span> sizin
            bulunduğunuz yer; <span className="font-medium">aranan şehir</span>{" "}
            gencin nerede olmasını istediğiniz. “Uzaktan / fark etmez”
            seçerseniz şehir filtresi hiç uygulanmaz.
          </p>

          <Button
            type="submit"
            size="lg"
            disabled={bekleniyor}
            className="w-fit"
          >
            {bekleniyor ? "Kaydediliyor…" : "Kartı onayla"}
          </Button>
        </form>
      </section>
    </div>
  );
}

/* --- Kart gösterimleri ---------------------------------------------------- */

function TaslakKarti({
  taslak,
  kurumAdi,
}: {
  taslak: IhtiyacTaslagi;
  kurumAdi?: string;
}) {
  return (
    <article className="rounded-sm border border-kenar bg-card">
      {kurumAdi ? (
        <div className="border-b border-kenar px-4 py-3">
          <p className="text-xs text-muted-foreground">Kurum</p>
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
            {sehirEtiketi(taslak.sehir_tercihi)}
          </dd>
        </div>
        <div className="bg-card px-4 py-3">
          <dt className="text-xs text-muted-foreground">Müsaitlik tercihi</dt>
          <dd className="text-sm break-words">
            {etiketle(MUSAITLIK_ETIKETLERI, taslak.musaitlik_tercihi)}
          </dd>
        </div>
      </dl>
    </article>
  );
}

function KayitliKart({ kart }: { kart: IhtiyacKartiYaniti }) {
  return (
    <section className="flex flex-col gap-3">
      <h2 className="font-heading text-xl font-semibold text-ana">
        İhtiyaç kartınız kaydedildi
      </h2>
      <p className="text-sm text-pretty text-muted-foreground">
        Artık genç yeteneklerin yetenek kartlarıyla eşleştirilebilir.
      </p>

      <TaslakKarti taslak={kart} kurumAdi={kart.kurum.ad} />

      <p className="font-mono text-xs text-muted-foreground">
        kart no: <span className="break-all">{kart.id}</span>
      </p>

      <Button asChild size="lg" className="mt-1 w-fit">
        <Link href={`/kurum/oneriler?kurum=${kart.kurum.id}`}>
          Eşleştirme önerilerini gör
        </Link>
      </Button>
    </section>
  );
}
