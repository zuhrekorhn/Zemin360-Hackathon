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
  type KartTaslagi,
  type KullaniciGirdisi,
  type YetenekKartiYaniti,
  kartOnayla,
  sohbetBaslat,
  sohbetCevap,
} from "@/lib/api";
import {
  DENEYIM_ETIKETLERI,
  MUSAITLIK_SECENEKLERI,
  SEHIR_SECENEKLERI,
  etiketle,
} from "@/lib/sabitler";
import { kimlikYaz } from "@/lib/yerel";

/**
 * Keşif Ajanı sohbeti (docs/agent-specs.md § 1).
 *
 * Akış: sohbet → taslak gözden geçirme → onay formu → kaydedilen kart.
 * Taslak onaylanana kadar hiçbir şey veritabanına yazılmaz; insan onayı
 * zorunlu (spec madde 3).
 *
 * Görsel dil (docs/design-language.md): sohbet balonları yuvarlak/sıcak,
 * taslak ve kayıtlı kart hairline çizgili ve az yuvarlak — "resmi belge".
 */

type Asama = "baslatiliyor" | "sohbet" | "taslak" | "kaydedildi";

export default function KesifSayfasi() {
  const [asama, setAsama] = useState<Asama>("baslatiliyor");
  const [oturumId, setOturumId] = useState<string | null>(null);
  const [mesajlar, setMesajlar] = useState<Mesaj[]>([]);
  const [taslak, setTaslak] = useState<KartTaslagi | null>(null);
  const [kart, setKart] = useState<YetenekKartiYaniti | null>(null);

  const [girdi, setGirdi] = useState("");
  const [bekleniyor, setBekleniyor] = useState(false);
  const [hata, setHata] = useState<SohbetHatasi | null>(null);
  // 429 sonrası "Tekrar dene" aynı cevabı yeniden göndersin diye tutuluyor;
  // sohbet backend'de checkpointer'da durduğu için oturum_id değişmez.
  const bekleyenCevap = useRef<string | null>(null);
  const baslatildi = useRef(false);
  const sonMesaj = useRef<HTMLDivElement | null>(null);

  const hatayiYaz = useCallback((sebep: unknown) => {
    if (sebep instanceof ApiHatasi && sebep.durumKodu === 429) {
      setHata({
        metin: "Şu an yoğunluk var. Birkaç saniye sonra tekrar dene.",
        kota: true,
      });
      return;
    }
    setHata({
      metin:
        sebep instanceof ApiHatasi
          ? sebep.message
          : "Beklenmeyen bir şey oldu, tekrar dene.",
      kota: false,
    });
  }, []);

  const sohbetiBaslat = useCallback(async () => {
    setHata(null);
    setBekleniyor(true);
    try {
      const yanit = await sohbetBaslat();
      setOturumId(yanit.oturum_id);
      setMesajlar(yanit.soru ? [{ kim: "ajan", metin: yanit.soru }] : []);
      setTaslak(yanit.taslak);
      setAsama("sohbet");
    } catch (sebep) {
      hatayiYaz(sebep);
    } finally {
      setBekleniyor(false);
    }
  }, [hatayiYaz]);

  useEffect(() => {
    // React StrictMode geliştirmede efekti iki kez çalıştırıyor; ikinci bir
    // oturum açılmasın.
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
      const yanit = await sohbetCevap(oturumId, cevap);
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
          Keşif Ajanı
        </h1>
        <p className="text-sm text-pretty text-muted-foreground">
          Kısa bir sohbet. Ne yaptığını birlikte bir yetenek kartına
          dönüştüreceğiz. Kart sen onaylamadan kaydedilmez.
        </p>
      </header>

      {asama === "sohbet" || asama === "baslatiliyor" ? (
        <Sohbet
          ajanAdi="Keşif Ajanı"
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
          onOnayla={async (kullanici) => {
            if (!oturumId) return;
            setHata(null);
            setBekleniyor(true);
            try {
              const kayitli = await kartOnayla(oturumId, kullanici);
              // Kanıt ekleme ekranı kart kimliğiyle açılıyor; giriş akışı
              // olmadığı için kimlik tarayıcıda hatırlanıyor.
              kimlikYaz("kart", kayitli.id);
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
  taslak: KartTaslagi;
  bekleniyor: boolean;
  onOnayla: (kullanici: KullaniciGirdisi) => void;
}) {
  const [ad, setAd] = useState("");
  const [email, setEmail] = useState("");
  const [sehir, setSehir] = useState("");
  const [musaitlik, setMusaitlik] = useState("");

  return (
    <div className="flex flex-col gap-8">
      <section className="flex flex-col gap-3">
        <h2 className="font-heading text-xl font-semibold text-ana">
          Kart taslağın
        </h2>
        <p className="text-sm text-pretty text-muted-foreground">
          Sohbetten çıkan kart bu. Gözden geçir, doğruysa aşağıdan onayla.
        </p>
        <TaslakKarti taslak={taslak} />
      </section>

      <section className="flex flex-col gap-4">
        <div className="flex flex-col gap-1">
          <h2 className="font-heading text-xl font-semibold text-ana">
            Seninle nasıl iletişime geçelim
          </h2>
          <p className="text-sm text-pretty text-muted-foreground">
            E-postan kartta görünmez. Kurumlara sadece kart gösterilir; iletişim
            iki taraf da onaylayınca açılır.
          </p>
        </div>

        <form
          className="flex flex-col gap-4"
          onSubmit={(olay) => {
            olay.preventDefault();
            if (bekleniyor) return;
            onOnayla({
              ad: ad.trim(),
              email: email.trim(),
              sehir: sehir.trim() || null,
              musaitlik: musaitlik || null,
            });
          }}
        >
          <div className="grid gap-4 sm:grid-cols-2">
            <FormAlani etiket="Ad" htmlFor="ad">
              <Input
                id="ad"
                value={ad}
                onChange={(olay) => setAd(olay.target.value)}
                required
                autoComplete="name"
              />
            </FormAlani>

            <FormAlani etiket="E-posta" htmlFor="email">
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(olay) => setEmail(olay.target.value)}
                required
                autoComplete="email"
              />
            </FormAlani>

            <FormAlani etiket="Şehir" htmlFor="sehir" istegeBagli>
              {/* Serbest metin değil: yazım farkı eşleştirmeyi sessizce
                  bozuyordu (bkz. backend/app/core/sehir.py). */}
              <select
                id="sehir"
                value={sehir}
                onChange={(olay) => setSehir(olay.target.value)}
                className="h-8 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-baglanti focus-visible:ring-3 focus-visible:ring-baglanti/30"
              >
                {SEHIR_SECENEKLERI.map((secenek) => (
                  <option key={secenek.deger} value={secenek.deger}>
                    {secenek.etiket}
                  </option>
                ))}
              </select>
            </FormAlani>

            <FormAlani etiket="Müsaitlik" htmlFor="musaitlik" istegeBagli>
              <select
                id="musaitlik"
                value={musaitlik}
                onChange={(olay) => setMusaitlik(olay.target.value)}
                className="h-8 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm outline-none focus-visible:border-baglanti focus-visible:ring-3 focus-visible:ring-baglanti/30"
              >
                {MUSAITLIK_SECENEKLERI.map((secenek) => (
                  <option key={secenek.deger} value={secenek.deger}>
                    {secenek.etiket}
                  </option>
                ))}
              </select>
            </FormAlani>
          </div>

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

function TaslakKarti({ taslak }: { taslak: KartTaslagi }) {
  return (
    <article className="rounded-sm border border-kenar bg-card">
      <dl className="grid gap-px bg-kenar sm:grid-cols-2">
        <KartSatiri etiket="Rol / alan" deger={taslak.rol_alani} />
        <KartSatiri
          etiket="Deneyim"
          deger={etiketle(DENEYIM_ETIKETLERI, taslak.deneyim_seviyesi)}
        />
        <KartSatiri
          etiket="Sektör ilgisi"
          deger={taslak.sektor_ilgi_alani.join(", ")}
        />
        <KartSatiri
          etiket="Araçlar"
          deger={taslak.araclar_teknolojiler.join(", ")}
        />
      </dl>

      <div className="border-t border-kenar px-4 py-3">
        <h3 className="text-xs text-muted-foreground">Somut çıktılar</h3>
        {taslak.somut_ciktilar.length === 0 ? (
          <p className="mt-1 text-sm text-pretty">
            Henüz yok — kartın “potansiyel” olarak kaydedilecek. Sonradan
            ekleyebilirsin.
          </p>
        ) : (
          <ul className="mt-2 flex flex-col gap-3">
            {taslak.somut_ciktilar.map((cikti) => (
              <li key={cikti.baslik} className="flex flex-col gap-0.5">
                <span className="text-sm font-medium break-words">
                  {cikti.baslik}
                </span>
                {cikti.aciklama ? (
                  <span className="text-sm text-pretty text-muted-foreground">
                    {cikti.aciklama}
                  </span>
                ) : null}
                {cikti.kanit_linki ? (
                  <span className="font-mono text-xs break-all text-baglanti">
                    {cikti.kanit_linki}
                  </span>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </div>
    </article>
  );
}

function KartSatiri({
  etiket,
  deger,
}: {
  etiket: string;
  deger: string | null;
}) {
  return (
    <div className="bg-card px-4 py-3">
      <dt className="text-xs text-muted-foreground">{etiket}</dt>
      <dd className="text-sm break-words">{deger || "—"}</dd>
    </div>
  );
}

function KayitliKart({ kart }: { kart: YetenekKartiYaniti }) {
  return (
    <section className="flex flex-col gap-3">
      <h2 className="font-heading text-xl font-semibold text-ana">
        Kartın kaydedildi
      </h2>
      <p className="text-sm text-pretty text-muted-foreground">
        Artık kurumların ihtiyaç kartlarıyla eşleştirilebilir.
        {kart.kanit_bekleyen
          ? " Çıktılarının bir kısmı kanıt bekliyor — kanıt eklersen kartın daha güçlü görünür."
          : null}
      </p>

      <TaslakKarti
        taslak={{
          rol_alani: kart.rol_alani,
          deneyim_seviyesi: kart.deneyim_seviyesi,
          sektor_ilgi_alani: kart.sektor_ilgi_alani,
          araclar_teknolojiler: kart.araclar_teknolojiler,
          somut_ciktilar: kart.somut_ciktilar,
        }}
      />

      <p className="font-mono text-xs text-muted-foreground">
        {/* Sadece id kırılsın; "sürüm" kelimesi dar ekranda ortadan bölünmesin. */}
        kart no: <span className="break-all">{kart.id}</span> · sürüm{" "}
        {kart.versiyon}
      </p>

      <Button asChild size="lg" className="mt-1 w-fit">
        <Link href={`/kart/${kart.id}`}>Kanıt ekle ve doğrulat</Link>
      </Button>
    </section>
  );
}
