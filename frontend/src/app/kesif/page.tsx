"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useRef, useState } from "react";

import { CokluSecim } from "@/components/coklu-secim";
import { GirisKapisi, useGirisliHesap } from "@/components/giris-kapisi";
import { IsKalemiFormu } from "@/components/is-kalemi-formu";
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
import {
  type KartTaslagi,
  type SomutCiktiTaslagi,
  type GencProfili,
  type YetenekKartiYaniti,
  kartOnayla,
  sohbetBaslat,
  sohbetCevap,
  yetenekKartiHazirla,
} from "@/lib/api";
import { hatayaCevir } from "@/lib/hata";
import { onaydaProfilSorulmali } from "@/lib/profil";
import {
  CALISMA_MODELLERI,
  DENEYIM_ETIKETLERI,
  IS_TURU_ETIKETLERI,
  MUSAITLIKLER,
  SEHIR_SECENEKLERI,
  etiketle,
} from "@/lib/sabitler";

/**
 * Keşif Ajanı sohbeti (docs/agent-specs.md § 1).
 *
 * Akış: sohbet → taslak gözden geçirme → onay formu → kaydedilen kart.
 * Kayıttan hemen sonra buraya gelinir (`?ilk=1`, docs/plans/genc-akisi.md
 * § 5.2); "Şimdilik atla" panele götürür, kartı olmayan genç eşleştirmeye
 * girmez ve panel onu kart tamamlamaya çağırır. Kayıt formundaki bilgiler
 * sohbette sorulmaz.
 * Taslak onaylanana kadar hiçbir şey veritabanına yazılmaz; insan onayı
 * zorunlu (spec madde 3).
 *
 * Görsel dil (docs/design-language.md): sohbet balonları yuvarlak/sıcak,
 * taslak ve kayıtlı kart hairline çizgili ve az yuvarlak — "resmi belge".
 */

type Asama = "baslatiliyor" | "sohbet" | "taslak" | "kaydedildi";

export default function KesifSayfasi() {
  return (
    <Suspense fallback={null}>
      <GirisKapisi roller={["genc"]}>
        <KesifSohbeti />
      </GirisKapisi>
    </Suspense>
  );
}

function KesifSohbeti() {
  // Kayıttan hemen sonra (onboarding): "Şimdilik atla" görünür.
  const ilkKez = useSearchParams().get("ilk") === "1";
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

  // Hata cümlesi tek yerden: lib/hata.ts (429 hız sınırı, 503 arıza ayrımı orada).
  const hatayiYaz = useCallback(
    (sebep: unknown) => setHata(hatayaCevir(sebep)),
    [],
  );

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
          {ilkKez
            ? " Kayıtta verdiğin bilgileri tekrar sormayacağız."
            : null}
        </p>
        {ilkKez && asama !== "kaydedildi" ? (
          <p className="text-sm text-pretty text-muted-foreground">
            Şimdi vaktin yoksa sonra da yapabilirsin; ama kartı olmayan genç
            kurumlara önerilmez.{" "}
            <Link href="/genc" className="text-baglanti underline">
              Şimdilik atla
            </Link>
          </p>
        ) : null}
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
          onOnayla={async (profil, duzeltilmisTaslak) => {
            if (!oturumId) return;
            setHata(null);
            setBekleniyor(true);
            try {
              const kayitli = await kartOnayla(
                oturumId,
                profil,
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
          <Link href="/genc">Panele dön</Link>
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
  onOnayla: (profil: GencProfili, duzeltilmisTaslak: KartTaslagi) => void;
}) {
  // Sohbetten çıkan taslak üzerinde kullanıcı son sözü söylesin: ajan aynı işi
  // iki kez yazmış ya da bir şeyi yanlış anlamış olabilir.
  const [ciktilar, setCiktilar] = useState(taslak.somut_ciktilar);
  const [sehir, setSehir] = useState("");
  // Kabul ettiği çalışma modelleri — çoklu. Konumdan ayrı bir şey.
  const [calismaModelleri, setCalismaModelleri] = useState<string[]>([]);
  // Kabul ettiği çalışma tipleri — çoklu (staj dahil).
  const [musaitlikler, setMusaitlikler] = useState<string[]>([]);
  // Kayıtta alındıysa sorulmaz; bu alanlardan önce açılmış hesapta eksikse sorulur.
  const profilSor = onaydaProfilSorulmali(
    useGirisliHesap().eksik_profil_alanlari,
  );

  return (
    <div className="flex flex-col gap-8">
      <section className="flex flex-col gap-3">
        <h2 className="font-heading text-xl font-semibold text-ana">
          Kart taslağın
        </h2>
        <p className="text-sm text-pretty text-muted-foreground">
          Sohbetten çıkan kart bu. Gözden geçir, doğruysa aşağıdan onayla.
        </p>
        <TaslakKarti
          taslak={{ ...taslak, somut_ciktilar: ciktilar }}
          duzenlenebilir
          onCiktiDegis={(sira, alan, deger) =>
            setCiktilar((oncekiler) =>
              oncekiler.map((cikti, i) =>
                i === sira ? { ...cikti, [alan]: deger || null } : cikti,
              ),
            )
          }
          onCiktiSil={(sira) =>
            setCiktilar((oncekiler) => oncekiler.filter((_, i) => i !== sira))
          }
        />
      </section>

      <section className="flex flex-col gap-4">
        <div className="flex flex-col gap-1">
          <h2 className="font-heading text-xl font-semibold text-ana">
            {profilSor ? "Nerede ve nasıl çalışabilirsin" : "Onay"}
          </h2>
          <p className="text-sm text-pretty text-muted-foreground">
            {profilSor
              ? "Eşleştirme bu bilgilerle yapılır. "
              : "Çalışma tercihlerin profilinde; değiştirmek istersen Profilim sayfasından. "}
            E-postan kartta görünmez; iletişim ancak karşılıklı ilgiyle açılır.
          </p>
        </div>

        <form
          className="flex flex-col gap-4"
          onSubmit={(olay) => {
            olay.preventDefault();
            if (bekleniyor) return;
            onOnayla(
              // Boş profil kayıtlı değerleri silmez (backend kuralı).
              profilSor
                ? { sehir, calisma_modelleri: calismaModelleri, musaitlikler }
                : {},
              { ...taslak, somut_ciktilar: ciktilar },
            );
          }}
        >
          {profilSor ? (
          <div className="grid gap-4 sm:grid-cols-2">
            <FormAlani etiket="Şehir" htmlFor="sehir">
              {/* Serbest metin değil: yazım farkı eşleştirmeyi sessizce
                  bozuyordu (bkz. backend/app/core/sehir.py). */}
              <select
                id="sehir"
                value={sehir}
                required
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

            <CokluSecim
              baslik="Çalışma modeli"
              ipucu="(kabul ettiklerini işaretle)"
              aciklama="Nerede çalışacağın. Müsaitlik ayrı bir şey: ne kadar süreyle."
              secenekler={CALISMA_MODELLERI}
              secili={calismaModelleri}
              onDegis={setCalismaModelleri}
            />

            <CokluSecim
              baslik="Müsaitlik"
              ipucu="(uygun olanların hepsini işaretle; boş bırakabilirsin)"
              secenekler={MUSAITLIKLER}
              secili={musaitlikler}
              onDegis={setMusaitlikler}
            />
          </div>
          ) : null}

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
  duzenlenebilir = false,
  onCiktiDegis,
  onCiktiSil,
}: {
  taslak: KartTaslagi;
  /** Onaydan önce kullanıcı çıktıları düzeltebilsin diye. */
  duzenlenebilir?: boolean;
  onCiktiDegis?: (
    sira: number,
    alan: keyof SomutCiktiTaslagi,
    deger: string,
  ) => void;
  onCiktiSil?: (sira: number) => void;
}) {
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
        {taslak.sertifikalar?.length ? (
          <KartSatiri
            etiket="Sertifikalar"
            deger={taslak.sertifikalar.join(", ")}
          />
        ) : null}
        {taslak.diller?.length ? (
          <KartSatiri etiket="Diller" deger={taslak.diller.join(", ")} />
        ) : null}
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
            {taslak.somut_ciktilar.map((cikti, sira) =>
              duzenlenebilir && onCiktiDegis && onCiktiSil ? (
                <li
                  key={sira}
                  className="flex flex-col gap-2 rounded-sm border border-kenar px-3 py-3"
                >
                  <div className="flex justify-end">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => onCiktiSil(sira)}
                    >
                      Çıkar
                    </Button>
                  </div>
                  <IsKalemiFormu
                    kimlik={`cikti-${sira}`}
                    cikti={cikti}
                    onDegis={(alan, deger) => onCiktiDegis(sira, alan, deger)}
                  />
                </li>
              ) : (
                <li key={sira} className="flex flex-col gap-0.5">
                  <span className="text-sm font-medium break-words">
                    {cikti.baslik}
                    {cikti.is_turu ? (
                      <span className="ml-2 text-xs font-normal text-muted-foreground">
                        {etiketle(IS_TURU_ETIKETLERI, cikti.is_turu)}
                      </span>
                    ) : null}
                  </span>
                  {cikti.aciklama ? (
                    <span className="text-sm text-pretty text-muted-foreground">
                      {cikti.aciklama}
                    </span>
                  ) : null}
                  {cikti.olculebilir_sonuc ? (
                    <span className="text-sm text-pretty">
                      Sonuç: {cikti.olculebilir_sonuc}
                    </span>
                  ) : null}
                  {cikti.kendi_rolu ? (
                    <span className="text-sm text-pretty">
                      Payın: {cikti.kendi_rolu}
                    </span>
                  ) : null}
                  {cikti.kanit_linki ? (
                    <span className="font-mono text-xs break-all text-baglanti">
                      {cikti.kanit_linki}
                    </span>
                  ) : null}
                </li>
              ),
            )}
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

function KayitliKart({
  kart,
  onGuncelle,
}: {
  kart: YetenekKartiYaniti;
  onGuncelle: (kart: YetenekKartiYaniti) => void;
}) {
  return (
    <section className="flex flex-col gap-3">
      <h2 className="font-heading text-xl font-semibold text-ana">
        Kartın kaydedildi
      </h2>
      {kart.embedding_var ? (
        <p className="text-sm text-pretty text-muted-foreground">
          Artık kurumların ihtiyaç kartlarıyla eşleştirilebilir.
          {kart.kanit_bekleyen
            ? " Çıktılarının bir kısmı kanıt bekliyor — kanıt eklersen kartın daha güçlü görünür."
            : null}
        </p>
      ) : (
        <EslestirmeyeHazirla
          hazirla={async () => onGuncelle(await yetenekKartiHazirla(kart.id))}
        />
      )}

      <TaslakKarti
        taslak={{
          rol_alani: kart.rol_alani,
          deneyim_seviyesi: kart.deneyim_seviyesi,
          sektor_ilgi_alani: kart.sektor_ilgi_alani,
          araclar_teknolojiler: kart.araclar_teknolojiler,
          sertifikalar: kart.sertifikalar,
          diller: kart.diller,
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
